from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ThermalConductivityModel:
    @property
    def reference_k_w_m_k(self) -> float:
        return get_derived_parameters()["tc_p"]

    def conductivity(self, temperature_k: float) -> float:
        derived = get_derived_parameters()
        # Grounded thermal dependency for pouch cell assembly
        return self.reference_k_w_m_k * (1 + 0.001 * (temperature_k - derived["t_ref"]))

    def as_dict(self) -> dict:
        return {"reference_k_w_m_k": self.reference_k_w_m_k}
