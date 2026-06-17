import re
import math
import numpy as np
from typing import Dict, Set, List, Optional, Any
from pymatgen.core import Composition

KT = 0.0259 # eV at 300K

def thermo_norm(x, ref=0.0):
    # Boltzmann scaling: nondimensionalizing energy residuals
    return (x - ref) / KT

def stoich_norm(formula: str) -> dict:
    try:
        comp = Composition(formula)
        total = sum(comp.values())
        if total == 0: return {}
        return {k: v / total for k, v in comp.items()}
    except Exception:
        return {}

def geom_norm(props, base_props):
    vp = props.get("volume_per_atom", 1.0)
    vb = base_props.get("volume_per_atom", 1.0)
    return {
        "volume_ratio": vp / vb,
        "strain": (vp - vb) / vb
    }

def compute_chemical_realization(
    base_formula: str,
    proxy_formula: str,
    base_props: Dict[str, float],
    proxy_props: Dict[str, float]
) -> float:
    """How safely can this proxy perturb the base material?"""
    try:
        c_base = stoich_norm(base_formula)
        c_proxy = stoich_norm(proxy_formula)
        shared = set(c_base) & set(c_proxy)
        overlap = sum(min(c_base.get(e, 0), c_proxy.get(e, 0)) for e in shared)

        # Physical Residual Mismatch (nondimensionalized)
        dE = abs(thermo_norm(proxy_props.get("formation_energy", 0), base_props.get("formation_energy", 0)))
        dV = abs(geom_norm(proxy_props, base_props)["strain"]) / 0.05

        # Realization score: higher means proxy is chemically similar to base
        realization = np.tanh(overlap * 3.0) * np.exp(-0.5 * (dE + dV))
        return float(np.clip(realization, 0.01, 1.0))
    except Exception:
        return 0.1

def derive_coupled_deltas(base_props, proxy_props, base_formula, proxy_formula) -> dict:
    # 2.3 Physical residuals
    dE = thermo_norm(proxy_props.get("formation_energy", 0), base_props.get("formation_energy", 0))
    # Stability improvement dS (positive means more stable)
    dS = (base_props.get("stability", 0) - proxy_props.get("stability", 0)) / KT
    dV = geom_norm(proxy_props, base_props)["strain"]

    # Realization Factor: Regularizes deltas for different chemistries
    R = compute_chemical_realization(base_formula, proxy_formula, base_props, proxy_props)

    # 2.4 Physically grounded coupling rules attenuated by Realization
    voltage_boost = -dE * KT * R
    Ea_base = 0.5 * abs(base_props.get("formation_energy", -1.0))
    Ea_proxy = 0.5 * abs(proxy_props.get("formation_energy", -1.0))
    conductivity_log_delta = (Ea_base - Ea_proxy) / KT * R
    diffusivity_log_delta = (dV - 0.1 * abs(dE)) * R
    reaction_rate_log_delta = (0.1 * dE + 0.1 * dS) * R
    stability_shift = dS * R

    return {
        "thermodynamic": {
            "voltage_boost": float(voltage_boost),
            "stability_shift": float(stability_shift)
        },
        "kinetic": {
            "exchange_current_log_delta": float(reaction_rate_log_delta)
        },
        "transport": {
            "diffusivity_log_delta": float(diffusivity_log_delta),
            "conductivity_log_delta": float(conductivity_log_delta)
        },
        "structural": {
            "strain": float(dV * R)
        }
    }

def regularize_salt_props(base_salt_formula: str, candidate_salt_formula: str, base_salt_props: Dict[str, float], candidate_salt_props: Dict[str, float]) -> Dict[str, Any]:
    """Derive electrolyte deltas attenuated by chemical realization."""
    try:
        R = compute_chemical_realization(base_salt_formula, candidate_salt_formula, base_salt_props, candidate_salt_props)
        Ea_base = 0.3 * abs(base_salt_props.get("formation_energy", -1.0))
        Ea_can = 0.3 * abs(candidate_salt_props.get("formation_energy", -1.0))
        dEa_norm = (Ea_base - Ea_can) / KT
        v_can = candidate_salt_props.get("volume_per_atom", 1.0)
        v_base = base_salt_props.get("volume_per_atom", 1.0)
        dV = (v_can - v_base) / v_base

        return {
            "transport": {
                "electrolyte_conductivity_log_delta": float(dEa_norm * R),
                "electrolyte_diffusivity_log_delta": float(-1.0 * dV * R)
            }
        }
    except Exception: return {"transport": {}}

def regularize_functionalization(base_int_formula: str, candidate_func_formula: str, base_props: Dict[str, float], candidate_props: Dict[str, float]) -> Dict[str, Any]:
    """
    MTMS Functionalization integrated via latent degradation scalar theta_surf.
    θ_surf couples electrochemistry to mechanics.
    """
    try:
        R = compute_chemical_realization(base_int_formula, candidate_func_formula, base_props, candidate_props)
        dS = (base_props.get("stability", 0) - candidate_props.get("stability", 0)) / KT

        # 1. Latent degradation scalar theta_surf based on stability residuals
        # Clamped in [0, 1] as requested
        # Improved stability (positive dS) leads to LOWER theta_surf (less degradation)
        theta_surf = np.clip(1.0 - np.exp(-abs(dS) * R), 0.0, 1.0)

        # 2. Electrochemical degradation channels (j0 suppression, Diffusivity reduction)
        # k1, k2 are sensitivity coefficients
        k1, k2, beta = 2.0, 0.5, 0.3

        return {
            "kinetic": {
                "exchange_current_log_delta": float(-k1 * theta_surf) # j0_eff = j0 * exp(-k1 * theta)
            },
            "transport": {
                "negative_diffusivity_delta": float(-k2 * theta_surf) # D_eff = D0 * (1 - k2 * theta)
            },
            "mechanical": {
                "modulus_degradation_factor": float(1.0 - beta * theta_surf) # E_eff = E0 * (1 - beta * theta)
            }
        }
    except Exception: return {"kinetic": {}, "transport": {}, "mechanical": {}}

def mechanical_stability_metric(stresses: Optional[List[float]] = None) -> float:
    """Von Mises yield proxy for mechanical stability."""
    if stresses and len(stresses) >= 2:
        s1 = stresses[0]
        s2 = stresses[1]
        s3 = 0.0
        von_mises = np.sqrt(0.5 * ((s1-s2)**2 + (s2-s3)**2 + (s3-s1)**2))
        return float(-von_mises)
    elif stresses:
        return float(-max(np.abs(stresses)))
    return -1e-6
