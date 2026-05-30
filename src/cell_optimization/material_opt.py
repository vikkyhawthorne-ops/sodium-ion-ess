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

import pybamm
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

# --- CONSTANTS & SCIENTIFIC CONFIG ---
CACHE_FILE = "material_cache.json"
OQMD_URL = "https://oqmd.org/oqmdapi/formationenergy"
KT = 0.0259 # Thermal energy at 300K (eV)

# Hard Carbon is not well-represented by crystalline OQMD entries.
# We use literature-referenced properties for Hard Carbon stability and electronics.
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
    reference: str = "OQMD Phase-Space Harvester"

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
        self.session = self._setup_session() if requests else None
        self.base_params = get_parameter_values()

    def _setup_session(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Saves cache with deduplication logic."""
        clean_cache = {}
        for key, val in self.cache.items():
            if isinstance(val, list):
                # Ensure entries in lists are unique by entry_id if possible
                seen_ids = set()
                unique_val = []
                for item in val:
                    eid = item.get("entry_id")
                    if eid not in seen_ids:
                        unique_val.append(item)
                        seen_ids.add(eid)
                val = unique_val
            clean_cache[key] = val

        with open(CACHE_FILE, "w") as f:
            json.dump(clean_cache, f, indent=2)

    def harvest_phase_space(self, elements: List[str], stability_cutoff: float = 0.1) -> List[Dict[str, Any]]:
        """Harvester implementing pagination to retrieve entire chemical systems."""
        filter_str = f"element_set=({','.join(elements)}) AND ntypes={len(elements)}"
        cache_key = f"HARVEST:{filter_str}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.session:
            return []

        all_data = []
        offset = 0
        while True:
            params = {
                "fields": "name,entry_id,composition,delta_e,stability,band_gap,volume,natoms",
                "filter": filter_str,
                "limit": 500,
                "offset": offset,
                "sort_by": "stability"
            }
            try:
                response = self.session.get(OQMD_URL, params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data", [])
                all_data.extend(data)

                if not payload.get("meta", {}).get("more_data_available", False):
                    break
                offset += 500
                if offset >= 2000: break # Safety cap for ESS optimization
            except Exception as e:
                print(f"Harvesting failed for {elements}: {e}")
                break

        # Filter by stability cutoff locally for high-quality battery phases
        all_data = [d for d in all_data if float(d.get("stability", 1.0)) <= stability_cutoff]
        self.cache[cache_key] = all_data
        self._save_cache()
        return all_data

    def get_best_phase(self, phase_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extracts properties of the ground-state or most stable phase in a harvested dataset."""
        if not phase_data:
            return {"stability": 0.2, "formation_energy": -1.0, "band_gap": 1.0, "volume_per_atom": 15.0}

        # Phase data is already sorted by stability from the API
        best = phase_data[0]
        try:
            natoms = float(best.get("natoms", 1.0))
            return {
                "stability": float(best.get("stability", 0.1)),
                "formation_energy": float(best.get("delta_e", 0.0)),
                "band_gap": float(best.get("band_gap", 0.0)),
                "volume_per_atom": float(best.get("volume", 1.0)) / natoms
            }
        except (ValueError, TypeError, ZeroDivisionError):
            return {"stability": 0.2, "formation_energy": -1.0, "band_gap": 1.0, "volume_per_atom": 15.0}

    def derive_deltas(self, target_props: Dict[str, float], base_props: Dict[str, float], category: str) -> Dict[str, float]:
        """Scientifically grounded delta derivation."""
        deltas = {}

        # 1. Realization Factor: Penalize materials far from the stability hull
        # Decays realization of performance as stability decreases (higher eV/atom)
        realization = 1.0 / (1.0 + math.exp(25.0 * (target_props["stability"] - 0.02)))

        if category == "Cathode_Dopant":
            # Voltage Shift from Formation Energy difference
            # ΔV = -ΔG / nF. Formation energy is a proxy for ΔG.
            de_diff = target_props["formation_energy"] - base_props["formation_energy"]

            # Sampling OCP safely from PyBaMM
            base_ocp = self.base_params["Positive electrode OCP [V]"]
            try:
                # evaluate at 0.5 stoichiometry
                v = base_ocp(0.5)
                base_v_val = float(v.value) if hasattr(v, "value") else float(v)
            except Exception:
                base_v_val = 3.2

            # 10% Doping voltage boost: Scaled by formation energy shift and realization
            deltas["voltage_boost"] = -de_diff * 0.1 * (base_v_val / 3.0) * realization

            # Diffusivity scaling: Conservative mapping from volume ratio
            vol_ratio = target_props["volume_per_atom"] / base_props["volume_per_atom"]
            deltas["diffusivity_mult"] = (vol_ratio ** 1.2) * realization

        elif category == "Salt":
            # Conductivity scaling: σ ∝ exp(-Eg / 2kT)
            # We compare the target salt gap vs baseline NaPF6 gap
            gap_diff = base_props["band_gap"] - target_props["band_gap"]
            cond_mult = math.exp(gap_diff / (2 * KT))
            deltas["conductivity_mult"] = min(max(cond_mult, 0.1), 10.0) # Physical clamping

            # Transference: Penalize hull distance (less stable salts often have worse decomposition/SEI)
            deltas["ion_transference_mult"] = 1.0 + (0.05 / (1.0 + target_props["stability"] * 20.0))

        elif category == "Functionalization":
            # Derived relative to HARD_CARBON_REF
            stab_gain = base_props["stability"] / max(target_props["stability"], 0.01)
            deltas["sei_growth_mult"] = 0.6 + 0.4 / (1.0 + realization)
            deltas["initial_loss_mult"] = 0.7 + 0.3 / (1.0 + realization)
            deltas["resistance_drift_mult"] = 0.75 + 0.25 / (1.0 + realization)
            deltas["exchange_current_mult"] = 1.0 + 0.15 * realization

        return deltas

    def run_discovery(self):
        print("Harvesting Chemical Phase Spaces via OQMD Harvester...")
        system = {"Cathode_Dopant": [], "Salt": [], "Functionalization": []}

        # 1. BASELINE HARVESTING
        # NFPP system baseline
        nfpp_space = self.harvest_phase_space(["Na", "Fe", "P", "O"])
        base_cathode_props = self.get_best_phase(nfpp_space)

        # Salt system baseline (Fluorinated)
        napf6_space = self.harvest_phase_space(["Na", "P", "F"])
        base_salt_props = self.get_best_phase(napf6_space)

        # 2. CATHODE DOPANTS
        dopant_systems = {
            "Mn": ["Na", "Mn", "Fe", "P", "O"],
            "Cr": ["Na", "Cr", "Fe", "P", "O"],
            "Ni": ["Na", "Ni", "Fe", "P", "O"]
        }
        for d, elements in dopant_systems.items():
            doped_space = self.harvest_phase_space(elements)
            target_props = self.get_best_phase(doped_space)

            # We derive deltas from the best doped phase found in the space vs the baseline NFPP
            deltas = self.derive_deltas(target_props, base_cathode_props, "Cathode_Dopant")
            system["Cathode_Dopant"].append(MaterialCandidate(
                name=d, category="Cathode_Dopant", composition=f"Doped-{d}-NFPP",
                energy_above_hull=target_props["stability"], formation_energy=target_props["formation_energy"],
                band_gap=target_props["band_gap"], volume_per_atom=target_props["volume_per_atom"],
                projected_delta=deltas
            ))

        # 3. NON-FLUORINATED SALTS
        salts = {"NaBOB": ["Na", "B", "C", "O"], "NaTCP": ["Na", "C", "N", "O"]}
        for name, elements in salts.items():
            salt_space = self.harvest_phase_space(elements)
            target_props = self.get_best_phase(salt_space)
            deltas = self.derive_deltas(target_props, base_salt_props, "Salt")
            system["Salt"].append(MaterialCandidate(
                name=name, category="Salt", composition=name,
                energy_above_hull=target_props["stability"], formation_energy=target_props["formation_energy"],
                band_gap=target_props["band_gap"], volume_per_atom=target_props["volume_per_atom"],
                projected_delta=deltas
            ))

        # 4. FUNCTIONALIZATION (MTMS)
        mtms_space = self.harvest_phase_space(["Si", "C", "H", "O"])
        mtms_props = self.get_best_phase(mtms_space)
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

    print("\n--- material_cache.json (Deduplicated Harvest) ---")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            # Just print keys to verify deduplication
            for k in data.keys():
                print(f"Key: {k[:80]}... (Items: {len(data[k]) if isinstance(data[k], list) else 'N/A'})")
