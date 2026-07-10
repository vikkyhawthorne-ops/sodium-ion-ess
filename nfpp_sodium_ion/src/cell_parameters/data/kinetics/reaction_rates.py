from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ReactionRateModel:
    @property
    def k0(self) -> float:
        return get_derived_parameters()["k0_ref"]

    @property
    def activation_energy_j_mol(self) -> float:
        return get_derived_parameters()["e_a_rxn"]

    def rate_constant(self, temperature_k: float) -> float:
        derived = get_derived_parameters()
        return self.k0 * (temperature_k / derived["t_ref"]) ** 0.5

    def as_dict(self) -> dict:
        return {"k0": self.k0, "activation_energy_j_mol": self.activation_energy_j_mol}
