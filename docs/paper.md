# Distribution System State Estimation Using Wavelet Decomposition with NFPP Sodium-Ion BESS Performance Evaluation

## Methodology

Base Cell Model (Literature-Aligned NFPP Sodium-Ion Twin System)
1. Electrochemical Core (DFN-Compatible Reaction)
The sodium iron pyrophosphate (NFPP) cathode operates via reversible sodium intercalation:
Na₂FePO₄P₂O₇ ⇌ NaₓFePO₄P₂O₇ + (2 − x)Na⁺ + (2 − x)e⁻
Theoretical specific capacity: ~95–100 mAh g⁻¹, consistent with reported polyanionic NFPP sodium-ion cathode systems used in pouch-scale prototypes.
2. Cathode Electrode Architecture (Composite Design)
NFPP cathodes in practical sodium-ion full cells follow a carbon–binder–domain composite structure processed using N-methyl-2-pyrrolidone (NMP)-based slurry casting.
Fixed composition:
	Sodium iron pyrophosphate (NFPP) active material: 85 wt% 
	Conductive carbon additive (carbon black / acetylene black): 8 wt% 
	Binder: polyvinylidene fluoride (PVDF): 7 wt% 
This structure reflects standard aluminum current collector-based cathodes used in sodium-ion pouch cells with high-density electrode compaction.
3. Anode Design (Hard Carbon System)
Hard carbon anodes are implemented as disordered carbon networks with nanopore and turbostratic domains enabling sodium storage through adsorption, intercalation, and pore filling mechanisms.
Fixed formulation:
	Hard carbon active material: 88 wt% 
	Conductive carbon additive: 6 wt% 
	Binder: polyvinylidene fluoride (PVDF): 6 wt% 
Practical specific capacity: 250–300 mAh g⁻¹, consistent with full-cell hard carbon sodium storage behavior.
4. Electrolyte System (Carbonate-Based Sodium Salt System)
The electrolyte follows a standard sodium-ion full-cell carbonate formulation:
	Sodium hexafluorophosphate (NaPF₆): 1.0 molar concentration 
	Sodium difluoro(oxalato)borate (NaDFOB): 0.2 molar concentration 
	Solvent system: ethylene carbonate and propylene carbonate in 1:1 volumetric ratio 
	Ionic conductivity: ~10 mS cm⁻¹ at 25°C
5. Electrolyte Additive System (Interphase Engineering)
Interfacial stability is controlled using electrolyte additives that regulate both solid electrolyte interphase and cathode electrolyte interphase formation:
	Fluoroethylene carbonate (FEC): 3 wt%
→ promotes stable solid electrolyte interphase (SEI) formation on the hard carbon anode 
	Vinylene carbonate (VC): 2 wt%
→ enhances SEI uniformity and suppresses continuous electrolyte decomposition 
	Sodium difluoro(oxalato)borate (NaDFOB): functions as both co-salt and cathode electrolyte interphase (CEI) stabilizer 
The SEI is a passivation layer formed on the anode that regulates sodium-ion transport and prevents continuous electrolyte decomposition, while the CEI stabilizes cathode surface reactions and mitigates structural degradation.
6. Pouch Cell Mechanical Architecture (Stacked Design)
The full cell follows a stacked pouch configuration consistent with sodium-ion prototype manufacturing systems:
	Form factor: stacked Z-fold pouch cell architecture 
	Nominal voltage: 3.0–3.2 volts 
	Target capacity class: 10 ampere-hour design point 
Layer stack:
	Cathode current collector: aluminum foil (~15 micrometers) 
	Anode current collector: copper foil (~10 micrometers) 
	Separator: polyolefin trilayer membrane (~20 micrometers) 
	External casing: poly-based moisture barrier (no aluminum laminate)
	Inner sealant: polypropylene-based sealing layer 

#### **Design Space:**
   
*   **Structural Parameters ($\theta_s$):** Electrode thickness ($L_c, L_a$), porosity ($\epsilon_c, \epsilon_a, \epsilon_{sep}$), tortuosity ($\tau$), active material loading and particle size ($r_p$).
*   **Material Parameters ($\theta_m$):** NFPP fraction, conductive carbon fraction, and electrolyte composition (concentration/salts)

#### **Layered Material Mapping**

