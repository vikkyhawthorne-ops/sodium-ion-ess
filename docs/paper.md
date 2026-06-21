# DFN-Based Optimization of NFPP Sodium-Ion Cells within an Integrated Plant–Network Digital Twin Framework for Solar–BESS Microgrids

## Methodology

### 1. Base Cell Model (Literature-Aligned NFPP Sodium-Ion Twin System)
The electrochemical behavior is resolved using a Doyle-Fuller-Newman (DFN) framework implemented in PyBaMM. This captures the coupled evolution of State of Charge (SOC), State of Health (SOH), and heat generation.

### 2. DFN-Based NFPP Cell Optimization Framework
A hierarchical Material-Structural framework optimizes the NFPP-based sodium-ion cells.
- **Design Space**: Structural parameters (thickness, porosity, particle size) and material parameters (dopants, electrolyte composition).
- **Objectives**: Energy capacity, power capability, and thermo-mechanical stability.

### 3. Integrated Plant–Network State Estimation & Fault Detection Framework (Core Contribution)
The proposed framework provides diagnostic and estimation capabilities across the distribution network and integrated BESS-Solar microgrid. This is an analytical and monitoring layer rather than an active control system.

#### 3.1 Network State Vector & State Estimation
The system performs high-fidelity tracking of the plant-network state vector:
$x(t) = [V, I, f, THD, Q, P_{loss}, Z_{network}]$

Where:
- **$[V, I, f, THD, Q]$**: Grid-interface and power quality metrics.
- **$P_{loss}$**: Unavoidable conduction and network losses.
- **$Z_{network}$**: Equivalent network impedance for fault localization.

Note: Internal BESS states (SOC, SOH, T) are monitored at the module level via internal telemetry but are distinct from the network-level state estimation vector.

#### 3.2 Residual-Based Fault Detection
The framework estimates deviations from expected behavior using digital twin residuals:
$r(t) = y(t) - \hat{y}(t|x)$
Where $y(t)$ are measured variables and $\hat{y}$ is the digital twin prediction. The fault indicator $F(t) = ||r(t)||_W$ triggers diagnostic actions for inverter faults, thermal abnormalities, or battery degradation events.

#### 3.3 Monitoring & Estimation Objectives
1. **System Availability**: $\mathbb{P}(\text{instability}) \le \epsilon$ (no-collapse monitoring manifold).
2. **Degradation Monitoring**: Characterizing battery and PCU wear over time using internal telemetry and network-level impact.
3. **Estimation Accuracy**: Minimizing the estimation error covariance of the network state vector.

#### 3.4 Physical Power Plant Digital Twin
The plant environment represents the physical microgrid hardware:
- **Microgrid Assets**: 100kWp Solar PV, 50kW Primary Generation, and 100kWh BESS (208 modules).
- **Infrastructure**: Utility-scale power conditioning (150kVA PCU, Step-up transformer, MV Switchgear).
- **Balanced 3-Phase Interface**: Nodal monitoring points for real-time state estimation across feeders.
