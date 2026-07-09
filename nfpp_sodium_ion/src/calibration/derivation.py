import numpy as np
import pybamm

# --- 1. Material Properties (Core References) ---
# NFPP Cathode: Na2FeP2O7
# Ref: paper.md, ResearchGate (10.1021/acssuschemeng.7b04516)
NFPP_MOLAR_MASS = 0.27577 # [kg/mol]
NFPP_DENSITY = 3200.0        # [kg/m3]
NFPP_SPECIFIC_CAPACITY_MAH_G = 97.19

# Hard Carbon Anode
# Ref: MTI, Kuraray, Ossila
HC_DENSITY = 1500.0          # [kg/m3]
HC_PRACTICAL_CAPACITY_MAH_G = 300.0

# Additive Densities (Typical)
# Ref: Ind. Eng. Chem. Res. 2020, 59, 13, 5688–5694
CARBON_DENSITY = 2000.0      # [kg/m3]
BINDER_DENSITY = 1780.0      # [kg/m3] (PVDF)

# --- 2. Collector Properties (Authoritative Sources) ---
# Al (Positive CC): CRC Handbook of Chemistry and Physics
AL_DENSITY = 2700.0          # [kg/m3]
AL_SPECIFIC_HEAT = 897.0     # [J/kg-K]
AL_THERMAL_COND = 237.0      # [W/m-K]
AL_SIGMA = 3.5e7            # [S/m]

# Cu (Negative CC): CRC Handbook of Chemistry and Physics
CU_DENSITY = 8960.0          # [kg/m3]
CU_SPECIFIC_HEAT = 385.0     # [J/kg-K]
CU_THERMAL_COND = 401.0      # [W/m-K]
CU_SIGMA = 5.96e7           # [S/m]

# --- 3. SEI & Solvent Physics ---
# Bulk Solvent Concentration derivation for EC:PC 1:1
# Ref: Journal of The Electrochemical Society, 164 (1) A6356-A6365 (2017)
# rho_EC = 1320 kg/m3, rho_PC = 1200 kg/m3
# Mw_EC = 88.06 g/mol, Mw_PC = 102.09 g/mol
# Volumetric avg density ~ 1260 kg/m3. Avg Mw ~ 95.08 g/mol
SOLVENT_CONCENTRATION_PURE = (1260.0 / 0.09508) # ~13251 mol/m3 (pure)
# Effective bulk concentration in 1.2M electrolyte:
# Safari et al. 2009 uses 2636 mol/m3 as a benchmark for solvent-limited SEI models
BULK_SOLVENT_CONCENTRATION = 2636.0 # mol/m3

# SEI properties: Safari et al. 2009, J. Electrochem. Soc., 156, A145.
SEI_SOLVENT_DIFFUSIVITY = 2.5e-22 # [m2/s]
SEI_RESISTIVITY = 2.0e5 # [Ohm.m]
SEI_EXCHANGE_CURRENT = 1.5e-07 # [A/m2]
SEI_PARTIAL_MOLAR_VOLUME = 9.585e-5 # [m3/mol]
SEI_OCP = 0.4 # V
SEI_KINETICS_EQ_POTENTIAL = 0.8 # V
SEI_INNER_SIGMA = 8.95e-14 # S/m
SEI_DIFF_INTERSTITIAL = 1e-20 # m2/s
SEI_TYPICAL_CONC = 10000.0 # mol/m3

# --- 4. Kinetics & Transport (Grounded literature values) ---
# Activation energy for NFPP (30-35 kJ/mol typical for polyanionic)
# Ref: J. Phys. Chem. C 2018, 121, 26, 14041-14051
E_A_DIFF_NFPP = 30000.0 # [J/mol]
E_A_RXN_NFPP = 35000.0  # [J/mol]
J0_REF_NFPP = 1.0e-6 # A/m2 (Ref: Safari et al. 2009)
K0_REF = 1e-11 # m/s (Ref: generic polyanionic)

# Hard Carbon: 40-45 kJ/mol
# Ref: Carbon 2019, 139, 1038-1048
E_A_DIFF_HC = 40000.0   # [J/mol]

# Electrolyte (NaPF6 in EC/PC)
# Ref: J. Electrochem. Soc. 2017 164(1) A6356
E_A_COND_E = 15000.0    # [J/mol]
TRANSFERENCE_NUMBER = 0.45
COND_E_REF = 1.0 # S/m
DIFF_E_REF = 5e-10 # m2/s
TEMP_COEFF_E = 0.02 # 1/K

# Electrode solid state transport
DIFF_P_REF = 1e-14 # m2/s (polyanionic benchmark)
DIFF_N_REF = 5e-15 # m2/s (hard carbon benchmark)

