from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ThermalExpansionModel:
    @property
    def thermal_expansion_coefficient(self) -> float:
        return get_derived_parameters()["alpha_thermal"]

    def as_dict(self) -> dict:
        return {
            "thermal_expansion_coefficient": self.thermal_expansion_coefficient,
        }