This phase resolves performance properties for chemistry modifications using a decoupled architecture: a **Material Mapping Engine** for data resolution and a **Physics Layer** for property-to-parameter transformation.

*   **Decoupled Mapping Engine:** The framework implements a prioritized resolution flow (OQMD Exact $\rightarrow$ MP Exact $\rightarrow$ Class Baselines) for a fixed candidate space (Mn/Cr/Ni dopants, NaBOB/NaTCP salts, MTMS functionalization). Strict stability-sorting ensures ground-state accuracy.
*   **Physics Channel Models:** Performance deltas are derived through channel-specific physics models: Nernstian proxies for voltage shifts ($ΔV \propto -ΔE_f$), exponential thermal activation mapping for conductivity ($\sigma \propto \exp(-E_g/2kT)$), and interphase kinetic models for SEI growth, all scaled by a bounded stability realization factor.
*   **Electrolyte & Fluorine Reduction:** Selection of non-fluorinated salts to reduce environmental burden and cost. Primary candidates include **NaBOB** (Sodium bis(oxalato)borate) for stability and **NaTCP** (Sodium tricyanomethanide) for high performance.
*   **Electrode Doping:** Fe-site doping for cathodes using **Cr** (Cr³⁺ stabilizer), **Mn** (voltage booster), and **Ni** is evaluated via sensitivity-based optimization.
*   **Alkyl Silane Functionalization:** Implementation of hard carbon electrode functionalization using **methyltrimethoxysilane (MTMS)**. This process replaces surface –OH groups with –Si–O–R groups on the hard carbon electrode, increasing hydrophobicity and promoting a more uniform SEI layer. The model accounts for reduced SEI kinetics (slower growth and lower irreversible capacity fade), slower interfacial resistance growth over cycles, and optimized exchange current density resulting from improved surface wetting and local ion accessibility.
*   **Sensitivity-Driven Cell Parameter Optimization:** The projected design space ($\theta = [\theta_s, \theta_m]$) is explored with a hierarchical workflow that combines sensitivity screening, objective-specific SG-CEM refinement, and expensive stability filtering. In the implementation, the design vector is first perturbed around a nominal point to estimate the Jacobian of the energy, power, and stability responses; only the most influential variables for each objective are retained for optimization instead of searching the full design space at once.

#### BESS Robustness Evaluation Framework

The BESS is evaluated using the DFN electrochemical model coupled with the thermal model. The model provides the measurable simulation outputs required for performance evaluation including:
  Terminal voltage, \(V(t)\)
  Terminal current, \(I(t)\)
  Temperature, \(T(t)\)
  State of charge, \(SoC(t)\)
  Available capacity, \(Q(t)\)
  Energy throughput
The BESS is evaluated under simulated grid-outage, PV-firming, and variable C-rate dispatch profiles.

**Performance Measurements**
Each performance metric is calculated directly from the simulated measurements.

 * **Round-Trip Energy Efficiency (RTE)**: Measures the fraction of charging energy recovered during discharge
[\eta_{\mathrm{RTE}}=\frac{E_{\mathrm{dis}}}{E_{\mathrm{chg}}}] where
[E_{\mathrm{dis}}=\int_{\mathrm{discharge}} V(t)I(t)\,dt]
and [E_{\mathrm{chg}}=\int_{\mathrm{charge}} |V(t)I(t)|\,dt.]

 * **Coulombic Efficiency**: Measures the fraction of charge recovered in terms of electrical charge [\eta_C=\frac{Q_{\mathrm{dis}}}{Q_{\mathrm{chg}}}] with [Q_{\mathrm{dis}}=\int_{\mathrm{discharge}} |I(t)|\,dt,\qquad Q_{\mathrm{chg}}=\int_{\mathrm{charge}} |I(t)|\,dt.]

 * **Voltage Efficiency**: Represents the voltage-related loss independently of charge throughput [\eta_V=\frac{\eta_{\mathrm{RTE}}}{\eta_C}.]

 * **Usable Energy Capacity**: Measures the energy delivered over the defined operating SOC window [E_{\mathrm{usable}}=\int_{t_0}^{t_1}|V(t)I(t)|\,dt] where \(t_0\) and \(t_1\) correspond to the specified upper and lower SOC limits.

 * **Power Capability**: Measures the maximum deliverable electrical power during the simulated operating window [P_{\max}=\max_t |V(t)I(t)|.]

 * **Thermal Response**: Measures the temperature excursion produced during operation [\Delta T=T_{\max}-T_{\min}] and the maximum operating temperature is [T_{\max}=\max_t T(t).]

 * **Depth of Discharge**: For each simulated cycle [DoD=SoC_{\max}-SoC_{\min}.]

 * **Equivalent Full Cycles**: Accumulated energy throughput is converted into equivalent full cycles [EFC=\frac{\displaystyle\int |P(t)|\,dt}{2E_{\mathrm{rated}}}.]. The factor of \(2\) accounts for one complete charge and discharge throughput.

 * **Capacity Fade**: The loss of usable capacity relative to the initial condition is [F_Q(t)=1-\frac{Q_{\max}(t)}{Q_{\max}(0)}.]

 * **Cycle Life**: Cell life cycle is estimated from the simulated degradation trajectory as the point at which the battery reaches the prescribed minimum \(SoH\), [N_{\mathrm{life}}=\min\left\{N:SoH(N)\le SoH_{\mathrm{limit}}\right\}.]

 * **Calendar Life**: Where calendar-aging simulations are performed, the corresponding lifetime is:
