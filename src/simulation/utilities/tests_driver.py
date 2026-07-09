"""Electrochemical-Thermal Driver"""

import numpy as np
import traceback
import copy
import pybamm
import hashlib
from typing import Any, Dict, Optional


from nfpp_sodium_ion.src.cell_parameters.parameter_builder import get_parameter_values

class ElectrochemicalThermalDriverModel:
    """DFN Electrochemical-Thermal Driver with component caching."""

    def __init__(self, name: str = "DFN Electrochemical-Thermal Driver"):
        self.name = name
        self.model_type = "DFN"
        self._cache = {}
        self._interp_cache = {}
        self.solver = pybamm.CasadiSolver(mode="safe")

    def _get_processed_components(self, param: pybamm.ParameterValues):
        # Cache key based on geometry-affecting parameters and options
        geometry_keys = [
            "Positive electrode thickness [m]",
            "Negative electrode thickness [m]",
            "Separator thickness [m]",
            "Positive particle radius [m]",
            "Negative particle radius [m]"
        ]
        key = tuple(float(param.get(k, 0)) for k in geometry_keys)

        if key in self._cache:
            return self._cache[key]

        options = {
            "thermal": "x-full",
            "SEI": "reaction limited",
            "SEI porosity change": "true",
            "loss of active material": "stress-driven"
        }
        try:
            model = pybamm.sodium_ion.DFN(options=options)
        except AttributeError:
            model = pybamm.lithium_ion.DFN(options=options)

        geometry = copy.deepcopy(model.default_geometry)
        param.process_geometry(geometry)
        mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)
        disc = pybamm.Discretisation(mesh, model.default_spatial_methods)

        self._cache[key] = {"model": model, "geometry": geometry, "mesh": mesh, "disc": disc}
        return self._cache[key]

    def build_model(self, parameter_updates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if pybamm is None:
            raise ImportError("pybamm is required for the electrochemical-thermal driver model")

        param = get_parameter_values(updates=parameter_updates)
        components = self._get_processed_components(param)
        return {"model": components["model"], "parameter_values": param, "components": components}

    def get_varying_c_rate_profile(self, base_c_rate: float, duration: float, n_points: int = 100) -> np.ndarray:
        """Generates a varying C-rate profile (sine-wave oscillation around base)."""
        t = np.linspace(0, duration, n_points)
        # Sine oscillation between 0.5x and 1.5x of base_c_rate
        profile = base_c_rate * (1.0 + 0.5 * np.sin(2 * np.pi * t / (duration / 2)))
        return profile

    def simulate(self, model_dict: Dict[str, Any], times: Optional[list] = None, current_function=None, experiment: Optional[Any] = None) -> Dict[str, Any]:
        if pybamm is None:
            raise ImportError("pybamm is required for simulation")

        model = model_dict["model"]
        # Use copy to avoid mutation (Issue 15)
        param = model_dict["parameter_values"].copy()
        components = model_dict.get("components")

        if experiment is not None:
            # Standard API usage (Issue 2)
            sim = pybamm.Simulation(model, parameter_values=param, experiment=experiment, solver=self.solver)
            solution = sim.solve()
        else:
            if current_function is not None:
                if isinstance(current_function, (list, np.ndarray)):
                    # Use high-fidelity interpolation for varying current profile (Issue 3, 4)
                    t_eval = np.array(times)
                    from scipy.interpolate import PchipInterpolator

                    # Cache interpolator if the profile is reusable
                    profile_key = hashlib.md5(np.array(current_function).tobytes()).hexdigest()
                    if profile_key not in self._interp_cache:
                         t_orig = np.linspace(t_eval[0], t_eval[-1], len(current_function))
                         self._interp_cache[profile_key] = PchipInterpolator(t_orig, current_function)

                    interp_obj = self._interp_cache[profile_key]
                    current_profile = interp_obj(t_eval)

                    param["Current function [A]"] = pybamm.Interpolant(t_eval, current_profile, pybamm.t)
                else:
                    param["Current function [A]"] = current_function

            sim = pybamm.Simulation(model, parameter_values=param, solver=self.solver)
            solution = sim.solve(times)

        cap_ah = solution["Discharge capacity [A.h]"].entries
        nom_cap = param["Nominal cell capacity [A.h]"]
        soc = 1.0 - (cap_ah / nom_cap)

        return {
            "solution": solution,
            "times": solution["Time [s]"].entries,
            "soc_trajectory": soc,
            "soh_trajectory": solution["Loss of active material in negative electrode [%]"].entries,
            "temperature": solution["Cell temperature [K]"].entries,
            "heat_generation_rate": solution["Total heating [W.m-3]"].entries,
            "terminal_voltage": solution["Terminal voltage [V]"].entries,
        }
