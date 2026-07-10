from dataclasses import dataclass
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ChemistryParameters:
    # Ref: paper.md
    @property
    def active_material(self) -> str:
        return "Na2FePO4P2O7"

    @property
    def anode_material(self) -> str:
        return "hard carbon"

    @property
    def electrolyte_salt_primary(self) -> str:
        return "NaPF6"

    @property
    def electrolyte_salt_secondary(self) -> str:
        return "NaDFOB"

    @property
    def solvent_system(self) -> str:
        return "EC:PC 1:1"

    fem_additives: dict = None

    def __post_init__(self):
        derived = get_derived_parameters()
        if self.fem_additives is None:
            self.fem_additives = {"FEC": derived["additives_fec"], "VC": derived["additives_vc"]}

    def as_dict(self) -> dict:
        return {
            "active_material": self.active_material,
            "anode_material": self.anode_material,
            "electrolyte_salt_primary": self.electrolyte_salt_primary,
            "electrolyte_salt_secondary": self.electrolyte_salt_secondary,
            "solvent_system": self.solvent_system,
            "electrolyte_additives": self.fem_additives,
        }