[t_{\mathrm{life}}=\min\left\{t:SoH(t)\le SoH_{\mathrm{limit}}\right\}.]

 * **Levelized Cost of Storage**: For the economic assessment [LCOS=\frac{C_{\mathrm{capital}}+C_{\mathrm{replacement}}+C_{\mathrm{operation}}}{E_{\mathrm{lifetime,dis}}}]
where \(E_{\mathrm{lifetime,dis}}\) is the cumulative simulated energy delivered by the BESS.

**Limitations:**  While this work focuses on a foundational design space, the cell architecture remains amenable to further performance enhancement via composite electrode structuring, advanced pore network engineering, perturbing other dopant sites (beyond the Fe-site), and exploring a broader range of electrolyte systems (solvents and additives) to further enhance cycle life and energy density. The current optimization scope is intentionally streamlined to accommodate the computational constraints of the DFN solver.

---

## DSSE using Load Frequency Reconstruction and LV Transformer Signal Processing

In this research, state estimation in partially observed low-voltage (LV) distribution networks is accomplished using 36% consumer meter measurements and feeder head / boundary transformer measurements. Smart meters are used to estimate the number of unknown (unmetered) consumer units.

We estimate system states by representing the known network using load groups (representative energy classes or load profiles derived from smart meter observations). From the 36% consumer meter measurements, we extract the frequency of each representative energy group across the three feeders and global distribution system.

We reconstruct the LV network using **inverse-similarity weighting of local group frequency**:

[ w_g \propto \frac{f_g^{\mathrm{global}}}{f_g^{\mathrm{local}} + \epsilon} ]

where $f_g^{\mathrm{local}}$ is the local frequency of load group $g$ in the metered 36% sample, and $f_g^{\mathrm{global}}$ is the global distribution frequency across the system. This sampling weighting ensures that under-represented energy groups in local observations are prioritized during network reconstruction, while satisfying both local and global distributions for a sample size large enough to satisfy the feeder head measurements for the LV network.

We compare the estimated network state against ground truth and derive the load profile of the network by exploring transformer transients using Datasets 2, 3, and 4.

The mathematical formulation for consumer unit load frequency reconstruction is:

[ \hat{N}_{\mathrm{unmetered}}, \hat{P}_{\mathrm{unmetered}} = \Phi_{\mathrm{freq}}\left( M_{36\%}, M_{\mathrm{feeder}}; \mathcal{K}_{\mathrm{known}}, w_g \right) ]

where:
- $M_{36\%}$ denotes observations from 36% instrumented consumer smart meters;
- $M_{\mathrm{feeder}}$ denotes total feeder head / transformer secondary readings;
- $\mathcal{K}_{\mathrm{known}}$ represents the known LV network parameters;
- $w_g$ represents inverse-similarity weights for load group sampling;
- $\hat{N}_{\mathrm{unmetered}}$ is the estimated number of unmetered consumer units;
- $\hat{P}_{\mathrm{unmetered}}$ is the estimated active power load profile of unmetered consumer units.

Detailed physical parameters for the upstream station, substation transformer, and LV networks are documented in `docs/specs/upstream_distribution_station.md`, `docs/specs/upstream_transformer.md`, and `docs/specs/lv1/*`, `docs/specs/lv2/*`, `docs/specs/lv3/*`.

