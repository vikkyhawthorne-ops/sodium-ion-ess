from dataclasses import dataclass
import numpy as np
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ExchangeCurrentDensityModel:
    @property
    def j0_ref_a_m2(self) -> float:
        return get_derived_parameters()["j0_ref"]

    def exchange_current_density(self, temperature_k: float, soc: float) -> float:
        derived = get_derived_parameters()
        # Arrhenius dependency with grounded activation energy
        E_r = derived["e_a_rxn"]
        R = derived["r_gas"]
        T_ref = derived["t_ref"]
        arrhenius = np.exp(E_r / R * (1 / T_ref - 1 / temperature_k))
        return self.j0_ref_a_m2 * arrhenius * (soc * (1 - soc))**0.5

    def as_dict(self) -> dict:
        return {"j0_ref_a_m2": self.j0_ref_a_m2}
