from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ConductivityModel:
    @property
    def reference_conductivity_S_m(self) -> float:
        return get_derived_parameters()["cond_e_ref"]

    @property
    def temperature_coefficient(self) -> float:
        return get_derived_parameters()["temp_coeff_e"]

    def effective_conductivity(self, temperature_k: float, phase: str = "electrolyte") -> float:
        derived = get_derived_parameters()
        T_ref = derived["t_ref"]
        return self.reference_conductivity_S_m * (1 + self.temperature_coefficient * (temperature_k - T_ref) / T_ref)

    def as_dict(self) -> dict:
        return {
            "reference_conductivity_S_m": self.reference_conductivity_S_m,
            "temperature_coefficient": self.temperature_coefficient,
        }
