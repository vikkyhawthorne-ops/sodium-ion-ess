from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ElasticModuliModel:
    # NFPP typically has higher modulus than layered oxides.
    # Ref: Materials Project (mp-752506), average polyanionic response
    youngs_modulus_pa: float = 60.0e9
    poisson_ratio: float = 0.25

    def as_dict(self) -> dict:
        return {
            "youngs_modulus_pa": self.youngs_modulus_pa,
            "poisson_ratio": self.poisson_ratio,
        }
