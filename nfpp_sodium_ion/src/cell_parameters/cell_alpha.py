import numpy as np
import pybamm
from ..calibration.derivation import get_derived_parameters
from .data.electrodes.nfpp_cathode import NfppCathodeParameters
from .data.electrodes.hard_carbon_anode import HardCarbonAnodeParameters
from .data.electrodes.separator import SeparatorParameters
from .data.mechanics.elastic_moduli import ElasticModuliModel
from .data.mechanics.thermal_expansion import ThermalExpansionModel
from .data.mechanics.swelling_coefficients import SwellingCoefficientModel
from .data.thermal.heat_capacity import HeatCapacityModel
from .data.thermal.thermal_conductivity import ThermalConductivityModel
from .data.thermal.heat_generation import HeatGenerationModel
from .data.kinetics.exchange_current_density import ExchangeCurrentDensityModel
from .data.kinetics.reaction_rates import ReactionRateModel
from .data.degradation.sei_growth import SeiGrowthModel
from .data.degradation.cei_growth import CeiGrowthModel
from .data.degradation.loss_of_lithium_equivalent import LossOfSodiumEquivalentModel
from .data.base.cell import CellParameters

def nfpp_diffusivity_literature(sto, T):
    derived = get_derived_parameters()
    E_D_s = derived["e_a_diff_p"]
    arrhenius = np.exp(E_D_s / derived["r_gas"] * (1 / derived["t_ref"] - 1 / T))
    return derived["diff_p_ref"] * arrhenius

def nfpp_ocp_literature(sto):
    # Ref: paper.md
    u_eq = 3.11 - 0.5 * sto + 0.1 * np.exp(-100 * sto) - 0.1 * np.exp(-100 * (1 - sto))
    return u_eq

def hard_carbon_diffusivity_literature(sto, T):
    derived = get_derived_parameters()
    E_D_s = derived["e_a_diff_n"]
    arrhenius = np.exp(E_D_s / derived["r_gas"] * (1 / derived["t_ref"] - 1 / T))
    return derived["diff_n_ref"] * arrhenius

def hard_carbon_ocp_literature(sto):
    # Ref: benchmark hard carbon data
    u_eq = 0.1 * np.exp(-20 * sto) + 0.05 * (1 - sto)
    return u_eq

def exchange_current_density_sodium(c_e, c_s_surf, c_s_max, T):
    derived = get_derived_parameters()
    m_ref = 2e-5 # generic exchange scale
    E_r = derived["e_a_rxn"]
    arrhenius = np.exp(E_r / derived["r_gas"] * (1 / derived["t_ref"] - 1 / T))
    return m_ref * arrhenius * c_e**0.5 * c_s_surf**0.5 * (c_s_max - c_s_surf) ** 0.5

def current_function(t):
    return pybamm.InputParameter("Current [A]")

