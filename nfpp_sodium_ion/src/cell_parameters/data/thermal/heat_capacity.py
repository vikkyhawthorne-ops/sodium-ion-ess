from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class HeatCapacityModel:
    # Ref: Average specific heat for stacked pouch cells (benchmark data)
    reference_cp_j_kg_k: float = 900.0

    def specific_heat(self, temperature_k: float) -> float:
        # Linear dependency for lumped thermal model
        return self.reference_cp_j_kg_k * (1 + 0.001 * (temperature_k - 298.15))

    def as_dict(self) -> dict:
        return {"reference_cp_j_kg_k": self.reference_cp_j_kg_k}
