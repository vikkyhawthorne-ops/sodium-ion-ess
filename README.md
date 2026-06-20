
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mhizterpaul/sodium-ion-ess/blob/main/src/report.ipynb)

This repository implements a high-fidelity digital twin and optimization framework for Sodium Iron Pyrophosphate (NFPP) battery systems within an integrated plant–network digital twin framework for solar–BESS microgrids.

## Research Scope

### 1. Plant–Network State Estimation & Fault Detection (Core Contribution)
The primary research focus is an integrated plant–network digital twin that performs real-time estimation of all distribution lines, feeder buses, and asset states to ensure system integrity.

#### Monitoring Objectives
*   **Network State Estimation**: High-fidelity tracking of the state vector $x(t) = [V, I, f, THD, Q, P_{loss}, SOC, SOH, T, Z_{network}]$.
*   **Residual-Based Fault Detection**: Detecting anomalies using digital twin comparisons: $r(t) = y(t) - \hat{y}(t)$.
*   **System Availability Monitoring**: Ensuring $\mathbb{P}(\text{instability}) \le \epsilon$.
*   **Degradation Analysis**: Monitoring $\Delta SOH(t)$ for both BESS and Power Conditioning Units (PCUs).

### 2. DFN-Based NFPP Cell Optimization
A hierarchical multi-stage framework for cell design enhancement:
*   **Layered Material Mapping**: Decoupled architecture for eco-friendly salts (NaTCP, NaBOB), cathode dopants (Cr, Mn, Ni), and MTMS functionalization.
*   **Parameter Optimization**: Hierarchical search for structural ($\theta_s$) and material ($\theta_m$) parameters using sensitivity-based Jacobian screening and Genetic Algorithms.

### 3. Physical Power Plant Model (Digital Twin)
The plant environment represents the physical microgrid hardware:
*   **Microgrid Assets**: 100kWp Solar PV, 50kW Primary Generation, and 100kWh BESS (208 modules).
*   **Infrastructure**: Utility-scale power conditioning (150kVA PCU, Step-up transformer, MV Switchgear).
*   **Nodal Interface**: Balanced 3-phase interface for real-time state estimation across feeders.

## Repository Structure

- `src/cell_optimization/`: Material discovery engines and structural optimization scripts.
- `src/power_plant/`: Utility-scale power plant digital twin components.
- `nfpp_sodium_ion/`: Registered PyBaMM parameter set for NFPP/Hard-Carbon chemistry.
- `src/report.ipynb`: Orchestration notebook for the complete research pipeline.

## Getting Started

### Installation
```bash
# Install core dependencies
pip install -r requirements.txt

# Install PyBaMM parameter package
pip install -e nfpp_sodium_ion/
```

### Execution
Run the complete research pipeline via the Jupyter notebook:
```bash
jupyter notebook src/report.ipynb
```
