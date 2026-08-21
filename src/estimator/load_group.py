from dataclasses import dataclass
import numpy as np

@dataclass
class MeteredConsumerUnit:
    unit_id: str
    feeder_id: str
    p_kw: float
    q_kvar: float
    load_group: str
    phase: str = "ABC"

@dataclass
class LoadGroupFrequencyDistribution:
    group_counts: dict[str, int]
    group_frequencies: dict[str, float]
    total_units: int

class NetworkLoadGroupModel:
    """
    Load Group Model for LV Network State Estimation:
    Categorizes consumer units into representative energy classes/groups
    and calculates local and global load group frequencies across feeders.
    """
    GROUPS = ["residential_light", "commercial", "industrial_motor"]
    GLOBAL_FREQUENCIES = {
        "residential_light": 0.50,
        "commercial": 0.30,
        "industrial_motor": 0.20
    }
    TYPICAL_POWER_KW = {
        "residential_light": 8.0,
        "commercial": 18.0,
        "industrial_motor": 28.0
    }

    @classmethod
    def classify_unit(cls, p_kw: float) -> str:
        if p_kw < 12.0:
            return "residential_light"
        elif p_kw < 22.0:
            return "commercial"
        else:
            return "industrial_motor"

    @classmethod
    def compute_distribution(cls, units: list[MeteredConsumerUnit]) -> LoadGroupFrequencyDistribution:
        counts = {g: 0 for g in cls.GROUPS}
        for u in units:
            counts[u.load_group] += 1

        total = max(1, len(units))
        freqs = {g: counts[g] / float(total) for g in cls.GROUPS}

        return LoadGroupFrequencyDistribution(
            group_counts=counts,
            group_frequencies=freqs,
            total_units=len(units)
        )