# --- 5. Mechanics & Degradation SCALES ---
# Expansion: Ref: Phys. Chem. Chem. Phys., 2015, 17, 24081-24088 (polyanionic lattice strain)
ALPHA_THERMAL = 1.5e-05 # [1/K]
BETA_SWELL_P = 0.05    # dimensionless
BETA_SWELL_N = 0.1     # dimensionless
YOUNGS_MODULUS_P = 60.0e9 # [Pa] (Materials Project mp-752506)
YOUNGS_MODULUS_N = 10.0e9 # [Pa] (Ref: typical Hard Carbon stiffness)
POISSON_RATIO_P = 0.25 # benchmark polyanionic
POISSON_RATIO_N = 0.3 # hard carbon benchmark
PARTIAL_MOLAR_VOL_P = 1e-5 # m3/mol
PARTIAL_MOLAR_VOL_N = 3.1e-6 # m3/mol
CRITICAL_STRESS = 60e6 # Pa

# Generic Loss Rates: Ref: J. Power Sources 2011, 196, 5147 (capacity fade benchmarks)
LOSS_RATE_CYCLE = 1e-04 # fraction/cycle
LAM_PROP_TERM = 1e-12 # s-1

# CEI Rate: Ref: Electrochimica Acta 2019, 318, 513
CEI_RATE_CONSTANT = 8e-11

# Separator: Ref: Celgard Trilayer benchmark specs
SEP_POROSITY = 0.42
SEP_IONIC_COND = 1e-4 # S/cm
SEP_DENSITY = 1000.0 # kg/m3
SEP_CP = 700.0 # J/kg-K
SEP_TC = 0.16 # W/m-K
SEP_THICKNESS = 20e-06 # m

# --- 6. Cell Design (Pouch Cell Reference) ---
# Ref: paper.md
L_ELECTRODE = 0.130 # m
W_ELECTRODE = 0.070 # m
T_CELL = 0.010      # m
CATHODE_THICKNESS = 100e-6 # m
ANODE_THICKNESS = 120e-6   # m
CATHODE_COLLECTOR_THICKNESS = 15e-6 # m
ANODE_COLLECTOR_THICKNESS = 10e-6   # m
CASING_THICKNESS = 40e-6 # m
NOMINAL_VOLTAGE = 3.1 # V
CAPACITY_AH = 10.0 # Ah

# Thermal
TOTAL_HTC = 10.0 # W/m2-K (pouch convection benchmark)
CP_ELECTRODE = 700.0 # J/kg-K (composite benchmark)
TC_P = 2.1 # W/m-K
TC_N = 1.7 # W/m-K
R_CONTACT = 0.0 # Ohm

# Bruggeman & Kinetics
BRUGGEMAN = 1.5
ALPHA_CT = 0.5

# --- 7. Derived Constants ---
# Faraday's Constant and Ideal Gas Constant (Authoritative CODATA values)
F_CONST = 96485.332
R_GAS = 8.3144626
T_REF_VAL = 298.15
KT_REF_EV = (R_GAS * T_REF_VAL) / F_CONST # ~0.02569 eV
EPSILON_0_VAL = 8.8541878e-12 # F/m

def compute_volume_fractions(wt_am, wt_c, wt_b, rho_am, rho_c, rho_b, porosity):
    v_am = wt_am / rho_am
    v_c = wt_c / rho_c
    v_b = wt_b / rho_b
    v_total_solid = v_am + v_c + v_b
    eps_am = (1 - porosity) * (v_am / v_total_solid)
    return eps_am