### System Model

#### 1. Known Plant Model

The upstream distribution station and MV feeders are completely known and serve as the boundary for observing downstream LV network states.

The plant model contains strictly distribution network elements and local sources:

* **Utility Source (Swing Bus)**: Ideal infinite bus connection to the transmission grid (33 kV LL RMS, $Z_{\mathrm{src}} = 0$).
* **Distribution Substation Transformer**: Substation transformer supplying the 11 kV medium-voltage bus (7.5 MVA, 33/11 kV, Dyn11).
* **Main Feeders**: Radial 11 kV feeders extending from the substation, characterized by known lengths and sequence impedances ($Z_1 = 0.25 + j0.35\ \Omega/\mathrm{km}$).
* **Fixed Set of Transformers**: Step-down 11/0.415 kV distribution transformers (`trans1`, `trans2`, `trans3`).
* **Consumer Load Circuits**: To accurately represent realistic residential, commercial, and industrial end-user devices, consumer equipment circuits are implemented compatibly across OpenDSS and ATP-EMTP:
  1. **AC Motor (`ac_motor`)**: Three-phase induction motor with stator resistance/inductance, magnetizing branch, rotor resistance/inductance, and mechanical inertia.
  2. **DC Motor + Inverter (`dc_motor_inverter`)**: Rectifier stage, DC-link capacitor, PWM H-bridge inverter, and DC motor armature $R_a, L_a$ with speed-dependent Back-EMF.
  3. **Microwave (`microwave`)**: Input rectifier, PFC stage, DC-link capacitor, high-voltage transformer, diode voltage doubler, and magnetron non-linear load.
  4. **Induction Plate (`induction_plate`)**: Input rectifier, DC-link, high-frequency resonant inverter, resonant capacitor, and induction coil $R_{\mathrm{eq}} + j\omega L_{\mathrm{eq}}$.
  5. **Compressor (`compressor`)**: Single-phase AC induction motor driving reciprocating/scroll compressor load torque.
  6. **Audio Amplifier (`audio_amplifier`)**: AC supply rectifier, DC-link supply capacitor bank, Class-D switching H-bridge, LC output filter, and speaker impedance.
  7. **Uninterruptible Power Supply / UPS (`ups`)**: Battery bank equivalent circuit, DC-link, bidirectional converter, and AC-side filter interface.
  8. **Industrial Fan (`industrial_fan`)**: Three-phase induction motor driving speed-squared aerodynamic fan load torque.

#### 2. Measurement Architecture

Measurements are obtained from two sensing layers: consumer smart meters (36% coverage) and transformer edge monitoring.

##### Consumer Smart-Meter Measurements
Selected candidate consumer nodes (36% coverage) are instrumented with smart meters to acquire:
  Three-phase voltage magnitude and phase angle
  Three-phase current magnitude and phase angle
  Active power (P), Reactive power (Q), Apparent power (S), Power factor (PF)
  Positive-, negative-, and zero-sequence components

##### Transformer Measurements
Each distribution transformer secondary serves as an edge measurement node representing the boundary interface to the LV network. Measurements include:
Primary Electrical Measurements
  Low-voltage terminal voltage magnitude and phase angle
  Low-voltage terminal current magnitude and phase angle
  Active power, Reactive power, Apparent power, Power factor

Dynamic Quantities
  Loading rate, overload duration, load recovery characteristics
  Transformer temperature
  High-frequency transient voltage and current waveforms ($V_{abc}(t), I_{abc}(t)$)

#### 3. Network Reconstruction via Inverse-Similarity Weighting

To estimate unmetered consumer units and derive the network load profile:
1. Construct initial network model from known buses and 36% metered consumer units.
2. Calculate local load group frequencies $f_g^{\mathrm{local}}$ and global distribution frequencies $f_g^{\mathrm{global}}$.
3. Compute inverse-similarity weights $w_g \propto f_g^{\mathrm{global}} / (f_g^{\mathrm{local}} + \epsilon)$ for sampling candidate energy groups.
4. Compute power residual $\Delta P = P_{\mathrm{feeder}} - \sum P_v$.
5. Reconstruct unmetered consumer units sampled according to inverse-similarity weights $w_g$ until reconstructed load satisfies $P_{\mathrm{feeder}}$.

