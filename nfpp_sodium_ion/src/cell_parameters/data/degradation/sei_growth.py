from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class SeiGrowthModel:
    @property
    def rate_constant(self) -> float:
        return get_derived_parameters()["sei_exchange_current"]

    def growth_rate(self, current_density_a_m2: float, time_s: float) -> float:
        return self.rate_constant * abs(current_density_a_m2) * time_s

    def as_dict(self) -> dict:
        return {"rate_constant": self.rate_constant}