def get_parameter_values():
    cathode = NfppCathodeParameters()
    anode = HardCarbonAnodeParameters()
    sep = SeparatorParameters()
    cell = CellParameters()
    elastic = ElasticModuliModel()
    thermal_exp = ThermalExpansionModel()
    swelling = SwellingCoefficientModel()
    cp_model = HeatCapacityModel()
    tc_model = ThermalConductivityModel()
    hg_model = HeatGenerationModel()
    derived = get_derived_parameters()

    return {
        "chemistry": "sodium_ion",
        "Negative current collector thickness [m]": cell.anode_collector_thickness_um * 1e-6,
        "Negative electrode thickness [m]": derived["anode_thickness"],
        "Separator thickness [m]": sep.thickness_um * 1e-6,
        "Positive electrode thickness [m]": derived["cathode_thickness"],
        "Positive current collector thickness [m]": cell.cathode_collector_thickness_um * 1e-6,
        "Electrode height [m]": derived["l_electrode"],
        "Electrode width [m]": derived["w_electrode"],
        "Number of electrodes connected in parallel to make a cell": float(derived["n_layers_10ah"]),
        "Number of cells connected in series to make a battery": 1,
        "Number of strings connected in parallel to make a battery": 1,
        "Nominal cell capacity [A.h]": cell.capacity_ah,
        "Current function [A]": current_function,
        "Contact resistance [Ohm]": derived["r_contact"],
        "Negative electrode conductivity [S.m-1]": 256.0,
        "Maximum concentration in negative electrode [mol.m-3]": derived["c_max_n"],
        "Negative particle diffusivity [m2.s-1]": hard_carbon_diffusivity_literature,
        "Negative electrode OCP [V]": hard_carbon_ocp_literature,
        "Negative electrode porosity": 0.3,
        "Negative electrode active material volume fraction": derived["eps_am_n"],
        "Negative particle radius [m]": 5e-06,
        "Negative electrode Bruggeman coefficient (electrolyte)": derived["bruggeman"],
        "Negative electrode Bruggeman coefficient (electrode)": derived["bruggeman"],
        "Negative electrode charge transfer coefficient": derived["alpha_ct"],
        "Negative electrode exchange-current density [A.m-2]": exchange_current_density_sodium,
        "Negative electrode density [kg.m-3]": anode.density_kg_m3,
        "Negative electrode Young's modulus [Pa]": derived["youngs_modulus_n"],
        "Negative electrode Poisson's ratio": derived["poisson_ratio_n"],
        "Negative electrode OCP entropic change [V.K-1]": 0,
        "Negative electrode specific heat capacity [J.kg-1.K-1]": cp_model.reference_cp_j_kg_k,
        "Negative electrode thermal conductivity [W.m-1.K-1]": derived["tc_n"],
        "Positive electrode conductivity [S.m-1]": 50.0,
        "Maximum concentration in positive electrode [mol.m-3]": derived["c_max_p"],
        "Positive particle diffusivity [m2.s-1]": nfpp_diffusivity_literature,
        "Positive electrode OCP [V]": nfpp_ocp_literature,
        "Positive electrode porosity": 0.3,
        "Positive electrode active material volume fraction": derived["eps_am_p"],
        "Positive particle radius [m]": 1e-06,
        "Positive electrode Bruggeman coefficient (electrolyte)": derived["bruggeman"],
        "Positive electrode Bruggeman coefficient (electrode)": derived["bruggeman"],
        "Positive electrode charge transfer coefficient": derived["alpha_ct"],
        "Positive electrode exchange-current density [A.m-2]": exchange_current_density_sodium,
        "Positive electrode density [kg.m-3]": cathode.density_kg_m3,
        "Positive electrode Young's modulus [Pa]": elastic.youngs_modulus_pa,
        "Positive electrode Poisson's ratio": elastic.poisson_ratio,
        "Positive electrode OCP entropic change [V.K-1]": 0,
        "Positive electrode specific heat capacity [J.kg-1.K-1]": cp_model.reference_cp_j_kg_k,
        "Positive electrode thermal conductivity [W.m-1.K-1]": tc_model.reference_k_w_m_k,
        "Separator porosity": sep.porosity,
        "Separator Bruggeman coefficient (electrolyte)": derived["bruggeman"],
        "Separator density [kg.m-3]": derived["sep_density"],
        "Separator specific heat capacity [J.kg-1.K-1]": derived["sep_cp"],
        "Separator thermal conductivity [W.m-1.K-1]": derived["sep_tc"],
        "Initial concentration in electrolyte [mol.m-3]": derived["conc_e"],
        "Cation transference number": derived["transference_number"],
        "Thermodynamic factor": 1.0,
        "Electrolyte diffusivity [m2.s-1]": derived["diff_e_ref"],
        "Electrolyte conductivity [S.m-1]": derived["cond_e_ref"],
        "Reference temperature [K]": derived["t_ref"],
        "Ambient temperature [K]": derived["t_ref"],
        "Initial temperature [K]": derived["t_ref"],
        "Lower voltage cut-off [V]": derived["nominal_voltage"] * 0.65, # benchmark window
        "Upper voltage cut-off [V]": derived["nominal_voltage"] * 1.25,
        "Initial concentration in negative electrode [mol.m-3]": 0.95 * derived["c_max_n"],
        "Initial concentration in positive electrode [mol.m-3]": 0.05 * derived["c_max_p"],
        "Cell volume [m3]": derived["cell_volume"],
        "Cell cooling surface area [m2]": derived["surface_area"],

        # SEI parameters
        "Initial SEI thickness [m]": 5e-9,
        "Initial inner SEI thickness [m]": 2.5e-9,
        "Initial outer SEI thickness [m]": 2.5e-9,
        "SEI partial molar volume [m3.mol-1]": derived["sei_partial_molar_volume"],
        "Inner SEI partial molar volume [m3.mol-1]": derived["sei_partial_molar_volume"],
        "Outer SEI partial molar volume [m3.mol-1]": derived["sei_partial_molar_volume"],
        "SEI resistivity [Ohm.m]": derived["sei_resistivity"],
        "SEI reaction exchange current density [A.m-2]": derived["sei_exchange_current"],
        "SEI kinetics equilibrium potential [V]": derived["sei_kinetics_eq_potential"],
        "Inner SEI electron conductivity [S.m-1]": derived["sei_inner_sigma"],
        "Inner SEI lithium interstitial diffusivity [m2.s-1]": derived["sei_diff_interstitial"],
        "Outer SEI lithium interstitial diffusivity [m2.s-1]": derived["sei_diff_interstitial"],
        "Typical SEI concentration [mol.m-3]": derived["sei_typical_conc"],
        "Bulk solvent concentration [mol.m-3]": derived["bulk_solvent_concentration"],
        "SEI solvent diffusivity [m2.s-1]": derived["sei_solvent_diffusivity"],
        "SEI growth activation energy [J.mol-1]": 0.0,
        "SEI open-circuit potential [V]": derived["sei_ocp"],
        "Ratio of lithium moles to SEI moles": 2.0,

        # LAM parameters
        "Negative electrode LAM constant proportional term [s-1]": derived["lam_prop_term"],
        "Negative electrode LAM constant exponential term": 2.0,
        "Negative electrode critical stress [Pa]": derived["critical_stress"],
        "Positive electrode LAM constant proportional term [s-1]": derived["lam_prop_term"],
        "Positive electrode LAM constant exponential term": 2.0,
        "Positive electrode critical stress [Pa]": derived["critical_stress"],
        "Negative electrode partial molar volume [m3.mol-1]": derived["partial_molar_vol_n"],
        "Positive electrode partial molar volume [m3.mol-1]": derived["partial_molar_vol_p"],
        "Negative electrode reference concentration for free of deformation [mol.m-3]": 0.0,
        "Positive electrode reference concentration for free of deformation [mol.m-3]": 0.0,

        # Thermal parameters
        "Negative current collector surface heat transfer coefficient [W.m-2.K-1]": derived["total_htc"],
        "Positive current collector surface heat transfer coefficient [W.m-2.K-1]": derived["total_htc"],
        "Negative tab heat transfer coefficient [W.m-2.K-1]": derived["total_htc"],
        "Positive tab heat transfer coefficient [W.m-2.K-1]": derived["total_htc"],
        "Edge heat transfer coefficient [W.m-2.K-1]": derived["total_htc"],
        "Total heat transfer coefficient [W.m-2.K-1]": derived["total_htc"],
        "Negative current collector conductivity [S.m-1]": derived["cu_sigma"],
        "Positive current collector conductivity [S.m-1]": derived["al_sigma"],
        "Negative current collector density [kg.m-3]": derived["cu_density"],
        "Positive current collector density [kg.m-3]": derived["al_density"],
        "Negative current collector specific heat capacity [J.kg-1.K-1]": derived["cu_cp"],
        "Positive current collector specific heat capacity [J.kg-1.K-1]": derived["al_cp"],
        "Negative current collector thermal conductivity [W.m-1.K-1]": derived["cu_tc"],
        "Positive current collector thermal conductivity [W.m-1.K-1]": derived["al_tc"],
        "Negative tab width [m]": 0.01,
        "Positive tab width [m]": 0.01,
    }
