import re
import math
import numpy as np
from typing import Dict, Set, List

ELEMENT_UNIVERSE = ["Na", "Fe", "P", "O", "Mn", "Cr", "Ni"]

def parse_formula_counts(formula: str) -> Dict[str, float]:
    """
    Parses a chemical formula into element counts.
    Example: 'Na4Fe3P4O15' -> {'Na': 4.0, 'Fe': 3.0, 'P': 4.0, 'O': 15.0}
    """
    # This matches Element followed by optional count (including decimals)
    matches = re.findall(r'([A-Z][a-z]?)(\d*(?:\.\d+)?)', formula)
    counts = {}
    for element, count in matches:
        counts[element] = float(count) if count else 1.0
    return counts

def stoich_vector(formula: str) -> np.ndarray:
    """
    Converts formula to a normalized stoichiometric vector x.
    """
    counts = parse_formula_counts(formula)
    v = np.zeros(len(ELEMENT_UNIVERSE))
    total = sum(counts.values())
    for i, e in enumerate(ELEMENT_UNIVERSE):
        v[i] = counts.get(e, 0.0)
    return v / (total + 1e-12)

def compute_chemical_realization(base_formula: str, proxy_formula: str,
                                 base_props: Dict[str, float],
                                 proxy_props: Dict[str, float]) -> float:
    """
    Computes a realization factor [0, 1] based on composition distance,
    structural, and electronic similarity.
    """
    # 1. Chemical Similarity (Stoichiometric Vector Norm)
    r_chem = math.exp(-np.linalg.norm(stoich_vector(base_formula) - stoich_vector(proxy_formula)))

    # 2. Structural Similarity (Volume-per-atom mismatch)
    v_b = base_props["volume_per_atom"]
    v_p = proxy_props["volume_per_atom"]
    r_struct = math.exp(-abs(v_p - v_b) / (v_b + 1e-9))

    # 3. Electronic Similarity (Bandgap mismatch)
    eg_b = base_props["band_gap"]
    eg_p = proxy_props["band_gap"]
    epsilon = 1e-6
    r_electronic = math.exp(-abs(eg_p - eg_b) / (eg_b + epsilon))

    return r_chem * r_struct * r_electronic

# Calibrated Projection Matrix M (Representative of Polyanionic Physics)
# Rows: [Voltage, ln(Diffusivity), Conductivity, Reaction Rate]
# Cols: [dEf, dVatom, dEg, dEformation_total]
M_PROJECTION = np.array([
    [-0.2,  0.0,   0.0, -0.05], # Voltage
    [ 0.1,  1.2,  -0.5,  0.0],  # ln(Diffusivity)
    [ 0.0,  0.0,  -2.0,  0.0],  # ln(Conductivity)
    [-0.1,  0.1,  -0.1, -0.5]   # ln(Reaction Rate)
])

def derive_coupled_deltas(base_props: Dict[str, float],
                          proxy_props: Dict[str, float],
                          base_v: float,
                          realization: float) -> Dict[str, float]:
    """
    Derives correlated performance perturbations using a vector latent physics model.
    """
    # Latent Physics Vector z
    z = np.array([
        proxy_props["formation_energy"] - base_props["formation_energy"], # dEf (per atom proxy)
        proxy_props["volume_per_atom"] - base_props["volume_per_atom"],   # dVatom
        proxy_props["band_gap"] - base_props["band_gap"],                # dEg
        (proxy_props["formation_energy"] * proxy_props.get("natoms", 1)) -
        (base_props["formation_energy"] * base_props.get("natoms", 1))   # Total formation energy diff proxy
    ])

    # Multi-dimensional latent physics projection
    dy = M_PROJECTION @ z

    # Performance projections (mapped back to multipliers and additives)
    voltage_boost = dy[0] * realization * (base_v / 3.2)
    # Diffusivity follows exponential scaling
    diffusivity_mult = math.exp(dy[1] * realization)

    return {
        "voltage_boost": float(voltage_boost),
        "diffusivity_mult": float(max(0.1, min(10.0, diffusivity_mult)))
    }
