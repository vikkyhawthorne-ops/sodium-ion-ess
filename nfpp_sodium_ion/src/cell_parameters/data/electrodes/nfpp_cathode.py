from dataclasses import dataclass

@dataclass
class NfppCathodeParameters:
    active_material_fraction: float = 0.85
    conductive_carbon_fraction: float = 0.08
    binder_fraction: float = 0.07
    theoretical_capacity_mAh_g: float = 97.19
    density_kg_m3: float = 3200.0
    current_collector: str = "Aluminum"

    def composition(self) -> dict:
        return {
            "active_material": self.active_material_fraction,
            "conductive_carbon": self.conductive_carbon_fraction,
            "binder": self.binder_fraction,
        }

    def as_dict(self) -> dict:
        return {
            "composition": self.composition(),
            "theoretical_capacity_mAh_g": self.theoretical_capacity_mAh_g,
            "density_kg_m3": self.density_kg_m3,
            "current_collector": self.current_collector,
        }