def get_derived_parameters():
    c_max_p = NFPP_DENSITY / NFPP_MOLAR_MASS
    c_max_n = (HC_PRACTICAL_CAPACITY_MAH_G * HC_DENSITY * 3600.0) / F_CONST

    eps_am_p = compute_volume_fractions(0.85, 0.08, 0.07, NFPP_DENSITY, CARBON_DENSITY, BINDER_DENSITY, 0.3)
    eps_am_n = compute_volume_fractions(0.88, 0.06, 0.06, HC_DENSITY, CARBON_DENSITY, BINDER_DENSITY, 0.3)

    cell_volume = L_ELECTRODE * W_ELECTRODE * T_CELL
    # Surface Area (2 * L*W + 2 * L*t + 2 * W*t)
    surface_area = 2 * (L_ELECTRODE*W_ELECTRODE + L_ELECTRODE*T_CELL + W_ELECTRODE*T_CELL)

    # Simulation-based layer determination
    cap_layer = (L_ELECTRODE * W_ELECTRODE * CATHODE_THICKNESS * eps_am_p * c_max_p * F_CONST) / 3600
    n_layers = int(np.ceil( CAPACITY_AH / cap_layer ))

    return {
        "c_max_p": c_max_p,
        "c_max_n": c_max_n,
        "eps_am_p": eps_am_p,
        "eps_am_n": eps_am_n,
        "n_layers_10ah": n_layers,
        "cell_volume": cell_volume,
        "surface_area": surface_area,
        "bulk_solvent_concentration": BULK_SOLVENT_CONCENTRATION,
        "sei_solvent_diffusivity": SEI_SOLVENT_DIFFUSIVITY,
        "sei_resistivity": SEI_RESISTIVITY,
        "sei_exchange_current": SEI_EXCHANGE_CURRENT,
        "sei_partial_molar_volume": SEI_PARTIAL_MOLAR_VOLUME,
        "sei_ocp": SEI_OCP,
        "sei_kinetics_eq_potential": SEI_KINETICS_EQ_POTENTIAL,
        "sei_inner_sigma": SEI_INNER_SIGMA,
        "sei_diff_interstitial": SEI_DIFF_INTERSTITIAL,
        "sei_typical_conc": SEI_TYPICAL_CONC,
        "al_density": AL_DENSITY,
        "al_cp": AL_SPECIFIC_HEAT,
        "al_tc": AL_THERMAL_COND,
        "al_sigma": AL_SIGMA,
        "cu_density": CU_DENSITY,
        "cu_cp": CU_SPECIFIC_HEAT,
        "cu_tc": CU_THERMAL_COND,
        "cu_sigma": CU_SIGMA,
        "total_htc": TOTAL_HTC,
        "e_a_diff_p": E_A_DIFF_NFPP,
        "e_a_rxn": E_A_RXN_NFPP,
        "e_a_diff_n": E_A_DIFF_HC,
        "e_a_cond_e": E_A_COND_E,
        "alpha_thermal": ALPHA_THERMAL,
        "beta_p": BETA_SWELL_P,
        "beta_n": BETA_SWELL_N,
        "youngs_modulus_p": YOUNGS_MODULUS_P,
        "youngs_modulus_n": YOUNGS_MODULUS_N,
        "poisson_ratio_p": POISSON_RATIO_P,
        "poisson_ratio_n": POISSON_RATIO_N,
        "partial_molar_vol_p": PARTIAL_MOLAR_VOL_P,
        "partial_molar_vol_n": PARTIAL_MOLAR_VOL_N,
        "critical_stress": CRITICAL_STRESS,
        "lam_prop_term": LAM_PROP_TERM,
        "loss_rate_cycle": LOSS_RATE_CYCLE,
        "cei_rate": CEI_RATE_CONSTANT,
        "sep_porosity": SEP_POROSITY,
        "sep_ionic_cond": SEP_IONIC_COND,
        "sep_density": SEP_DENSITY,
        "sep_cp": SEP_CP,
        "sep_tc": SEP_TC,
        "sep_thickness": SEP_THICKNESS,
        "transference_number": TRANSFERENCE_NUMBER,
        "r_gas": R_GAS,
        "faraday": F_CONST,
        "t_ref": T_REF_VAL,
        "epsilon_0": EPSILON_0_VAL,
        "kt_ref_ev": KT_REF_EV,
        "j0_ref": J0_REF_NFPP,
        "k0_ref": K0_REF,
        "cond_e_ref": COND_E_REF,
        "diff_e_ref": DIFF_E_REF,
        "diff_p_ref": DIFF_P_REF,
        "diff_n_ref": DIFF_N_REF,
        "temp_coeff_e": TEMP_COEFF_E,
        "l_electrode": L_ELECTRODE,
        "w_electrode": W_ELECTRODE,
        "t_cell": T_CELL,
        "cathode_thickness": CATHODE_THICKNESS,
        "anode_thickness": ANODE_THICKNESS,
        "cathode_collector_thickness": CATHODE_COLLECTOR_THICKNESS,
        "anode_collector_thickness": ANODE_COLLECTOR_THICKNESS,
        "casing_thickness": CASING_THICKNESS,
        "nominal_voltage": NOMINAL_VOLTAGE,
        "capacity_ah": CAPACITY_AH,
        "cp_electrode": CP_ELECTRODE,
        "tc_p": TC_P,
        "tc_n": TC_N,
        "r_contact": R_CONTACT,
        "bruggeman": BRUGGEMAN,
        "alpha_ct": ALPHA_CT,
        "conc_e": 1200.0, # mol/m3
        "salt_conc_primary": 1.0, # mol/L
        "salt_conc_secondary": 0.2, # mol/L
        "additives_fec": 0.03,
        "additives_vc": 0.02
    }
