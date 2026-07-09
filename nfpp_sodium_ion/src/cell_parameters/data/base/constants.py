from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class Constants:
    @property
    def R(self) -> float:
        return get_derived_parameters()["r_gas"]

    @property
    def F(self) -> float:
        return get_derived_parameters()["faraday"]

    @property
    def T_ref(self) -> float:
        return get_derived_parameters()["t_ref"]

    @property
    def sigma_al(self) -> float:
        return get_derived_parameters()["al_sigma"]

    @property
    def sigma_cu(self) -> float:
        return get_derived_parameters()["cu_sigma"]

    @property
    def epsilon_0(self) -> float:
        return get_derived_parameters()["epsilon_0"]

    def as_dict(self) -> dict:
        return {
            "R": self.R,
            "F": self.F,
            "T_ref": self.T_ref,
            "sigma_al": self.sigma_al,
            "sigma_cu": self.sigma_cu,
            "epsilon_0": self.epsilon_0,
        }
