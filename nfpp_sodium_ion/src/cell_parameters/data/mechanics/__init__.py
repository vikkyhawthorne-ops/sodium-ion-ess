from dataclasses import dataclass
from typing import Any
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters

@dataclass
class ElasticModuliSpace:
    """Elastic moduli parameters as FEniCSx-compatible fields."""

    @property
    def youngs_modulus_pa(self) -> float:
        return get_derived_parameters()["youngs_modulus_p"]

    @property
    def poisson_ratio(self) -> float:
        return get_derived_parameters()["poisson_ratio_p"]

    def get_lame_parameters(self) -> tuple:
        """Compute Lamé parameters.

        Returns:
            (lambda, mu) for use in elasticity problems
        """
        derived = get_derived_parameters()
        E = self.youngs_modulus_pa
        nu = self.poisson_ratio
        lam = E * nu / ((1 + nu) * (1 - 2 * nu))
        mu = E / (2 * (1 + nu))
        return lam, mu


@dataclass
class ThermalExpansionSpace:
    """Thermal expansion coefficient as FEniCSx expression.

    Provides temperature-dependent thermal strain for coupling to
    mechanical problem in form compatible with ufl definitions.
    """

    @property
    def alpha_ref(self) -> float:
        return get_derived_parameters()["alpha_thermal"]

    @property
    def reference_temperature_k(self) -> float:
        return get_derived_parameters()["t_ref"]

    def thermal_strain(self, temperature_field: Any) -> Any:
        """Compute thermal strain from temperature field.

        Args:
            temperature_field: ufl/dolfinx function or scalar

        Returns:
            Thermal strain suitable for use in elasticity equations
        """
        return self.alpha_ref * (temperature_field - self.reference_temperature_k)


@dataclass
class SwellingCoefficientSpace:
    """SOC-driven swelling as FEniCSx-compatible field.

    Swelling from insertion/deinsertion couples to mechanical problem.
    """

    @property
    def swelling_coefficient(self) -> float:
        return get_derived_parameters()["beta_p"]

    def swelling_strain(self, soc_field: Any) -> Any:
        """Compute swelling strain from SOC field.

        Args:
            soc_field: State of charge [0,1] as ufl/dolfinx function

        Returns:
            Swelling-induced strain
        """
        return self.swelling_coefficient * soc_field
