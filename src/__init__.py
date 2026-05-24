"""Simulation and Model Infrastructure.

Provides the core simulation drivers and platform infrastructure for
electrochemical-thermal and structural mechanics modeling.
"""

from .simulation.utilities.electrochemical.pybamm_driver import ElectrochemicalThermalDriverModel
from .simulation.utilities.thermal.pybamm_thermal import ThermalFieldModel
from .simulation.utilities.mechanical.fenics_model import ThermoelasticStrainModel

__all__ = [
    "ElectrochemicalThermalDriverModel",
    "ThermalFieldModel",
    "ThermoelasticStrainModel",
    "SimulationPlatform",
]

class SimulationPlatform:
    """Infrastructure layer for managing coupled simulations."""

    def __init__(self, parameter_set):
        self.params = parameter_set
        self.electro_thermal = ElectrochemicalThermalDriverModel()
        self.thermal_field = ThermalFieldModel()
        self.mechanics = ThermoelasticStrainModel()

    def run_coupled_simulation(self, solution):
        """Executes the coupled DFN-Thermal-Strain pipeline."""
        # 1. Thermal Field extraction
        thermal_data = self.thermal_field.extract_thermal_data(solution)

        # 2. Thermoelastic Strain evaluation
        mech_res = self.mechanics.solve_strain(
            pybamm_solution=solution,
            params=self.params
        )

        return {
            "thermal_field": thermal_data,
            "mechanics": mech_res,
        }
