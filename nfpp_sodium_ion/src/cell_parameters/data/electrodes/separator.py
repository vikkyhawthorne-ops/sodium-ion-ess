from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class SeparatorParameters:
    material: str = "polyolefin trilayer"

    @property
    def thickness_um(self) -> float:
        return get_derived_parameters()["sep_thickness"] * 1e6

    @property
    def porosity(self) -> float:
        return get_derived_parameters()["sep_porosity"]

    @property
    def ionic_conductivity_S_cm(self) -> float:
        return get_derived_parameters()["sep_ionic_cond"]

    def as_dict(self) -> dict:
        return {
            "material": self.material,
            "thickness_um": self.thickness_um,
            "porosity": self.porosity,
            "ionic_conductivity_S_cm": self.ionic_conductivity_S_cm,
        }
