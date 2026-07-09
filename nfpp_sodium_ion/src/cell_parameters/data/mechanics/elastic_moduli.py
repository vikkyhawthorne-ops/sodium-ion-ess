from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ElasticModuliModel:
    @property
    def youngs_modulus_pa(self) -> float:
        return get_derived_parameters()["youngs_modulus_p"]

    @property
    def poisson_ratio(self) -> float:
        return get_derived_parameters()["poisson_ratio_p"]

    def as_dict(self) -> dict:
        return {
            "youngs_modulus_pa": self.youngs_modulus_pa,
            "poisson_ratio": self.poisson_ratio,
        }
