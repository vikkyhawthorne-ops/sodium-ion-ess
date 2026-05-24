"""Thermal Field Model.

Heat transport model implementing:
- Spatial-temporal temperature field T(x,t) for resolved analysis
- Lumped temperature T(t) for reduced-order analysis
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ThermalFieldModel:
    """Thermal Field Model for heat transport.

    A wrapper around PyBaMM outputs to extract thermal information.
    """

    name: str = "Thermal Field Model"

    def extract_thermal_data(self, solution: Any) -> Dict[str, Any]:
        """Extract thermal data from PyBaMM solution.

        Args:
            solution: PyBaMM solution object

        Returns:
            Dictionary containing temperature and heat generation
        """
        return {
            "temperature": solution["Cell temperature [K]"].entries,
            "heat_generation": solution["Total heating [W.m-3]"].entries,
            "ohmic_heating": solution["Ohmic heating [W.m-3]"].entries,
            "irreversible_electrochemical_heating": solution["Irreversible electrochemical heating [W.m-3]"].entries,
            "reversible_heating": solution["Reversible heating [W.m-3]"].entries,
        }

    def get_spatial_temperature(self, solution: Any) -> Any:
        """Extract spatially resolved temperature if available.

        Args:
            solution: PyBaMM solution object
        """
        return solution["Cell temperature [K]"]
