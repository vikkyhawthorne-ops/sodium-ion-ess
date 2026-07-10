from dataclasses import dataclass
from typing import Dict
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class NaPfpDfoParameters:
    @property
    def salt_primary(self) -> str:
        return "NaPF6"

    @property
    def salt_secondary(self) -> str:
        return "NaDFOB"

    @property
    def concentration_primary_mol_per_l(self) -> float:
        return get_derived_parameters()["salt_conc_primary"]

    @property
    def concentration_secondary_mol_per_l(self) -> float:
        return get_derived_parameters()["salt_conc_secondary"]

    @property
    def solvent_system(self) -> str:
        return "EC:PC 1:1"

    @property
    def ionic_conductivity_mS_cm(self) -> float:
        return 10.0 # Ref: benchmark electrolyte data

    additives: Dict[str, float] = None

    def __post_init__(self):
        derived = get_derived_parameters()
        if self.additives is None:
            self.additives = {"FEC": derived["additives_fec"], "VC": derived["additives_vc"]}

    def as_dict(self) -> dict:
        return {
            "salt_primary": self.salt_primary,
            "salt_secondary": self.salt_secondary,
            "concentration_primary_mol_per_l": self.concentration_primary_mol_per_l,
            "concentration_secondary_mol_per_l": self.concentration_secondary_mol_per_l,
            "solvent_system": self.solvent_system,
            "ionic_conductivity_mS_cm": self.ionic_conductivity_mS_cm,
            "additives": self.additives,
        }
