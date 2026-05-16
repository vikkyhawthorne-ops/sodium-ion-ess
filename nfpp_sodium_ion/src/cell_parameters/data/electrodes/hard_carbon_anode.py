from dataclasses import dataclass

@dataclass
class HardCarbonAnodeParameters:
    # Ref: paper.md
    active_material_fraction: float = 0.88
    conductive_carbon_fraction: float = 0.06
    binder_fraction: float = 0.06
    # Ref: MTI, Kuraray
    practical_capacity_mAh_g: float = 300.0
    density_kg_m3: float = 1500.0
    current_collector: str = "Copper"

    def as_dict(self) -> dict:
        return {
            "active_material_fraction": self.active_material_fraction,
            "practical_capacity_mAh_g": self.practical_capacity_mAh_g,
            "density_kg_m3": self.density_kg_m3,
        }
