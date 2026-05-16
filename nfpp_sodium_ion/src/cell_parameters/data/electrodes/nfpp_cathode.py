from dataclasses import dataclass

@dataclass
class NfppCathodeParameters:
    # Ref: paper.md
    active_material_fraction: float = 0.85
    conductive_carbon_fraction: float = 0.08
    binder_fraction: float = 0.07
    # Ref: ResearchGate (10.1021/acssuschemeng.7b04516)
    theoretical_capacity_mAh_g: float = 97.19
    density_kg_m3: float = 3200.0
    current_collector: str = "Aluminum"

    def as_dict(self) -> dict:
        return {
            "active_material_fraction": self.active_material_fraction,
            "theoretical_capacity_mAh_g": self.theoretical_capacity_mAh_g,
            "density_kg_m3": self.density_kg_m3,
        }
