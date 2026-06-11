import numpy as np
import pybamm
import logging
import math
import json
from typing import Dict, List, Any, Optional
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values
from src.cell_optimization.material_opt import MaterialMappingEngine, MaterialCandidate

logging.basicConfig(level=logging.INFO)

class ParamTransform:
    """Pure parameter wrapper to prevent dictionary mutation leakage."""
    def __init__(self, base_values):
        self.base = base_values.copy()
        self.multiplier_map = {}
        self.additive_map = {}

    def add_multiplier(self, name, val):
        self.multiplier_map[name] = self.multiplier_map.get(name, 1.0) * val

    def add_additive(self, name, val):
        self.additive_map[name] = self.additive_map.get(name, 0.0) + val

    def evaluate(self):
        params = pybamm.ParameterValues(self.base)
        for name, m in self.multiplier_map.items():
            if name in params:
                base = params[name]
                if callable(base):
                    params[name] = (lambda *args, b=base, mult=m, **kwargs: b(*args, **kwargs) * mult)
                else:
                    params[name] = base * m
        for name, a in self.additive_map.items():
            if name in params:
                base = params[name]
                if callable(base):
                    params[name] = (lambda *args, b=base, add=a, **kwargs: b(*args, **kwargs) + add)
                else:
                    params[name] = base + a
        return params

def get_y(params: pybamm.ParameterValues, horizon=1800) -> np.ndarray:
    """Runs PyBaMM simulation and extracts composite performance metrics."""
    options = {"thermal": "isothermal"}
    model = pybamm.lithium_ion.SPM(options)
    solver = pybamm.CasadiSolver(mode="safe")

    if "Cell volume [m3]" not in params:
        params["Cell volume [m3]"] = 0.130 * 0.070 * 0.0003

    sim = pybamm.Simulation(model, parameter_values=params, solver=solver)

    try:
        sl = sim.solve([0, horizon], inputs={"Current [A]": 1.0})
        v_entries = sl["Terminal voltage [V]"].entries
        i_entries = sl["Current [A]"].entries
        t_entries = sl.t
        v_final = float(v_entries[-1])
        trapezoid = getattr(np, "trapezoid", getattr(np, "trapz", None))
        energy_wh = np.abs(trapezoid(v_entries * i_entries, t_entries)) / 3600.0
        capacity_ah = np.abs(trapezoid(i_entries, t_entries)) / 3600.0
        power_w = np.mean(v_entries * i_entries)
        eff = float(np.mean(sl["X-averaged negative electrode transport efficiency"].entries))
        # Degradation proxy: max interfacial current density
        j_max = float(np.max(np.abs(sl["X-averaged negative electrode interfacial current density [A.m-2]"].entries)))

        # Composite Result Vector: [Voltage, Energy, Capacity, Power, Efficiency, -Degradation]
        return np.array([v_final, energy_wh, capacity_ah, power_w, eff, -j_max])
    except Exception as e:
        logging.warning(f"Simulation failed: {e}")
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, -1e6])

def get_params_for_theta(theta, materials, design_keys):
    transform = ParamTransform(get_parameter_values())
    for i, key in enumerate(design_keys):
        if key in transform.base:
            transform.base[key] = theta[i]

    # Material-specific composition mapping
    if "Positive electrode conductive carbon fraction" in design_keys:
        carbon_idx = design_keys.index("Positive electrode conductive carbon fraction")
        # Baseline conductivity 50 S/m is for 0.08 fraction
        transform.add_multiplier("Positive electrode conductivity [S.m-1]", theta[carbon_idx] / 0.08)

    for m in materials:
        deltas = m.to_pybamm_delta()
        for name, (mode, val) in deltas.items():
            if mode == "multiplier": transform.add_multiplier(name, val)
            else: transform.add_additive(name, val)
    return transform.evaluate()

def compute_sensitivity(theta: np.ndarray, materials: List[MaterialCandidate], design_keys: List[str]) -> np.ndarray:
    """Computes the parameter Jacobian S_{ij} = dy_i / dtheta_j for composite metrics."""
    y_base = get_y(get_params_for_theta(theta, materials, design_keys))
    n_y = len(y_base)
    n_theta = len(theta)
    S = np.zeros((n_y, n_theta))
    eps = 1e-4

    for j in range(n_theta):
        th_plus = theta.copy()
        h = eps * (abs(theta[j]) + 1e-9)
        th_plus[j] += h
        y_plus = get_y(get_params_for_theta(th_plus, materials, design_keys))
        S[:, j] = (y_plus - y_base) / h

    return S

