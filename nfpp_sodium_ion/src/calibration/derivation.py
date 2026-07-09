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
CARBON_DENSITY = 2000.0      # [kg/m3]
BINDER_DENSITY = 1780.0      # [kg/m3] (PVDF)

# --- 2. Collector Properties (Authoritative Sources) ---
# Al (Positive CC): CRC Handbook of Chemistry and Physics
AL_DENSITY = 2700.0          # [kg/m3]
AL_SPECIFIC_HEAT = 897.0     # [J/kg-K]
AL_THERMAL_COND = 237.0      # [W/m-K]

# Cu (Negative CC): CRC Handbook of Chemistry and Physics
CU_DENSITY = 8960.0          # [kg/m3]
CU_SPECIFIC_HEAT = 385.0     # [J/kg-K]
CU_THERMAL_COND = 401.0      # [W/m-K]

# --- 3. SEI & Solvent Physics ---
# Bulk Solvent Concentration derivation for EC:PC 1:1
# Ref: Journal of The Electrochemical Society, 164 (1) A6356-A6365 (2017)
# rho_EC = 1320 kg/m3, rho_PC = 1200 kg/m3
# Mw_EC = 88.06 g/mol, Mw_PC = 102.09 g/mol
# Volumetric avg density ~ 1260 kg/m3. Avg Mw ~ 95.08 g/mol
SOLVENT_CONCENTRATION = (1260.0 / 0.09508) # ~13251 mol/m3 (pure)
# Effective bulk concentration in 1.2M electrolyte:
BULK_SOLVENT_CONCENTRATION = 2636.0 # mol/m3 (Ref: Safari et al. 2009 for SEI models)

# SEI solvent diffusivity: Safari et al. 2009, J. Electrochem. Soc., 156, A145.
SEI_SOLVENT_DIFFUSIVITY = 2.5e-22 # [m2/s]

def compute_volume_fractions(wt_am, wt_c, wt_b, rho_am, rho_c, rho_b, porosity):
    v_am = wt_am / rho_am
    v_c = wt_c / rho_c
    v_b = wt_b / rho_b
    v_total_solid = v_am + v_c + v_b
    eps_am = (1 - porosity) * (v_am / v_total_solid)
    return eps_am

def get_derived_parameters():
    F = 96485.332
    c_max_p = NFPP_DENSITY / NFPP_MOLAR_MASS
    c_max_n = (HC_PRACTICAL_CAPACITY_MAH_G * HC_DENSITY * 3600.0) / F

    eps_am_p = compute_volume_fractions(0.85, 0.08, 0.07, NFPP_DENSITY, CARBON_DENSITY, BINDER_DENSITY, 0.3)
    eps_am_n = compute_volume_fractions(0.88, 0.06, 0.06, HC_DENSITY, CARBON_DENSITY, BINDER_DENSITY, 0.3)

    # Pouch Cell Dimensions
    L = 0.130
    W = 0.070
    t_cell = 0.010
    cell_volume = L * W * t_cell
    # Surface Area (2 * L*W + 2 * L*t + 2 * W*t)
    surface_area = 2 * (L*W + L*t_cell + W*t_cell)

    # Simulation-based layer determination
    L_p = 0.0001
    cap_layer = (L * W * L_p * eps_am_p * c_max_p * F) / 3600
    n_layers = int(np.ceil(10.0 / cap_layer))

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
        "al_density": AL_DENSITY,
        "al_cp": AL_SPECIFIC_HEAT,
        "al_tc": AL_THERMAL_COND,
        "cu_density": CU_DENSITY,
        "cu_cp": CU_SPECIFIC_HEAT,
        "cu_tc": CU_THERMAL_COND,
        "total_htc": 10.0 # Ref: lumped thermal convection for pouch cells
    }
