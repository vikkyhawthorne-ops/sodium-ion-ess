from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class NfppCathodeParameters:
    @property
    def active_material_fraction(self) -> float:
        return 0.85 # Ref: paper.md benchmark design

    @property
    def conductive_carbon_fraction(self) -> float:
        return 0.08 # Ref: paper.md benchmark design

    @property
    def binder_fraction(self) -> float:
        return 0.07 # Ref: paper.md benchmark design

    @property
    def theoretical_capacity_mAh_g(self) -> float:
        return 97.19 # Ref: ResearchGate (10.1021/acssuschemeng.7b04516)

    @property
    def density_kg_m3(self) -> float:
        return 3200.0 # Ref: ResearchGate (10.1021/acssuschemeng.7b04516)

    def as_dict(self) -> dict:
        return {
            "active_material_fraction": self.active_material_fraction,
            "theoretical_capacity_mAh_g": self.theoretical_capacity_mAh_g,
            "density_kg_m3": self.density_kg_m3,
        }
