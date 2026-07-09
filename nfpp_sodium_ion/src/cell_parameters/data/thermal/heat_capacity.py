from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class HeatCapacityModel:
    @property
    def reference_cp_j_kg_k(self) -> float:
        return get_derived_parameters()["cp_electrode"]

    def specific_heat(self, temperature_k: float) -> float:
        derived = get_derived_parameters()
        # Linear dependency for lumped thermal model
        return self.reference_cp_j_kg_k * (1 + 0.001 * (temperature_k - derived["t_ref"]))

    def as_dict(self) -> dict:
        return {"reference_cp_j_kg_k": self.reference_cp_j_kg_k}