#### 4. Simulation Framework and Datasets

The co-simulation framework generates four distinct datasets to evaluate load frequency reconstruction and transient observability:

1. **Dataset 1 (Load Frequency Reconstruction Dataset)**: Evaluates estimation of unmetered consumer units ($\hat{N}_{\mathrm{unmetered}}$) and total consumer units ($\hat{N}_{\mathrm{total}}$) under 36% consumer coverage using inverse-similarity weighted load group reconstruction.
   - **Ground-Truth Target Variables:** `gt_scenario_id`, `gt_feeder_id`, `known_number_of_buses`, `gt_total_consumer_units`, `gt_metered_consumer_units`, `gt_unmetered_consumer_units`, `gt_r_eq_ohm`, `gt_x_eq_ohm`, `gt_z_eq_ohm`.
   - **Estimator Predictions:** `est_total_consumer_units`, `est_metered_consumer_units`, `est_unmetered_consumer_units`, `est_unmetered_power_kw`, `est_r_eq_ohm`, `est_x_eq_ohm`, `est_z_eq_ohm`.

2. **Dataset 2 (Question 1 Event Pair Observability Dataset)**: Evaluates event pair observability across load-load, fault-fault, and load-fault pairs using 36% consumer coverage and feeder measurements under fixed baseline transformer specs and zero time shift.

3. **Dataset 3 (Question 2 Time Shift Operation Dataset)**: Evaluates residual magnitude variation under time shift operations ($t_{\mathrm{offset}} = 0.0\ \mathrm{s}$ vs $t_{\mathrm{offset}} > 0.0\ \mathrm{s}$) using dataset 3.

4. **Dataset 4 (Question 3 Transformer Specification Dataset)**: Evaluates how transformer specification variations affect event pair observability across load-load, fault-fault, and mixed pairs using dataset 4.

#### 5. Statistical Testing for Datasets 1, 2, 3, and 4

##### Statistical Testing for Dataset 1
Dataset 1 statistical analysis (`src/statistics/correlation.py`) evaluates the accuracy of `LoadFrequencyReconstructionEstimator` in recovering unmetered consumer units ($\hat{N}_{\mathrm{unmetered}}$) and network load parameters across 3 feeder subgroups (`feeder_1`, `feeder_2`, `feeder_3`).
- **Mean Absolute Error (MAE):** Evaluates unmetered consumer unit estimation accuracy $\mathrm{MAE}_{N_{\mathrm{unmetered}}} = \frac{1}{N} \sum |\hat{N}_{\mathrm{unmetered},i} - N_{\mathrm{unmetered},i}|$.
- **Root Mean Squared Error (RMSE):** Evaluates equivalent impedance estimation accuracy ($\mathrm{RMSE}_R, \mathrm{RMSE}_X, \mathrm{RMSE}_Z$).

##### Statistical Testing for Dataset 2
Factorial ANOVA analysis (`src/statistics/q1_event_pair_analysis.py`) evaluates event pair observability across pair categories (`load_load`, `fault_fault`, `load_fault`) using Dataset 2 under fixed baseline transformer specs and zero time shift:
- **Main Effect:** Evaluates $F_{\mathrm{voltage}}, p_{\mathrm{voltage}}$ and $F_{\mathrm{current}}, p_{\mathrm{current}}$ to test observability differences across pair categories.

##### Statistical Testing for Dataset 3
Levene / Brown-Forsythe variance analysis (`src/statistics/q2_time_shift_analysis.py`) evaluates residual magnitude variation under time shift operations ($t_{\mathrm{offset}} = 0$ vs $t_{\mathrm{offset}} > 0$) using Dataset 3 across:
- (i) Load switch event pairs
- (ii) Line fault event pairs
- (iii) Across load switch and fault pairs

##### Statistical Testing for Dataset 4
One-Way ANOVA testing (`src/statistics/q3_transformer_spec_analysis.py`) evaluates how transformer specification variations affect observability across pair categories using Dataset 4:
- **Transformer Spec Effect:** Measures $F_{\mathrm{spec}}, p_{\mathrm{spec}}$ across transformer specifications (`tx_spec_std_1500kva`, `tx_spec_high_z_1200kva`, `tx_spec_low_loss_2000kva`) under zero time shift.
