from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class CellParameters:
    @property
    def name(self) -> str:
        return "NFPP Sodium-ion Pouch Cell"

    @property
    def nominal_voltage(self) -> float:
        return get_derived_parameters()["nominal_voltage"]

    @property
    def capacity_ah(self) -> float:
        return get_derived_parameters()["capacity_ah"]

    @property
    def form_factor(self) -> str:
        return "stacked pouch"

    @property
    def cathode_collector_thickness_um(self) -> float:
        return get_derived_parameters()["cathode_collector_thickness"] * 1e6

    @property
    def anode_collector_thickness_um(self) -> float:
        return get_derived_parameters()["anode_collector_thickness"] * 1e6

    @property
    def separator_thickness_um(self) -> float:
        return get_derived_parameters()["sep_thickness"] * 1e6

    @property
    def casing_thickness_um(self) -> float:
        return get_derived_parameters()["casing_thickness"] * 1e6

    @property
    def number_of_layers(self) -> int:
        return get_derived_parameters()["n_layers_10ah"]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "nominal_voltage": self.nominal_voltage,
            "capacity_ah": self.capacity_ah,
            "number_of_layers": self.number_of_layers,
        }
