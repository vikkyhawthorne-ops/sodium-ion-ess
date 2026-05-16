import numpy as np
import pybamm

def nfpp_diffusivity_literature(sto, T):
    """
    Diffusivity of Na2FeP2O7.
    Reference: Typical polyanionic transport data.
    """
    D_ref = 1.0 * 10 ** (-14)
    E_D_s = 30000
    arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
    return D_ref * arrhenius

def nfpp_ocp_literature(sto):
    """
    OCP for Na2FeP2O7 vs Na/Na+.
    Plateau at ~3.0V.
    """
    u_eq = 3.11 - 0.5 * sto + 0.1 * np.exp(-100 * sto) - 0.1 * np.exp(-100 * (1 - sto))
    return u_eq

def hard_carbon_diffusivity_literature(sto, T):
    """
    Diffusivity of Hard Carbon.
    """
    D_ref = 5.0 * 10 ** (-15)
    E_D_s = 40000
    arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
    return D_ref * arrhenius

def hard_carbon_ocp_literature(sto):
    """
    OCP for Hard Carbon vs Na/Na+.
    """
    u_eq = 0.1 * np.exp(-20 * sto) + 0.05 * (1 - sto)
    return u_eq

def electrolyte_exchange_current_density_sodium(c_e, c_s_surf, c_s_max, T):
    """
    Exchange-current density for Na-ion intercalation.
    """
    m_ref = 1 * 10 ** (-6)
    E_r = 35000
    arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
    return m_ref * arrhenius * c_e**0.5 * c_s_surf**0.5 * (c_s_max - c_s_surf) ** 0.5

def get_parameter_values():
    """
    Base parameter set for NFPP Sodium-ion cell.
    Properties derived in src/calibration/calibrate_parameters.py
    """
    return {
        "chemistry": "sodium_ion",
        # cell (Design parameters from paper.md)
        "Negative current collector thickness [m]": 10e-06,
        "Negative electrode thickness [m]": 0.0001,
        "Separator thickness [m]": 20e-06,
        "Positive electrode thickness [m]": 0.0001,
        "Positive current collector thickness [m]": 15e-06,
        "Electrode height [m]": 0.137,
        "Electrode width [m]": 0.207,
        "Nominal cell capacity [A.h]": 1.0, # Base unit
        "Current function [A]": 1.0,
        "Contact resistance [Ohm]": 0,
        # negative electrode (Hard Carbon)
        "Negative electrode conductivity [S.m-1]": 256.0,
        "Maximum concentration in negative electrode [mol.m-3]": 16790.0,
        "Negative particle diffusivity [m2.s-1]": hard_carbon_diffusivity_literature,
        "Negative electrode OCP [V]": hard_carbon_ocp_literature,
        "Negative electrode porosity": 0.3,
        "Negative electrode active material volume fraction": 0.88,
        "Negative particle radius [m]": 5e-06,
        "Negative electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrode)": 1.5,
        "Negative electrode charge transfer coefficient": 0.5,
        "Negative electrode exchange-current density [A.m-2]": electrolyte_exchange_current_density_sodium,
        "Negative electrode density [kg.m-3]": 1500.0,
        "Negative electrode specific heat capacity [J.kg-1.K-1]": 700.0,
        "Negative electrode thermal conductivity [W.m-1.K-1]": 1.7,
        "Negative electrode OCP entropic change [V.K-1]": 0,
        # positive electrode (NFPP)
        "Positive electrode conductivity [S.m-1]": 50.0,
        "Maximum concentration in positive electrode [mol.m-3]": 11604.0,
        "Positive particle diffusivity [m2.s-1]": nfpp_diffusivity_literature,
        "Positive electrode OCP [V]": nfpp_ocp_literature,
        "Positive electrode porosity": 0.3,
        "Positive electrode active material volume fraction": 0.85,
        "Positive particle radius [m]": 1e-06,
        "Positive electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Positive electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode charge transfer coefficient": 0.5,
        "Positive electrode exchange-current density [A.m-2]": electrolyte_exchange_current_density_sodium,
        "Positive electrode density [kg.m-3]": 3200.0,
        "Positive electrode specific heat capacity [J.kg-1.K-1]": 700.0,
        "Positive electrode thermal conductivity [W.m-1.K-1]": 2.1,
        "Positive electrode OCP entropic change [V.K-1]": 0,
        # separator
        "Separator porosity": 0.5,
        "Separator Bruggeman coefficient (electrolyte)": 1.5,
        "Separator density [kg.m-3]": 1000.0,
        "Separator specific heat capacity [J.kg-1.K-1]": 700.0,
        "Separator thermal conductivity [W.m-1.K-1]": 0.16,
        # electrolyte (1.0M NaPF6 + 0.2M NaDFOB in EC:PC 1:1)
        "Initial concentration in electrolyte [mol.m-3]": 1200.0,
        "Cation transference number": 0.45,
        "Thermodynamic factor": 1.0,
        "Electrolyte diffusivity [m2.s-1]": 5e-10,
        "Electrolyte conductivity [S.m-1]": 1.0,
        # experiment
        "Reference temperature [K]": 298.15,
        "Ambient temperature [K]": 298.15,
        "Initial temperature [K]": 298.15,
        "Lower voltage cut-off [V]": 2.0,
        "Upper voltage cut-off [V]": 3.8,
        "Initial concentration in negative electrode [mol.m-3]": 16000,
        "Initial concentration in positive electrode [mol.m-3]": 500,
        "Number of electrodes connected in parallel to make a cell": 1.0,
        "Number of cells connected in series to make a battery": 1.0,
    }
