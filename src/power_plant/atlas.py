import os
import json
import random
import numpy as np
import opendssdirect as dss
from typing import Dict, Any, List, Tuple
from src.power_plant.plant import (
    MonteCarloMicrogridCampaign,
    LatentNetworkStateEstimator,
    NetworkRealizationEngine,
    GraphSpectrumAnalyzer,
    TopologyEstimator,
    OptimalPowerFlow
)

class SignatureAtlasBuilder:
    """
    Constructs the Network Signature Atlas from OpenDSS experiments
    and maps boundary measurements to latent states X_R = Phi(M).
    """

    def __init__(self):
        self.atlas: List[Dict[str, Any]] = []

    def add_entry(self, sig_id: str, measurements: Dict[str, Any], hidden_state: Dict[str, Any], realization: Dict[str, Any], event: str):
        derived_features = {
            "feeder_phase_coupling": measurements["delta_theta_deg"],
            "power_balance_pf": measurements["pcc_active_power_kw"] / (np.sqrt(measurements["pcc_active_power_kw"]**2 + measurements["pcc_reactive_power_kvar"]**2) + 1e-6),
            "aggregate_impedance_proxy": measurements["pcc_voltage_v"] / (abs(measurements["pcc_active_power_kw"]) + 1e-6),
            "voltage_sensitivity_stiffness": (1.0 - (measurements["f1_voltage_v"] / 240.0)) / (abs(measurements["pcc_active_power_kw"]) + 1e-6)
        }

        self.atlas.append({
            "sig_id": sig_id,
            "boundary": measurements,
            "features": derived_features,
            "hidden_state": hidden_state,
            "realization": realization,
            "event": event
        })


def realize_latent_topology(m: Dict[str, Any]) -> str:
    """
    Realizes the latent network topology (Radial vs. Multi-drop)
    from feeder phase coupling signatures and voltage sensitivity.
    """
    delta_theta = abs(m["delta_theta_deg"])
    if delta_theta > 1.0:
        return "Multi-drop"
    return "Radial"


def solve_latent_opf(m: Dict[str, Any], estimated_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Solves an Optimal Power Flow (OPF) for the estimated latent downstream network.
    Optimizes BESS dispatch and MV transformer tap settings to minimize active power losses.
    """
    campaign = MonteCarloMicrogridCampaign()

    # 1. Reconstruct estimated latent network topology
    campaign.build_fixed_plant()
    num_buses = estimated_state["estimated_buses"]
    topo = estimated_state["estimated_topology"]
    campaign.generate_random_hidden_network(num_buses, topo)

    # 2. Extract base losses before optimization
    dss.Solution.Solve()
    base_losses = dss.Circuit.Losses()[0] / 1000.0 # kW

    # 3. Optimize over grid of control variables: BESS dispatch [-50kW to 50kW] and transformer tap [0.95 to 1.05]
    best_loss = base_losses
    best_bess_kw = 0.0
    best_tap = 1.0

    for bess_kw in [-50.0, -25.0, 0.0, 25.0, 50.0]:
        for tap in [0.95, 1.0, 1.05]:
            # Set BESS output
            dss.Circuit.SetActiveElement("Generator.bess")
            dss.Text.Command(f"Generator.bess.kw={bess_kw}")

            # Set Transformer tap
            dss.Transformers.First()
            dss.Transformers.Tap(tap)

            dss.Solution.Solve()
            losses = dss.Circuit.Losses()[0] / 1000.0 # kW

            if losses < best_loss:
                best_loss = losses
                best_bess_kw = bess_kw
                best_tap = tap

    loss_reduction_pct = ((base_losses - best_loss) / (base_losses + 1e-6)) * 100.0

    return {
        "base_losses_kw": float(base_losses),
        "optimal_losses_kw": float(best_loss),
        "optimal_bess_dispatch_kw": float(best_bess_kw),
        "optimal_transformer_tap": float(best_tap),
        "loss_reduction_percent": float(max(0.0, loss_reduction_pct))
    }


def run_pipeline_experiments() -> Tuple[List[Dict[str, Any]], LatentNetworkStateEstimator]:
    """Runs the full OpenDSS Monte Carlo network realization campaign and instantiates the Estimator."""
    campaign = MonteCarloMicrogridCampaign()
    campaign.run_monte_carlo_campaign(num_realizations=120)

    estimator = LatentNetworkStateEstimator()
    return campaign.signature_db, estimator
