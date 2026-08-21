from dataclasses import dataclass
import numpy as np
from src.estimator.load_group import (
    MeteredConsumerUnit,
    NetworkLoadGroupModel,
    LoadGroupFrequencyDistribution
)

@dataclass
class FrequencyReconstructionEstimate:
    known_number_of_buses: int
    known_number_of_branches: int
    estimated_total_consumer_units: int
    estimated_metered_consumer_units: int
    estimated_unmetered_consumer_units: int
    estimated_unmetered_power_kw: float
    group_inverse_weights: dict
    r_eq_ohm: float
    x_eq_ohm: float
    z_eq_ohm: float
    objective_loss: float

class LoadFrequencyReconstructionEstimator:
    """
    DSSE Estimator using Load Frequency Reconstruction:
    Reconstructs the LV network using inverse-similarity weighting of local group frequency
    extracted from 36% consumer meter measurements to estimate unmetered consumer units
    and satisfy total feeder head readings.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def estimate(
        self,
        metered_consumer_measurements: list[dict],
        feeder_measurements: dict,
        known_num_buses: int = 20,
        known_num_branches: int = 19
    ) -> FrequencyReconstructionEstimate:
        """
        Args:
            metered_consumer_measurements: 36% metered consumer observations.
            feeder_measurements: feeder head / boundary transformer secondary measurement dict.
            known_num_buses: known count of network buses.
            known_num_branches: known count of network branches.

        Returns:
            FrequencyReconstructionEstimate
        """
        rng = np.random.default_rng(self.seed)

        # 1. Parse metered consumer units
        metered_units = []
        metered_power_sum = 0.0

        for idx, m in enumerate(metered_consumer_measurements):
            p_kw = float(m.get("p_kw", 12.0))
            q_kvar = float(m.get("q_kvar", 2.0))
            grp = NetworkLoadGroupModel.classify_unit(p_kw)

            metered_power_sum += p_kw
            metered_units.append(MeteredConsumerUnit(
                unit_id=f"metered_{idx}",
                feeder_id="feeder_local",
                p_kw=p_kw,
                q_kvar=q_kvar,
                load_group=grp
            ))

        n_metered = max(1, len(metered_units))

        # 2. Compute local frequencies and inverse-similarity weights
        dist = NetworkLoadGroupModel.compute_distribution(metered_units)
        local_freqs = dist.group_frequencies

        inv_weights = {
            g: NetworkLoadGroupModel.GLOBAL_FREQUENCIES[g] / (local_freqs[g] + 1e-3)
            for g in NetworkLoadGroupModel.GROUPS
        }
        sum_w = sum(inv_weights.values())
        norm_probs = [inv_weights[g] / sum_w for g in NetworkLoadGroupModel.GROUPS]

        # 3. Get Feeder Head power reading
        p_feeder = float(feeder_measurements.get("p_kw", metered_power_sum / 0.36 if metered_power_sum > 0 else 100.0))
        power_residual = max(0.0, p_feeder - metered_power_sum)

        # 4. Reconstruct unmetered consumer units via inverse-similarity weighted sampling
        n_unmetered = 0
        p_unmetered_added = 0.0

        while p_unmetered_added < power_residual:
            sampled_group = str(rng.choice(NetworkLoadGroupModel.GROUPS, p=norm_probs))
            typ_kw = NetworkLoadGroupModel.TYPICAL_POWER_KW[sampled_group]
            unit_kw = round(float(rng.uniform(0.85, 1.15) * typ_kw), 2)

            n_unmetered += 1
            p_unmetered_added += unit_kw

        n_total = n_metered + n_unmetered

        # Estimate equivalent impedance from line parameters and reconstructed consumer load density
        total_line_len = 0.05 * known_num_branches
        r_eq = round(float(0.21 * total_line_len / max(1, known_num_branches**0.5)), 4)
        x_eq = round(float(0.08 * total_line_len / max(1, known_num_branches**0.5)), 4)
        z_eq = round(float(np.sqrt(r_eq**2 + x_eq**2)), 4)

        objective_loss = round(float(abs(p_feeder - (metered_power_sum + p_unmetered_added)) / (p_feeder + 1e-6)), 6)

        return FrequencyReconstructionEstimate(
            known_number_of_buses=known_num_buses,
            known_number_of_branches=known_num_branches,
            estimated_total_consumer_units=n_total,
            estimated_metered_consumer_units=n_metered,
            estimated_unmetered_consumer_units=n_unmetered,
            estimated_unmetered_power_kw=round(p_unmetered_added, 2),
            group_inverse_weights={g: round(inv_weights[g], 4) for g in NetworkLoadGroupModel.GROUPS},
            r_eq_ohm=r_eq,
            x_eq_ohm=x_eq,
            z_eq_ohm=z_eq,
            objective_loss=objective_loss
        )
