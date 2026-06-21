# DFN-Based Optimization of NFPP Sodium-Ion Cells within an Integrated Plant–Network Digital Twin Framework for Solar–BESS Microgrids

## Methodology

### 1. Base Cell Model (Literature-Aligned NFPP Sodium-Ion Twin System)
The electrochemical behavior is resolved using a Doyle-Fuller-Newman (DFN) framework implemented in PyBaMM. This captures the coupled evolution of State of Charge (SOC), State of Health (SOH), and heat generation.

### 2. DFN-Based NFPP Cell Optimization Framework
A hierarchical Material-Structural framework optimizes the NFPP-based sodium-ion cells.
- **Design Space**: Structural parameters (thickness, porosity, particle size) and material parameters (dopants, electrolyte composition).
- **Objectives**: Energy capacity, power capability, and thermo-mechanical stability.

### 3. Multi-Feeder Network State Realization & Anomaly Detection (Core Contribution)
This framework provides diagnostic capabilities for a multi-feeder distribution network coupled by shared solar and BESS generation sources.

#### 3.1 Shared Source Coupling Model
The total power from shared sources is distributed across $n$ feeders:
$P_{source}(t) = P_{solar}(t) + P_{BESS}(t) = \sum_{i=1}^{n} P_{F_i}(t) + P_{loss}(t)$

Feeders are physically coupled by:
- **Source capacity & inverter limits**.
- **Shared BESS constraints** (SOC, SOH, and thermal state).
- **Common PCC conditions** (voltage and frequency).

Disturbances on one feeder (e.g., fault or abnormal load $\Delta P_{Fi}$) propagate through the shared source, altering the operating point for all feeders.

#### 3.2 Network State Realization
The state of each feeder $i$ is defined by its nodal voltage and phase angles:
$x_i = [V_{i1}, \theta_{i1}, \dots, V_{im}, \theta_{im}]$

The global network state is $X = [x_1, \dots, x_n]$. To detect anomalies across the coupled system, we define the **Network Realization State**:
$X_R = [\Delta \theta_{F1}, \Delta \theta_{F2}, \dots, \Delta \theta_{Fn}]$

This represents the feeder-level phase behavior relative to the nominal operating manifold. Anomaly detection is performed by evaluating:
$\Delta \theta_{Fi} \notin \text{expected envelope}$

#### 3.3 Diagnostic Objectives
1. **Coupled Anomaly Localization**: Identifying which feeder is the source of a propagation event.
2. **Phase Dynamics Tracking**: Monitoring $\Delta \theta_{Fi}$ as a high-sensitivity indicator of network stress or fault conditions.
3. **Availability Under Stress**: Ensuring system stability ($\mathbb{P}(\text{instability}) \le \epsilon$) despite feeder-level disturbances.
