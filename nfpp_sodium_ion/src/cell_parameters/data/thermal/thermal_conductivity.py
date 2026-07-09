from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ThermalConductivityModel:
    # Ref: Effective thermal conductivity for stacked electrode assemblies
    reference_k_w_m_k: float = 0.2

    def conductivity(self, temperature_k: float) -> float:
        # Grounded thermal dependency for pouch cell assembly
        return self.reference_k_w_m_k * (1 + 0.001 * (temperature_k - 298.15))

    def as_dict(self) -> dict:
        return {"reference_k_w_m_k": self.reference_k_w_m_k}