def pybamm_loss(y: np.ndarray) -> float:
    """Tightened composite objective function."""
    # Weights for: [Voltage, Energy, Capacity, Power, Efficiency, Stability_Proxy]
    weights = np.array([-1.0, -10.0, -10.0, -2.0, -1.0, -0.001])
    return float(np.dot(y, weights))

def optimize(materials_db: Dict[str, List[MaterialCandidate]]):
    """
    Optimization loop over expanded design space.
    Structural (Lc, La, ec, ea, esep, tau, loading, rp).
    Material (NFPP fraction, Carbon fraction, Electrolyte).
    """
    design_keys = [
        "Positive electrode thickness [m]",                # Lc
        "Negative electrode thickness [m]",                # La
        "Positive electrode porosity",                     # ec
        "Negative electrode porosity",                     # ea
        "Separator porosity",                             # esep
        "Positive electrode Bruggeman coefficient (electrolyte)", # tau
        "Negative electrode Bruggeman coefficient (electrolyte)", # tau
        "Positive electrode active material volume fraction", # NFPP loading
        "Positive particle radius [m]",                    # rp
        "Negative particle radius [m]",                    # rp
        "Typical electrolyte concentration [mol.m-3]",      # Material
        "Positive electrode conductive carbon fraction"     # Material
    ]
    # Initial guess
    theta = np.array([1e-4, 1.2e-4, 0.3, 0.3, 0.5, 1.5, 1.5, 0.65, 1e-6, 5e-6, 1000.0, 0.08])

    best_overall_loss = float('inf')
    best_config = {}

    cathodes = materials_db.get("Cathode_Dopant", []) or [None]
    salts = materials_db.get("Salt", []) or [None]
    funcs = materials_db.get("Functionalization", []) or [None]

    for cathode in cathodes:
        for salt in salts:
            for func in funcs:
                selected_materials = [m for m in [cathode, salt, func] if m is not None]
                curr_theta = theta.copy()

                for i in range(2):
                    S = compute_sensitivity(curr_theta, selected_materials, design_keys)
                    weights = np.array([-1.0, -10.0, -10.0, -2.0, -1.0, -0.001])
                    grad = weights @ S

                    update = 0.05 * grad * curr_theta
                    curr_theta -= update

                    # Physical Manifold Constraints
                    curr_theta[0:2] = np.clip(curr_theta[0:2], 5e-5, 3e-4) # thickness
                    curr_theta[2:5] = np.clip(curr_theta[2:5], 0.2, 0.7)  # porosity
                    curr_theta[5:7] = np.clip(curr_theta[5:7], 1.0, 4.0)  # tortuosity
                    curr_theta[7] = np.clip(curr_theta[7], 0.4, 0.9)     # loading
                    curr_theta[8:10] = np.clip(curr_theta[8:10], 1e-7, 1e-5) # radius
                    curr_theta[10] = np.clip(curr_theta[10], 500.0, 2000.0) # electrolyte
                    curr_theta[11] = np.clip(curr_theta[11], 0.01, 0.2)  # carbon fraction

                    # Composition constraint: porosity + loading + carbon < 1.0
                    total_vol = curr_theta[2] + curr_theta[7] + curr_theta[11]
                    if total_vol > 0.95:
                        scale = 0.95 / total_vol
                        curr_theta[2] *= scale
                        curr_theta[7] *= scale
                        curr_theta[11] *= scale

                final_y = get_y(get_params_for_theta(curr_theta, selected_materials, design_keys))
                loss = pybamm_loss(final_y)

                if loss < best_overall_loss:
                    best_overall_loss = loss
                    best_config = {
                        "materials": {
                            "cathode": cathode.name if cathode else "Base",
                            "electrolyte": f"{salt.name if salt else 'Base'} + {func.name if func else 'None'}"
                        },
                        "cell_parameters": dict(zip(design_keys, curr_theta.tolist()))
                    }

    return best_config

if __name__ == "__main__":
    engine = MaterialMappingEngine()
    materials = engine.run()
    result = optimize(materials)
    print(json.dumps(result, indent=2))
