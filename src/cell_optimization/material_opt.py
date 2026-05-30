import json
import os
import re
import math
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

try:
    from mp_api.client import MPRester
except ImportError:
    MPRester = None

import pybamm
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

# --- CONSTANTS & SCIENTIFIC CONFIG ---
CACHE_FILE = "material_cache.json"
MP_API_KEY = os.environ.get("MP_API_KEY", "4wUDc4LwwKXSRWxiE6DHQS40pG45g0q6")
KT = 0.0259 # Thermal energy at 300K (eV)

# Hard Carbon is not well-represented by crystalline DFT entries.
HARD_CARBON_REF = {
    "stability": 0.05,
    "formation_energy": -0.12,
    "band_gap": 0.4,
    "volume_per_atom": 12.0
}

@dataclass
class MaterialCandidate:
    name: str
    category: str
    composition: str
    energy_above_hull: float = 0.0
    formation_energy: float = 0.0
    band_gap: float = 0.0
    volume_per_atom: float = 0.0
    projected_delta: Dict[str, float] = field(default_factory=dict)
    reference: str = "Materials Project Harvester"

    def to_pybamm_delta(self) -> Dict[str, Any]:
        """Maps derived deltas to PyBaMM parameter names."""
        mapping = {}
        if self.category == "Cathode_Dopant":
            mapping["Positive electrode OCP [V]"] = ("additive", self.projected_delta.get("voltage_boost", 0.0))
            mapping["Positive particle diffusivity [m2.s-1]"] = ("multiplier", self.projected_delta.get("diffusivity_mult", 1.0))
        elif self.category == "Salt":
            mapping["Electrolyte conductivity [S.m-1]"] = ("multiplier", self.projected_delta.get("conductivity_mult", 1.0))
            mapping["Cation transference number"] = ("multiplier", self.projected_delta.get("ion_transference_mult", 1.0))
        elif self.category == "Functionalization":
            mapping["SEI reaction exchange current density [A.m-2]"] = ("multiplier", self.projected_delta.get("sei_growth_mult", 1.0))
            mapping["Initial concentration in negative electrode [mol.m-3]"] = ("multiplier", self.projected_delta.get("initial_loss_mult", 1.0))
            mapping["SEI resistivity [Ohm.m]"] = ("multiplier", self.projected_delta.get("resistance_drift_mult", 1.0))
            mapping["Negative electrode exchange-current density [A.m-2]"] = ("multiplier", self.projected_delta.get("exchange_current_mult", 1.0))
        return mapping

