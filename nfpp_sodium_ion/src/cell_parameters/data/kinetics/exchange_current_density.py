from dataclasses import dataclass
import numpy as np

@dataclass
class ExchangeCurrentDensityModel:
    j0_ref_a_m2: float = 1.0e-6

    def exchange_current_density(self, temperature_k: float, soc: float) -> float:
        # Arrhenius dependency
        E_r = 35000
        R = 8.314
        arrhenius = np.exp(E_r / R * (1 / 298.15 - 1 / temperature_k))
        return self.j0_ref_a_m2 * arrhenius * (soc * (1 - soc))**0.5

    def as_dict(self) -> dict:
        return {"j0_ref_a_m2": self.j0_ref_a_m2}
