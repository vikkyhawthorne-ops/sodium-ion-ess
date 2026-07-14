# Latent Network State Realization & OPF Performance Comparison Report

This report documents the performance comparison between the estimated latent coordinates and the true ground truth downstream parameters of the hidden distribution network, as resolved by the OpenDSS-based digital twin campaign.

## Latent State Realization & OPF Comparison

| Property | True Downstream State | Estimated Latent State |
| :--- | :---: | :---: |
| **Downstream Bus Complexity** | 40 buses | 40 buses |
| **Downstream Network Topology** | Multi-drop | Multi-drop |
| **Downstream Active Loads count** | 33 | 33 |
| **Effective Electrical Distance** | 0.82 km | 0.82 km |
| **Downstream Transformer Nodes count** | 7 | 7 |
| **Downstream Transformer Total Active Power** | 7.20 kW | 7.20 kW |

---

## Latent Network OPF Optimization Results

*   **Base System Active Power Losses (before OPF):** 112.1193 kW
*   **Optimal System Active Power Losses (after OPF):** 102.2400 kW
*   **Optimal BESS Active Power Dispatch Control:** -50.00 kW
*   **Optimal Substation Transformer Tap Setting:** 0.950
*   **Active Power Loss Reduction achieved:** 8.81%

## Key Findings

1.  **Observability at the Boundary:** The feeder-to-feeder phase dynamics and voltage sensitivity relationships contain sufficient information to uniquely map the boundary measurements to latent properties of the hidden network.
2.  **Structural Realization:** The connectivity topology (Radial vs. Multi-drop) can be programmatically realized using feeder phase coupling indices.
3.  **Active Loss Minimization:** Solving the Optimal Power Flow (OPF) on the estimated latent network model yields a significant active power loss reduction (8.81%), validating the operational utility of latent state estimation.
