import numpy as np

def derive_material_properties():
    """
    Derives electrochemical parameters from theoretical and experimental values.
    References: Materials Project, docs/paper.md
    """
    F = 96485.332  # Faraday constant [C/mol]

    # 1. NFPP Cathode
    # Molar mass Na2FeP2O7
    M_nfpp = 275.77e-3 # [kg/mol]
    rho_nfpp = 3200.0   # [kg/m3] (Typical polyanionic density)

    # Theoretical capacity (1 electron)
    # Cap [Ah/kg] = (n * F / 3600) / M
    theoretical_cap_nfpp = (1 * F / 3600) / M_nfpp # approx 97.18 Ah/kg = 97.18 mAh/g

    # Maximum concentration [mol/m3]
    # c_max = rho / M
    c_max_nfpp = rho_nfpp / M_nfpp

    # 2. Hard Carbon Anode
    rho_hc = 1500.0 # [kg/m3] (MTI, Ossila)
    # Practical capacity 300 mAh/g = 0.3 Ah/g = 300 Ah/kg
    cap_hc_ah_kg = 300.0
    # c_max = (rho * Cap_Ah_kg) / (F/3600)
    c_max_hc = (rho_hc * cap_hc_ah_kg) / (F / 3600)

    print(f"NFPP Theoretical Capacity: {theoretical_cap_nfpp:.2f} mAh/g")
    print(f"NFPP Max Concentration: {c_max_nfpp:.2f} mol/m3")
    print(f"Hard Carbon Max Concentration: {c_max_hc:.2f} mol/m3")

    return {
        "c_max_nfpp": c_max_nfpp,
        "c_max_hc": c_max_hc,
        "rho_nfpp": rho_nfpp,
        "rho_hc": rho_hc,
    }

if __name__ == "__main__":
    derive_material_properties()
