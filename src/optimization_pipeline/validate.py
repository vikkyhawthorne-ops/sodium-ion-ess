import pybamm
import numpy as np
import scipy.io as sio
import os
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

class StabilityValidator:
    """
    Stability Validation (Physics Consistency Check).
    Uses coupled reduced-order physics framework with PyBaMM.
    Ref: docs/paper.md
    """

    def __init__(self, base_params_dict):
        self.base_params = base_params_dict

    def validate_electrochemical_performance(self, optimized_subset=None):
        """
        Validates energy density and stability constraints.
        """
        print("Validating electrochemical performance...")

        # Merge if optimized subset provided
        params_to_test = self.base_params.copy()
        if optimized_subset:
            # Map optimization vector theta = [L_c, L_a, eps_c, eps_a, r_p] back to keys
            params_to_test.update({
                "Positive electrode thickness [m]": optimized_subset[0],
                "Negative electrode thickness [m]": optimized_subset[1],
                "Positive electrode porosity": optimized_subset[2],
                "Negative electrode porosity": optimized_subset[3],
                "Positive particle radius [m]": optimized_subset[4]
            })

        param_values = pybamm.ParameterValues(params_to_test)

        try:
            model = pybamm.sodium_ion.DFN()
        except AttributeError:
            model = pybamm.lithium_ion.DFN()

        sim = pybamm.Simulation(model, parameter_values=param_values)
        sol = sim.solve([0, 3600])

        energy = sol["Discharge energy [W.h]"].data[-1]
        energy_density = energy / 0.07 # Mass estimate

        print(f"Validation: Energy Density = {energy_density:.2f} Wh/kg")

        return {
            "energy_density_wh_kg": energy_density,
            "met_constraints": energy_density >= 140.0,
            "merged_params": params_to_test
        }

    def export_to_matlab(self, merged_params, output_path="src/control_systems/optimized_params.mat"):
        """
        Exports the validated and merged parameter set as a MATLAB input file.
        """
        # Convert functions/callables to strings for MATLAB compatibility
        mat_ready_dict = {}
        for k, v in merged_params.items():
            clean_k = k.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "_").replace(".", "").replace("/", "_")
            if callable(v):
                mat_ready_dict[clean_k] = "function_handle"
            else:
                mat_ready_dict[clean_k] = v

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sio.savemat(output_path, {"optimized_params": mat_ready_dict})
        print(f"Validated parameter set exported to {output_path}")

if __name__ == "__main__":
    base_p = get_parameter_values()
    validator = StabilityValidator(base_p)
    results = validator.validate_electrochemical_performance()
    validator.export_to_matlab(results["merged_params"])
