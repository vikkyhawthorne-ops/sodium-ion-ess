"""Thermoelastic Strain Model (3D).

Continuum mechanics model implemented in FEniCSx using 3D mesh.
Couples temperature field T(x,t) to mechanical deformation via:
- 3D Thermal expansion
- SOC-driven swelling
- Elastic stress evolution
"""

from dataclasses import dataclass
from typing import Any, Dict
import numpy as np

try:
    import dolfinx
    from dolfinx import fem, mesh, default_scalar_type
    from dolfinx.fem.petsc import LinearProblem
    from mpi4py import MPI
    import ufl
except ImportError:  # pragma: no cover
    dolfinx = None
    ufl = None

from src.simulation.utilities.coupling.pybamm_to_fenics import project_to_fenics

@dataclass
class ThermoelasticStrainModel:
    """Thermoelastic Strain Model."""

    name: str = "Thermoelastic Strain Model"
    critical_thresholds: Dict[str, float] = None

    def __post_init__(self):
        if self.critical_thresholds is None:
            self.critical_thresholds = {"NFPP": 2e-3, "hard_carbon": 1e-3, "SEI": 5e-4}

    def solve_strain(self, pybamm_solution: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Solve for strain using 3D FEniCSx weak form."""
        if dolfinx is None or ufl is None:
            temperature = np.max(pybamm_solution["Cell temperature [K]"].entries)
            cap_ah = pybamm_solution["Discharge capacity [A.h]"].entries[-1]
            nom_cap = params.get("Nominal cell capacity [A.h]", 10.0)
            soc = 1.0 - (cap_ah / nom_cap)
            return {"max_strain": 1e-5 * (temperature - 298.15) + 0.02 * soc, "strain_field": np.array([0])}

        # 1. Create 3D Mesh (representing a pouch cell electrode section)
        # Dimensions in meters: 130mm x 70mm x 100um
        L, W, H = 0.130, 0.070, 1e-4
        domain = mesh.create_box(MPI.COMM_WORLD, [[0, 0, 0], [L, W, H]], [10, 10, 3])
        V = fem.functionspace(domain, ("CG", 1, (3,))) # Vector space for displacement

        # 2. Project PyBaMM variables
        # Scalar space for T and SOC
        Q = fem.functionspace(domain, ("CG", 1))
        T_field = project_to_fenics(pybamm_solution["Cell temperature [K]"], Q)

        cap_ah = pybamm_solution["Discharge capacity [A.h]"].entries[-1]
        nom_cap = params.get("Nominal cell capacity [A.h]", 10.0)
        soc_val = 1.0 - (cap_ah / nom_cap)
        soc_field = fem.Function(Q)
        soc_field.interpolate(lambda x: np.full(x.shape[1], soc_val))

        u = ufl.TrialFunction(V)
        v = ufl.TestFunction(V)

        # 3. Parameters
        E = fem.Constant(domain, default_scalar_type(params.get("Young's modulus", 10e9)))
        nu = fem.Constant(domain, default_scalar_type(0.3))
        alpha = fem.Constant(domain, default_scalar_type(1e-5))
        beta = fem.Constant(domain, default_scalar_type(0.02))
        T_ref = fem.Constant(domain, default_scalar_type(298.15))

        # Lame constants for 3D
        mu = E / (2 * (1 + nu))
        lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))

        def epsilon(u):
            return ufl.sym(ufl.grad(u))

        def sigma(u, T, s):
            eps_inel = (alpha * (T - T_ref) + beta * s) * ufl.Identity(3)
            return lmbda * ufl.tr(epsilon(u) - eps_inel) * ufl.Identity(3) + 2 * mu * (epsilon(u) - eps_inel)

        # 4. Weak Form
        a = ufl.inner(sigma(u, T_field, soc_field), epsilon(v)) * ufl.dx
        L_form = ufl.dot(fem.Constant(domain, default_scalar_type((0, 0, 0))), v) * ufl.dx # No body forces

        # 5. Boundary Conditions (clamped at one end)
        fdim = domain.topology.dim - 1
        boundary_facets = mesh.locate_entities_boundary(domain, fdim, lambda x: np.isclose(x[0], 0))
        bc = fem.dirichletbc(np.zeros(3, dtype=default_scalar_type), fem.locate_dofs_topological(V, fdim, boundary_facets), V)

        # 6. Solve
        problem = LinearProblem(a, L_form, bcs=[bc])
        uh = problem.solve()

        # 7. Extract Strain Intensity (max principal strain or equivalent)
        # For simplicity, we use the trace of the strain tensor as a proxy for volumetric strain intensity
        strain_expr = fem.Expression(ufl.tr(epsilon(uh)), Q.element.interpolation_points())
        strains = fem.Function(Q)
        strains.interpolate(strain_expr)
        max_strain = np.max(np.abs(strains.x.array))

        return {
            "max_strain": float(max_strain),
            "displacement": uh.x.array,
            "strain_field": strains.x.array
        }

    def compute_endurance_metric(self, strain_intensity: float) -> Dict[str, Any]:
        """Compute cycle-time endurance response using fatigue relation: N_f = A * ε^-b"""
        A = 1e6
        b = 2.1
        n_crit = A * (max(strain_intensity, 1e-9)**(-b))
        return {
            "strain_intensity": strain_intensity,
            "n_crit": int(min(n_crit, 1e15)),
            "failure_mode": "fatigue_fracture" if strain_intensity > 1e-3 else "safe",
        }
