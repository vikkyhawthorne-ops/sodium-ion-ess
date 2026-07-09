from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class LossOfSodiumEquivalentModel:
    @property
    def loss_rate_fraction_per_cycle(self) -> float:
        return get_derived_parameters()["loss_rate_cycle"]

    def loss_per_cycle(self, cycles: int) -> float:
        return self.loss_rate_fraction_per_cycle * cycles

    def as_dict(self) -> dict:
        return {"loss_rate_fraction_per_cycle": self.loss_rate_fraction_per_cycle}
