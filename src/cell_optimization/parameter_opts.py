import numpy as np
import pybamm
import logging
import json
import os
import traceback
from typing import Dict, Any, List, Tuple, Optional
from scipy.optimize import minimize
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

# --- DESIGN SPACE ---
DESIGN_SPACE = [
    "Positive electrode thickness [m]",
    "Negative electrode thickness [m]",
    "Positive electrode porosity",
    "Negative electrode porosity",
    "Positive particle radius [m]",
    "Negative particle radius [m]",
    "Separator porosity",
    "carbon_fraction"
]

# --- PHYSICS MODELS ---

def carbon_percolation_conductivity(fraction: float, base_cond: float = 100.0) -> float:
    phi_c = 0.03
    if fraction <= phi_c:
        return 1e-6
    return base_cond * np.power(max((fraction - phi_c) / (1 - phi_c), 0.01), 1.8)

class ParamTransform:
    def __init__(self, base_values: pybamm.ParameterValues):
        self.values_dict = dict(base_values)

    def _apply_scaling(self, key: str, factor: float):
        original = self.values_dict.get(key)
        if original is None: return
        if callable(original):
            def scaled_func(*args, f=factor, orig=original, **kwargs):
                return orig(*args, **kwargs) * f
            self.values_dict[key] = scaled_func
        else:
            self.values_dict[key] *= factor

    def apply_physics_deltas(self, deltas: Dict[str, Any]):
        if "thermodynamic" in deltas:
            d = deltas["thermodynamic"]
            if "voltage_boost" in d:
                ocp = self.values_dict.get("Positive electrode OCP [V]")
                if callable(ocp):
                    def shifted_ocp(sto, b=d["voltage_boost"], f=ocp):
                        return f(sto) + b
                    self.values_dict["Positive electrode OCP [V]"] = shifted_ocp
                else:
                    self.values_dict["Positive electrode OCP [V]"] += d["voltage_boost"]
            if "initial_sodium_loss_delta" in d:
                self.values_dict["Initial concentration in negative electrode [mol.m-3]"] *= (1.0 + d["initial_sodium_loss_delta"])

        if "transport" in deltas:
            d = deltas["transport"]
            if "diffusivity_log_delta" in d:
                self._apply_scaling("Positive particle diffusivity [m2.s-1]", np.exp(d["diffusivity_log_delta"]))
            if "conductivity_log_delta" in d:
                self._apply_scaling("Positive electrode conductivity [S.m-1]", np.exp(d["conductivity_log_delta"]))
            if "electrolyte_conductivity_log_delta" in d:
                self._apply_scaling("Electrolyte conductivity [S.m-1]", np.exp(d["electrolyte_conductivity_log_delta"]))
            if "electrolyte_diffusivity_log_delta" in d:
                self._apply_scaling("Electrolyte diffusivity [m2.s-1]", np.exp(d["electrolyte_diffusivity_log_delta"]))

        if "kinetic" in deltas:
            d = deltas["kinetic"]
            if "exchange_current_log_delta" in d:
                self._apply_scaling("Positive electrode exchange-current density [A.m-2]", np.exp(d["exchange_current_log_delta"]))
            if "sei_growth_log_delta" in d:
                self._apply_scaling("SEI reaction exchange current density [A.m-2]", np.exp(d["sei_growth_log_delta"]))
            if "sei_resistivity_log_delta" in d:
                 self._apply_scaling("SEI resistivity [Ohm.m]", np.exp(d["sei_resistivity_log_delta"]))

    def apply_design_vector(self, x: np.ndarray, names: List[str]):
        for val, name in zip(x, names):
            if name == "carbon_fraction":
                self.values_dict["Positive electrode conductivity [S.m-1]"] = carbon_percolation_conductivity(val)
            else:
                self.values_dict[name] = val

    def get_parameter_values(self) -> pybamm.ParameterValues:
        if "Cell volume [m3]" not in self.values_dict:
            self.values_dict["Cell volume [m3]"] = 0.13 * 0.07 * 0.01
        if "Cell cooling surface area [m2]" not in self.values_dict:
            self.values_dict["Cell cooling surface area [m2]"] = 0.02
        return pybamm.ParameterValues(self.values_dict)

# --- OPTIMIZATION ENGINE ---

