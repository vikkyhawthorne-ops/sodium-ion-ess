from dataclasses import dataclass
import numpy as np
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class DiffusivityModel:
    @property
    def reference_diffusivity_m2_s(self) -> float:
        return get_derived_parameters()["diff_p_ref"]

    def effective_diffusivity(self, temperature_k: float, porosity: float, electrode: str = "positive") -> float:
        derived = get_derived_parameters()
        R = derived["r_gas"]
        T_ref = derived["t_ref"]
        # Select grounded activation energy based on domain
        E_a = derived["e_a_diff_p"] if electrode == "positive" else derived["e_a_diff_n"]

        arrhenius = np.exp(E_a / R * (1 / T_ref - 1 / temperature_k))
        return self.reference_diffusivity_m2_s * arrhenius * porosity**1.5

    def as_dict(self) -> dict:
        derived = get_derived_parameters()
        return {
            "reference_diffusivity_m2_s": self.reference_diffusivity_m2_s,
            "activation_energy_p": derived["e_a_diff_p"],
            "activation_energy_n": derived["e_a_diff_n"]
        }
