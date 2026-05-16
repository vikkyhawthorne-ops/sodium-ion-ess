from dataclasses import dataclass

@dataclass
class SwellingCoefficientsModel:
    # SOC-driven expansion for Hard Carbon and NFPP
    negative_electrode_swelling_coefficient: float = 0.1 # HC expands ~10%
    positive_electrode_swelling_coefficient: float = 0.05 # NFPP is stable

    def as_dict(self) -> dict:
        return {
            "negative_electrode_swelling_coefficient": self.negative_electrode_swelling_coefficient,
            "positive_electrode_swelling_coefficient": self.positive_electrode_swelling_coefficient,
        }
