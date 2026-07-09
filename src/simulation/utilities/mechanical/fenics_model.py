"""Thermoelastic Strain Model (3D) in FEniCSx.

Solves the thermo-chemo-mechanical PDE:
∇·σ = 0
σ = C : (ε - ε_th - ε_soc)
ε = 0.5 * (∇u + ∇u^T)
ε_th = α(T - T0)
ε_soc = β(SOC - SOC0)
"""

import numpy as np
import pybamm
import traceback
from typing import Any, Dict, Optional
from dataclasses import dataclass
from scipy.interpolate import PchipInterpolator

try:
    import dolfinx
    from dolfinx import fem, mesh, default_scalar_type
    from dolfinx.fem.petsc import LinearProblem
    from mpi4py import MPI
    import ufl
except ImportError:
    dolfinx = None

@dataclass
class ThermoelasticStrainModel:
    critical_thresholds: Dict[str, float] = None

    def __post_init__(self):
        if self.critical_thresholds is None:
            self.critical_thresholds = {"NFPP": 2e-3, "hard_carbon": 1e-3, "SEI": 5e-4}

    def solve_strain(self, pybamm_sol: Any, params: Any, **kwargs) -> Dict[str, Any]:
        """Solves for the displacement and strain field with high-fidelity DFN->FEM mapping."""
        # Note: Rate-dependent scaling removed (Issue 9) as DFN concentration fields
        # already account for rate-induced internal gradients.

        if dolfinx is None:
            # Physics-based proxy for fallback (intercalation strain)
            try:
                T_all = pybamm_sol["Volume-averaged cell temperature [K]"].entries
            except (KeyError, pybamm.ModelError, AttributeError):
                T_all = pybamm_sol["Cell temperature [K]"].entries

            T_max = np.max(T_all)

            # Use particle-level stoichiometry change (Issue 6, 7)
            try:
                sto_p = pybamm_sol["X-averaged positive electrode surface stoichiometry"].entries
                sto_n = pybamm_sol["X-averaged negative electrode surface stoichiometry"].entries
                delta_sto = max(np.max(sto_p) - np.min(sto_p), np.max(sto_n) - np.min(sto_n))
            except (KeyError, pybamm.ModelError, AttributeError):
                cap_ah = pybamm_sol["Discharge capacity [A.h]"].entries
                nom_cap = params["Nominal cell capacity [A.h]"]
                soc_all = 1.0 - (cap_ah / nom_cap)
                delta_sto = np.max(soc_all) - np.min(soc_all)

            strain = (1e-5 * (T_max - 298.15) + 0.02 * delta_sto)
            return {"max_strain": float(strain)}

        # Electrode dimensions (Pouch section) from paper.md and cell_alpha.py
        L = params.get("Electrode height [m]", 0.130)
        W = params.get("Electrode width [m]", 0.070)
        H_p = params.get("Positive electrode thickness [m]", 100e-6)
        H_n = params.get("Negative electrode thickness [m]", 120e-6)
        H_s = params.get("Separator thickness [m]", 25e-6)
        H = H_n + H_s + H_p # Total stack height for mechanical PDE

        domain = mesh.create_box(MPI.COMM_WORLD, [[0, 0, 0], [L, W, H]], [10, 10, 5])
        V = fem.functionspace(domain, ("CG", 1, (3,)))
        u = ufl.TrialFunction(V)
        v = ufl.TestFunction(V)

        # Map DFN fields (T(x), c_s(x)) to FEniCS 3D mesh
        Q = fem.functionspace(domain, ("CG", 1))

        try:
             # Use actual PyBaMM spatial nodes (Issue 1, 2)
             x_dfn = pybamm_sol["x [m]"].entries[:, 0]
             T_spatial = pybamm_sol["Cell temperature [K]"].entries[:, -1]
             # PchipInterpolator for smoothness and monotonicity (Issue 3, 4)
             T_interp_obj = PchipInterpolator(x_dfn, T_spatial)
             T_interp = lambda x: T_interp_obj(x[2])

             # Stoichiometry nodes
             x_n = pybamm_sol["x_n [m]"].entries[:, 0]
             x_p = pybamm_sol["x_p [m]"].entries[:, 0]
             sto_n_spatial = pybamm_sol["Negative electrode surface stoichiometry"].entries[:, -1]
             sto_p_spatial = pybamm_sol["Positive electrode surface stoichiometry"].entries[:, -1]

             sto_n_interp = PchipInterpolator(x_n, sto_n_spatial)
             sto_p_interp = PchipInterpolator(x_p, sto_p_spatial)

             def stoichiometry_mapping(x):
                  val = np.zeros(x.shape[1])
                  # Domain-aware mapping (Issue 6)
                  mask_n = x[2] <= H_n
                  mask_p = x[2] >= (H_n + H_s)
                  val[mask_n] = sto_n_interp(x[2, mask_n])
                  val[mask_p] = sto_p_interp(x[2, mask_p])
                  return val

        except (KeyError, pybamm.ModelError, AttributeError):
             # Robust fallback
             T_max = np.max(pybamm_sol["Cell temperature [K]"].entries)
             cap_ah = pybamm_sol["Discharge capacity [A.h]"].entries
             soc_final = 1.0 - (cap_ah[-1] / params["Nominal cell capacity [A.h]"])
             T_interp = lambda x: np.full(x.shape[1], T_max)
             stoichiometry_mapping = lambda x: np.full(x.shape[1], soc_final)

        T_field = fem.Function(Q)
        T_field.interpolate(T_interp)
        s_field = fem.Function(Q)
        s_field.interpolate(stoichiometry_mapping)

        # Piecewise Material Properties (Issue 6, 7)
        # 0: Anode, 1: Separator, 2: Cathode
        x3 = ufl.SpatialCoordinate(domain)[2]
        domain_cond = ufl.conditional(x3 <= H_n, 0, ufl.conditional(x3 <= H_n + H_s, 1, 2))

        E_n = params.get("Negative electrode Young's modulus [Pa]", 10e9)
        E_p = params.get("Positive electrode Young's modulus [Pa]", 10e9)
        E_s = 0.5e9 # Typical polymer separator
        E = ufl.conditional(ufl.eq(domain_cond, 0), E_n, ufl.conditional(ufl.eq(domain_cond, 1), E_s, E_p))

        nu = ufl.conditional(ufl.eq(domain_cond, 1), 0.4, 0.3)
        alpha = ufl.conditional(ufl.eq(domain_cond, 1), 1e-4, 1e-5) # Separator expands more
        beta_n = 0.02
        beta_p = 0.01
        beta = ufl.conditional(ufl.eq(domain_cond, 0), beta_n, ufl.conditional(ufl.eq(domain_cond, 2), beta_p, 0.0))

        T_ref = fem.Constant(domain, default_scalar_type(298.15))
        mu = E / (2 * (1 + nu))
        lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))

        def epsilon(u):
            return ufl.sym(ufl.grad(u))

        def sigma(u, T, s):
            eps_inel = (alpha * (T - T_ref) + beta * s) * ufl.Identity(3)
            return lmbda * ufl.tr(epsilon(u) - eps_inel) * ufl.Identity(3) + 2 * mu * (epsilon(u) - eps_inel)

        a = ufl.inner(sigma(u, T_field, s_field), epsilon(v)) * ufl.dx
        L_form = ufl.dot(fem.Constant(domain, default_scalar_type((0, 0, 0))), v) * ufl.dx

        # BC: Fixed at one face
        fdim = domain.topology.dim - 1
        boundary_facets = mesh.locate_entities_boundary(domain, fdim, lambda x: np.isclose(x[0], 0))
        bc = fem.dirichletbc(np.zeros(3, dtype=default_scalar_type), fem.locate_dofs_topological(V, fdim, boundary_facets), V)

        problem = LinearProblem(a, L_form, bcs=[bc])
        uh = problem.solve()

        # Extract Von Mises metrics (Issue 9)
        eps_val = epsilon(uh)
        # Deviatoric strain
        eps_dev = eps_val - (1/3) * ufl.tr(eps_val) * ufl.Identity(3)
        eps_vm_expr = ufl.sqrt(ufl.inner(eps_dev, eps_dev) * (2/3))

        sig_val = sigma(uh, T_field, s_field)
        sig_dev = sig_val - (1/3) * ufl.tr(sig_val) * ufl.Identity(3)
        sig_vm_expr = ufl.sqrt(ufl.inner(sig_dev, sig_dev) * (3/2))

        eps_vm = fem.Function(Q)
        eps_vm.interpolate(fem.Expression(eps_vm_expr, Q.element.interpolation_points()))

        sig_vm = fem.Function(Q)
        sig_vm.interpolate(fem.Expression(sig_vm_expr, Q.element.interpolation_points()))

        return {
            "max_strain": float(np.max(eps_vm.x.array)),
            "max_stress": float(np.max(sig_vm.x.array))
        }

    def compute_endurance_metric(self, max_strain: float) -> Dict[str, float]:
        """
        Estimates cycle life (N_crit) using Coffin-Manson relationship.
        """
        # ε_p = ε_f' * (2N)^c -> N = 0.5 * (ε_p / ε_f')^(1/c)
        # For typical battery materials: ε_f' ~ 0.1, c ~ -0.5
        eps_f = 0.1
        c = -0.5
        n_crit = 0.5 * (max_strain / eps_f) ** (1/c) if max_strain > 0 else 1e12
        return {"n_crit": float(n_crit)}
