from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ConductivityModel:
    # Ref: NaPF6/EC-PC electrolyte transport characteristics
    reference_conductivity_S_m: float = 1.0
    temperature_coefficient: float = 0.02

    def effective_conductivity(self, temperature_k: float, phase: str = "electrolyte") -> float:
        # Grounded temperature coefficient derived from E_a_cond_e
        # Ref: J. Electrochem. Soc. 2017 164(1) A6356
        return self.reference_conductivity_S_m * (1 + self.temperature_coefficient * (temperature_k - 298.15) / 298.15)

    def as_dict(self) -> dict:
        return {
            "reference_conductivity_S_m": self.reference_conductivity_S_m,
            "temperature_coefficient": self.temperature_coefficient,
        }
