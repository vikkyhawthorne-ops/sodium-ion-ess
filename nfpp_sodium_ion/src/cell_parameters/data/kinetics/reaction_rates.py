from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ReactionRateModel:
    # Ref: Generic polyanionic surface kinetics
    k0: float = 1e-11

    @property
    def activation_energy_j_mol(self) -> float:
        return get_derived_parameters()["e_a_rxn"]

    def rate_constant(self, temperature_k: float) -> float:
        return self.k0 * (temperature_k / 298.15) ** 0.5

    def as_dict(self) -> dict:
        return {"k0": self.k0, "activation_energy_j_mol": self.activation_energy_j_mol}
