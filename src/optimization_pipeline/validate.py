import pybamm
import numpy as np
import scipy.io as sio
from scipy.integrate import trapezoid
import os
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

class StabilityValidator:
    """
    Stability Validation (Physics Consistency Check).
    Uses CasadiSolver (safe mode) and Refined Degradation/Resistance Models.
    Ref: docs/paper.md
    """

    def __init__(self, base_params_dict):
        self.base_params = base_params_dict

    def validate_electrochemical_performance(self, optimized_subset=None):
        print("Validating electrochemical performance (Physics-Coupled Twin)...")

        params_to_test = self.base_params.copy()
        if optimized_subset:
            design = optimized_subset["design"]
            params_to_test.update({
                "Positive electrode thickness [m]": design[0],
                "Negative electrode thickness [m]": design[1],
                "Positive electrode porosity": design[2],
                "Negative electrode porosity": design[3],
                "Positive particle radius [m]": design[4]
            })

        param_values = pybamm.ParameterValues(params_to_test)
        param_values["Current function [A]"] = 10.0 # 1C

        try:
            model = pybamm.sodium_ion.DFN()
        except AttributeError:
            model = pybamm.lithium_ion.DFN()

        # Numerical Stability: CasadiSolver in safe mode
        solver = pybamm.CasadiSolver(mode="safe", atol=1e-6, rtol=1e-6)
        sim = pybamm.Simulation(model, parameter_values=param_values, solver=solver)

        try:
            sol = sim.solve([0, 3600*2])
        except pybamm.SolverError as e:
            print(f"Solver Failure: {e}")
            return {"met_constraints": False, "error": str(e)}

        # Performance Metrics
        energy_wh = sol["Discharge energy [W.h]"].data[-1]
        nominal_voltage = np.mean(sol["Terminal voltage [V]"].data)
        capacity_ah = sol["Discharge capacity [A.h]"].data[-1]

        # 1. Physical Resistance Model: R(T) = R0 * exp(Ea/RT) + R_strain
        temp_k = sol["Volume-averaged cell temperature [K]"].data
        R0_base = params_to_test.get("Contact resistance [Ohm]", 0.001)
        Ea_r = 5000 # [J/mol]
        r_gas = 8.314

        # Strain calculation (Thermal + Concentration)
        alpha_thermal = 1e-5
        beta_soc = 0.02
        soc = 1.0 - (sol["Discharge capacity [A.h]"].data / (capacity_ah + 1e-6))
        strain = alpha_thermal * (temp_k - temp_k[0]) + beta_soc * soc

        resistance_profile = R0_base * np.exp(Ea_r / (r_gas * temp_k)) + 0.5 * strain

        # 2. Refined Cycle Life Model: Coupled to SOC, T, and I
        # dot_SEI = k * |I|^0.5 * exp(-Ea/RT) * f(SOC)
        k_sei = 2e-10
        Ea_sei = 35000
        f_soc = 1.0 + soc # Higher degradation at high SOC
        sei_rate = k_sei * (10.0**0.5) * np.exp(-Ea_sei / (r_gas * temp_k)) * f_soc
        sei_total = trapezoid(sei_rate, sol["Time [s]"].data)
        cycle_life = int(0.2 / (sei_total + 1e-15))
        cycle_life = min(max(cycle_life, 1000), 10000)

        results = {
            "energy_capacity_kwh": energy_wh / 1000.0,
            "nominal_voltage_v": nominal_voltage,
            "continuous_current_a": capacity_ah,
            "peak_current_a": 3.0 * capacity_ah,
            "charge_time_h": 1.0,
            "power_capability_kw": (nominal_voltage * 3.0 * capacity_ah) / 1000.0,
            "cycle_life": cycle_life,
            "energy_density_wh_kg": energy_wh / 0.07,
            "met_constraints": (energy_wh / 0.07) >= 140.0,
            "resistance_profile": {
                "temperature": temp_k.tolist(),
                "strain": strain.tolist(),
                "resistance": resistance_profile.tolist()
            },
            "merged_params": params_to_test
        }
        return results

    def export_to_matlab(self, results, output_path="src/control_systems/optimized_params.mat"):
        merged_params = results["merged_params"]
        mat_ready_dict = {}
        for k, v in merged_params.items():
            clean_k = k.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "_").replace(".", "").replace("/", "_")[:31]
            if not callable(v):
                mat_ready_dict[clean_k] = v

        mat_ready_dict["validation_metrics"] = {k: v for k, v in results.items() if k not in ["merged_params", "resistance_profile"]}
        mat_ready_dict["resistance_data"] = results["resistance_profile"]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sio.savemat(output_path, {"optimized_params": mat_ready_dict})
        print(f"Validated Twin exported to {output_path}")

if __name__ == "__main__":
    base_p = get_parameter_values()
    validator = StabilityValidator(base_p)
    mock_opt = {"design": [0.0001, 0.00012, 0.3, 0.3, 1e-6]}
    results = validator.validate_electrochemical_performance(mock_opt)
    validator.export_to_matlab(results)
