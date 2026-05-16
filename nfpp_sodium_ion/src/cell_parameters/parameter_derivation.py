import numpy as np

# --- 1. Material Properties (Core References) ---
F = 96485.332

# NFPP Cathode: Na2FeP2O7
# Ref: paper.md, ResearchGate (10.1021/acssuschemeng.7b04516)
NFPP_MOLAR_MASS = 275.77e-3 # [kg/mol]
NFPP_DENSITY = 3200.0        # [kg/m3]
NFPP_SPECIFIC_CAPACITY_MAH_G = 97.19

# Hard Carbon Anode
# Ref: MTI, Kuraray, Ossila
HC_DENSITY = 1500.0          # [kg/m3]
HC_PRACTICAL_CAPACITY_MAH_G = 300.0

def compute_parameters():
    # c_max [mol/m3]
    # NFPP: 1 mole of Na per formula unit (for 1e- reaction)
    # rho = M * c_max => c_max = rho / M
    c_max_p = NFPP_DENSITY / NFPP_MOLAR_MASS

    # Hard Carbon:
    # Practical capacity [Ah/kg] = (c_max * F / 3600) / rho
    # c_max = (Cap_Ah_kg * rho * 3600.0) / F
    cap_hc_ah_kg = HC_PRACTICAL_CAPACITY_MAH_G
    c_max_hc = (cap_hc_ah_kg * HC_DENSITY * 3600.0) / F

    # Area = 0.137 * 0.207 = 0.028359 m2
    # Capacity for 1 layer = Area * L * eps * c_max * F / 3600
    # = 0.028359 * 0.0001 * 0.85 * 11604 * 96485 / 3600 = 0.748 Ah
    # For 10Ah, N_layers = 10 / 0.748 = 13.3 layers.

    return {
        "Positive max concentration [mol.m-3]": c_max_p,
        "Negative max concentration [mol.m-3]": c_max_hc,
        "Recommended N_layers for 10Ah": 14,
    }

if __name__ == "__main__":
    params = compute_parameters()
    for k, v in params.items():
        print(f"{k}: {v:.4f}")
