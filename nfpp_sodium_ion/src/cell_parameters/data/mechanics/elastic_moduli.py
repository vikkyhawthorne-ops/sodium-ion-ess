from dataclasses import dataclass

@dataclass
class ElasticModuliModel:
    # NFPP typically has higher modulus than layered oxides.
    # Estimated from polyanionic compounds in Materials Project (e.g. mp-752506)
    # References: Materials Project, mp-752506
    youngs_modulus_pa: float = 60.0e9
    poisson_ratio: float = 0.25

    def as_dict(self) -> dict:
        return {
            "youngs_modulus_pa": self.youngs_modulus_pa,
            "poisson_ratio": self.poisson_ratio,
        }
