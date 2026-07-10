from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class HardCarbonAnodeParameters:
    @property
    def active_material_fraction(self) -> float:
        return 0.88 # Ref: paper.md benchmark design

    @property
    def conductive_carbon_fraction(self) -> float:
        return 0.06 # Ref: paper.md benchmark design

    @property
    def binder_fraction(self) -> float:
        return 0.06 # Ref: paper.md benchmark design

    @property
    def practical_capacity_mAh_g(self) -> float:
        return 300.0 # Ref: MTI, Kuraray benchmark

    @property
    def density_kg_m3(self) -> float:
        return 1500.0 # Ref: MTI, Kuraray benchmark

    def as_dict(self) -> dict:
        return {
            "active_material_fraction": self.active_material_fraction,
            "practical_capacity_mAh_g": self.practical_capacity_mAh_g,
            "density_kg_m3": self.density_kg_m3,
        }