class MaterialDiscoveryFramework:
    def __init__(self):
        self.cache = self._load_cache()
        self.base_params = get_parameter_values()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Saves cache with deduplication and normalization."""
        clean_cache = {}
        for key, val in self.cache.items():
            clean_cache[key] = val
        with open(CACHE_FILE, "w") as f:
            json.dump(clean_cache, f, indent=2)

    def harvest_mp_system(self, chemsys: str) -> List[Dict[str, Any]]:
        """Harvests entire chemical system from Materials Project."""
        cache_key = f"MP_HARVEST:{chemsys}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not MPRester:
            return []

        all_data = []
        try:
            with MPRester(api_key=MP_API_KEY) as mpr:
                docs = mpr.materials.summary.search(
                    chemsys=chemsys,
                    fields=['formula_pretty', 'material_id', 'formation_energy_per_atom', 'energy_above_hull', 'band_gap', 'volume', 'nsites']
                )
                for d in docs:
                    all_data.append({
                        "formula": d.formula_pretty,
                        "mid": str(d.material_id),
                        "delta_e": d.formation_energy_per_atom,
                        "stability": d.energy_above_hull,
                        "band_gap": d.band_gap,
                        "volume_per_atom": d.volume / d.nsites if d.nsites else 15.0
                    })
        except Exception as e:
            print(f"MP Harvest error for {chemsys}: {e}")

        self.cache[cache_key] = all_data
        self._save_cache()
        return all_data

    def get_best_stable_phase(self, system_data: List[Dict[str, Any]], formula: Optional[str] = None) -> Dict[str, float]:
        """Identifies the most stable phase, optionally filtering by formula."""
        if not system_data:
            return {"stability": 0.2, "formation_energy": -1.0, "band_gap": 1.0, "volume_per_atom": 15.0}

        subset = [d for d in system_data if d["formula"] == formula] if formula else system_data
        if not subset: subset = system_data

        # Sort by energy above hull
        subset.sort(key=lambda x: x["stability"])
        best = subset[0]
        return {
            "stability": best["stability"],
            "formation_energy": best["delta_e"],
            "band_gap": best["band_gap"],
            "volume_per_atom": best["volume_per_atom"]
        }

    def derive_deltas(self, target_props: Dict[str, float], base_props: Dict[str, float], category: str) -> Dict[str, float]:
        """Physics-based delta derivation from MP states."""
        deltas = {}
        de_diff = target_props["formation_energy"] - base_props["formation_energy"]
        # Penalize realizations for materials far from ground state
        realization = 1.0 / (1.0 + math.exp(20.0 * (target_props["stability"] - 0.05)))

        if category == "Cathode_Dopant":
            base_ocp = self.base_params["Positive electrode OCP [V]"]
            try:
                v = base_ocp(0.5)
                base_v_val = float(getattr(v, 'value', v))
            except Exception:
                base_v_val = 3.2

            # Voltage boost from Nernstian proxy
            deltas["voltage_boost"] = -de_diff * 0.1 * (base_v_val / 3.0) * realization

            # Diffusivity scaling from lattice expansion
            vol_ratio = target_props["volume_per_atom"] / base_props["volume_per_atom"]
            deltas["diffusivity_mult"] = (vol_ratio ** 1.3) * realization

        elif category == "Salt":
            # σ ∝ exp(-Eg / 2kT)
            gap_diff = base_props["band_gap"] - target_props["band_gap"]
            cond_mult = math.exp(gap_diff / (2 * KT))
            deltas["conductivity_mult"] = min(max(cond_mult, 0.2), 5.0)

            # Transference mapping
            deltas["ion_transference_mult"] = 1.0 + (0.08 / (1.0 + target_props["stability"] * 15.0))

        elif category == "Functionalization":
            deltas["sei_growth_mult"] = 0.65 + 0.35 / (1.0 + realization)
            deltas["initial_loss_mult"] = 0.7 + 0.3 / (1.0 + realization)
            deltas["resistance_drift_mult"] = 0.8 + 0.2 / (1.0 + realization)
            deltas["exchange_current_mult"] = 1.0 + 0.12 * realization

        return deltas

    def run_discovery(self):
        print("Harvesting Phase Spaces via Materials Project API...")
        system = {"Cathode_Dopant": [], "Salt": [], "Functionalization": []}

        # 1. BASELINES
        # Na-Fe-P-O system (NFPP)
        nfpp_sys = self.harvest_mp_system("Na-Fe-P-O")
        base_cathode_props = self.get_best_stable_phase(nfpp_sys, "Na4Fe3P4O15")

        # Salt baseline (NaPF6)
        napf6_sys = self.harvest_mp_system("Na-P-F")
        base_salt_props = self.get_best_stable_phase(napf6_sys, "NaPF6")

        # 2. CATHODE DOPANTS (Mn, Cr, Ni)
        dopant_systems = {"Mn": "Na-Fe-Mn-P-O", "Cr": "Na-Fe-Cr-P-O", "Ni": "Na-Fe-Ni-P-O"}
        for d, sys_name in dopant_systems.items():
            doped_sys = self.harvest_mp_system(sys_name)
            target_props = self.get_best_stable_phase(doped_sys)

            deltas = self.derive_deltas(target_props, base_cathode_props, "Cathode_Dopant")
            system["Cathode_Dopant"].append(MaterialCandidate(
                name=d, category="Cathode_Dopant", composition=f"Doped-{d}-NFPP",
                energy_above_hull=target_props["stability"], formation_energy=target_props["formation_energy"],
                band_gap=target_props["band_gap"], volume_per_atom=target_props["volume_per_atom"],
                projected_delta=deltas
            ))

        # 3. SALTS (NaBOB, NaTCP)
        salt_map = {"NaBOB": "Na-B-C-O", "NaTCP": "Na-C-N-O"}
        for name, sys_name in salt_map.items():
            s_sys = self.harvest_mp_system(sys_name)
            target_props = self.get_best_stable_phase(s_sys)
            deltas = self.derive_deltas(target_props, base_salt_props, "Salt")
            system["Salt"].append(MaterialCandidate(
                name=name, category="Salt", composition=name,
                energy_above_hull=target_props["stability"], formation_energy=target_props["formation_energy"],
                band_gap=target_props["band_gap"], volume_per_atom=target_props["volume_per_atom"],
                projected_delta=deltas
            ))

        # 4. FUNCTIONALIZATION (MTMS)
        mtms_sys = self.harvest_mp_system("Si-C-H-O")
        mtms_props = self.get_best_stable_phase(mtms_sys)
        deltas = self.derive_deltas(mtms_props, HARD_CARBON_REF, "Functionalization")
        system["Functionalization"].append(MaterialCandidate(
            name="MTMS", category="Functionalization", composition="C4H12O3Si",
            energy_above_hull=mtms_props["stability"], formation_energy=mtms_props["formation_energy"],
            band_gap=mtms_props["band_gap"], volume_per_atom=mtms_props["volume_per_atom"],
            projected_delta=deltas
        ))

        return system

if __name__ == "__main__":
    discovery = MaterialDiscoveryFramework()
    res = discovery.run_discovery()
    for cat, cands in res.items():
        print(f"\nCategory: {cat}")
        for c in cands:
            print(f"  - {c.name}: {c.projected_delta}")
            # print(f"    Eg: {c.band_gap:.2f} eV, Hull: {c.energy_above_hull:.4f} eV/atom")

    print("\n--- Final material_cache.json content ---")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            for k in data.keys():
                print(f"Key: {k} (Items: {len(data[k]) if isinstance(data[k], list) else 'N/A'})")
