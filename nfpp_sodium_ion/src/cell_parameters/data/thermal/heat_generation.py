from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class HeatGenerationModel:
    @property
    def reaction_heat_factor(self) -> float:
        return 0.5 # Unit partition (Safari model)

    @property
    def ohmic_heat_factor(self) -> float:
        return 0.3 # Unit partition (Safari model)

    @property
    def polarization_heat_factor(self) -> float:
        return 0.2 # Unit partition (Safari model)

    def total_heat(self, reaction_heat: float, ohmic_heat: float, polarization_heat: float) -> float:
        return reaction_heat * self.reaction_heat_factor + ohmic_heat * self.ohmic_heat_factor + polarization_heat * self.polarization_heat_factor

    def as_dict(self) -> dict:
        return {
            "reaction_heat_factor": self.reaction_heat_factor,
            "ohmic_heat_factor": self.ohmic_heat_factor,
            "polarization_heat_factor": self.polarization_heat_factor,
        }