class OptimizerEngine:
    def __init__(self, base_params: pybamm.ParameterValues):
        self.base_params = base_params
        try:
             self.model = pybamm.lithium_ion.SPM()
        except:
             self.model = None

    def simulate(self, params: pybamm.ParameterValues) -> Dict[str, float]:
        if self.model is None: return {"energy": 0, "success": False}
        try:
            inputs = {"Current [A]": params["Nominal cell capacity [A.h]"]}
            sim = pybamm.Simulation(self.model, parameter_values=params)
            sol = sim.solve([0, 3600], inputs=inputs)

            v = sol["Terminal voltage [V]"].data
            cap = sol["Discharge capacity [A.h]"].data[-1]

            trapz_func = getattr(np, "trapezoid", getattr(np, "trapz", None))
            energy = trapz_func(v * sol["Current [A]"].data, sol["Time [s]"].data) / 3600

            v_initial = v[0]
            v_step = v[1] if len(v) > 1 else v[0]
            curr = abs(sol["Current [A]"].data[0])
            r_int = abs(v_initial - v_step) / (curr + 1e-6)

            t_max = 298.15
            thermal_margin = 333.15 - t_max

            sei_growth = 0.0
            stress_proxy = params["Positive particle radius [m]"] * 1e5 * cap
            n_cycles = 1000 * np.exp(- (sei_growth * 1e8 + stress_proxy * 0.1))

            return {
                "energy": float(energy),
                "capacity": float(cap),
                "avg_voltage": float(np.mean(v)),
                "internal_resistance": float(r_int),
                "thermal_margin": float(thermal_margin),
                "cycle_life": float(n_cycles),
                "success": True
            }
        except Exception:
            return {"energy": 0, "success": False}

    def pybamm_loss(self, metrics: Dict[str, float]) -> float:
        if not metrics.get("success", False):
            return 1e6
        score = (1.0 * metrics["energy"] +
                 0.5 * metrics["thermal_margin"] +
                 0.01 * metrics["cycle_life"] -
                 50.0 * metrics["internal_resistance"])
        return -score

    def optimize(self, material_deltas: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, float]]:
        bounds = [
            (30e-6, 150e-6), (30e-6, 150e-6),
            (0.2, 0.5), (0.2, 0.5),
            (1e-7, 10e-6), (1e-7, 10e-6),
            (0.3, 0.7),
            (0.02, 0.15)
        ]

        def objective(x):
            pt = ParamTransform(self.base_params)
            pt.apply_physics_deltas(material_deltas)
            pt.apply_design_vector(x, DESIGN_SPACE)
            res = self.simulate(pt.get_parameter_values())
            return self.pybamm_loss(res)

        x0 = np.array([0.5 * (b[0] + b[1]) for b in bounds])
        res = minimize(objective, x0, bounds=bounds, method='L-BFGS-B', options={'maxiter': 5})

        final_pt = ParamTransform(self.base_params)
        final_pt.apply_physics_deltas(material_deltas)
        final_pt.apply_design_vector(res.x, DESIGN_SPACE)
        metrics = self.simulate(final_pt.get_parameter_values())
        return res.x, metrics

def run_workflow():
    from src.cell_optimization.material_opt import MaterialMappingEngine, MaterialCategory
    from src.cell_optimization.chem_regularization import derive_coupled_deltas, regularize_salt_props, regularize_functionalization

    engine = MaterialMappingEngine()
    db, bases = engine.run()
    if not bases: return

    opt = OptimizerEngine(pybamm.ParameterValues(engine.base_params))

    all_results = []
    cathodes = db[MaterialCategory.CATHODE_DOPANT] or [None]
    salts = db[MaterialCategory.SALT] or [None]
    funcs = db[MaterialCategory.FUNCTIONALIZATION] or [None]

    print(f"Iterating through material combinations...")
    for cat in cathodes[:2]: # Limit for demo speed
        for salt in salts[:2]:
            for func in funcs[:1]:
                deltas = {}
                if cat:
                    d = derive_coupled_deltas(bases["cathode"]["properties"], cat.properties,
                                            bases["cathode"]["formula"], cat.composition)
                    for k, v in d.items(): deltas.setdefault(k, {}).update(v)
                if salt:
                    d = regularize_salt_props(bases["salt"]["solution"], salt.properties)
                    for k, v in d.items(): deltas.setdefault(k, {}).update(v)
                if func:
                    d = regularize_functionalization(func.properties)
                    for k, v in d.items(): deltas.setdefault(k, {}).update(v)

                x_opt, metrics = opt.optimize(deltas)
                if metrics.get("success"):
                     all_results.append({
                        "cat": cat, "salt": salt, "func": func,
                        "x_opt": x_opt, "metrics": metrics, "deltas": deltas
                     })

    if not all_results:
        print("No successful optimization runs.")
        return

    # Rank by Energy
    all_results.sort(key=lambda x: x["metrics"]["energy"], reverse=True)
    best = all_results[0]

    output = {
        "materials": {
            "cathode": {
                "name": best["cat"].name if best["cat"] else "Base",
                "formula": best["cat"].composition if best["cat"] else bases["cathode"]["formula"]
            },
            "electrolyte": {
                "salt": best["salt"].name if best["salt"] else "Base",
                "functionalization": best["func"].name if best["func"] else "None"
            }
        },
        "cell_parameters": {
            "voltage": round(best["metrics"].get("avg_voltage", 0), 3),
            "energy_density": round(best["metrics"].get("energy", 0) * 15, 2),
            "internal_resistance": round(best["metrics"].get("internal_resistance", 0), 4),
            "thermal_margin": round(best["metrics"].get("thermal_margin", 0), 2),
            "cycle_life": int(best["metrics"].get("cycle_life", 0))
        },
        "design_specs": dict(zip(DESIGN_SPACE, best["x_opt"].tolist())),
        "combined_deltas": best["deltas"]
    }

    print("\nFINAL SYSTEM OUTPUT (RANKED BEST):")
    print(json.dumps(output, indent=2))
    return output

if __name__ == "__main__":
    run_workflow()
