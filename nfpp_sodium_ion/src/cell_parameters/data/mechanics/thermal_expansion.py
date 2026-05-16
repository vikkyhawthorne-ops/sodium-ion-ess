from dataclasses import dataclass

@dataclass
class ThermalExpansionModel:
    # Typical values for polyanionic cathodes
    thermal_expansion_coefficient: float = 1.5e-5

    def as_dict(self) -> dict:
        return {
            "thermal_expansion_coefficient": self.thermal_expansion_coefficient,
        }
