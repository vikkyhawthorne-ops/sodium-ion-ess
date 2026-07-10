from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class SwellingCoefficientModel:
    @property
    def negative_electrode_swelling_coefficient(self) -> float:
        return get_derived_parameters()["beta_n"]

    @property
    def positive_electrode_swelling_coefficient(self) -> float:
        return get_derived_parameters()["beta_p"]

    def as_dict(self) -> dict:
        return {
            "negative_electrode_swelling_coefficient": self.negative_electrode_swelling_coefficient,
            "positive_electrode_swelling_coefficient": self.positive_electrode_swelling_coefficient,
        }
