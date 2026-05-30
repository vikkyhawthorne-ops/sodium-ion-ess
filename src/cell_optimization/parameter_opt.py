import numpy as np
import pybamm
import casadi
import math
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values
from src.cell_optimization.material_opt import MaterialMappingEngine

try:
    import dolfinx
    from dolfinx import fem, mesh, default_scalar_type
    from dolfinx.fem.petsc import LinearProblem
    from mpi4py import MPI
    import ufl
    import petsc4py.PETSc as PETSc
except ImportError:
    dolfinx = None

class DSMOptimizer:
    """
    Two-Timescale Differentiable Sensitivity Manifold Optimizer (DSMO).
    Outer loop: Categorical Material Selection.
    Inner loop: Continuous Structural Parameter Optimization.
    """
    def __init__(self, target_y=None):
        self.target_y = target_y if target_y is not None else np.array([3.3, 298.15, 0.5, 1e-8])
        self.y_scale = np.array([3.5, 300.0, 1.0, 1e-6])

        self.engine = MaterialMappingEngine()
        self.material_data = None
        self.selected_dopant_idx = 0
        self.selected_salt_idx = 0
        self.mtms_enabled = 1.0

        self.lr = 0.05
        self.max_epochs = 3
        self.inner_iters = 4
        self.lam = 1e-3

        self.symbolic_keys = [
            "Positive electrode porosity",
            "Negative electrode porosity",
            "Separator porosity",
            "Bruggeman coefficient (electrolyte)",
            "Positive electrode active material volume fraction",
            "Negative electrode active material volume fraction",
            "Typical electrolyte concentration [mol.m-3]"
        ]
        self.numeric_keys = [
            "Positive electrode thickness [m]",
            "Negative electrode thickness [m]",
            "Positive particle radius [m]"
        ]

        self.structural_keys = self.numeric_keys + self.symbolic_keys
        self.theta_structural = np.array([1.2e-4, 1.2e-4, 1e-6, 0.3, 0.3, 0.5, 1.5, 0.65, 0.65, 1000.0])

    def apply_material_logic(self, param_vals):
        """Applies frozen material deltas for the current epoch."""
        dopants = self.material_data.get("Cathode_Dopant", [])
        salts = self.material_data.get("Salt", [])
        func = self.material_data.get("Functionalization", [])

        d_delta = dopants[self.selected_dopant_idx].to_pybamm_delta() if dopants else {}
        s_delta = salts[self.selected_salt_idx].to_pybamm_delta() if salts else {}
        f_delta = func[0].to_pybamm_delta() if func else {}

        def apply_p(delta_map, alpha=1.0):
            for name, (mode, val) in delta_map.items():
                base = param_vals[name]
                m = np.clip(1.0 + alpha * (val - 1.0), 0.2, 5.0) if mode == "multiplier" else 1.0
                a = np.clip(alpha * val, -0.5, 0.5) if mode == "additive" else 0.0

                if callable(base):
                    def make_wrapper(b, m_val, a_val):
                        return lambda *args, **kwargs: b(*args, **kwargs) * m_val + a_val
                    param_vals[name] = make_wrapper(base, m, a)
                else:
                    param_vals[name] = base * m + a

        apply_p(d_delta)
        apply_p(s_delta)
        apply_p(f_delta, alpha=self.mtms_enabled)
        return param_vals

    def setup_sim(self, theta_s, symbolic_keys=None):
        param_vals = pybamm.ParameterValues(get_parameter_values())
        for i, key in enumerate(self.structural_keys):
            if symbolic_keys and key in symbolic_keys:
                param_vals[key] = pybamm.InputParameter(key)
            else:
                param_vals[key] = theta_s[i]

        param_vals = self.apply_material_logic(param_vals)
        param_vals["Current function [A]"] = 10.0

        model = pybamm.lithium_ion.DFN()
        solver = pybamm.CasadiSolver(mode="fast")
        sim = pybamm.Simulation(model, parameter_values=param_vals, solver=solver)
        return sim

    def run(self):
        print(f"Starting Robust Decoupled DSMO Optimization...")
        theta_s = self.theta_structural

        for epoch in range(self.max_epochs):
            print(f"Epoch {epoch}: Material Resolution...")
            self.material_data = self.engine.run()

            # Outer Loop: Categorical Choice
            best_res = 1e9
            for di in range(len(self.material_data.get("Cathode_Dopant", [0]))):
                for si in range(len(self.material_data.get("Salt", [0]))):
                    self.selected_dopant_idx = di
                    self.selected_salt_idx = si
                    sim = self.setup_sim(theta_s)
                    try:
                        sol = sim.solve([0, 1800])
                        v = float(sol["Terminal voltage [V]"].entries[-1])
                        r_norm = abs(v - self.target_y[0])
                        if r_norm < best_res:
                            best_res = r_norm
                            self.selected_dopant_idx, self.selected_salt_idx = di, si
                    except: continue

            # Inner Loop: Continuous Gradient Descent
            for k in range(self.inner_iters):
                sim = self.setup_sim(theta_s, symbolic_keys=self.symbolic_keys)
                p_dict = {key: theta_s[i + len(self.numeric_keys)] for i, key in enumerate(self.symbolic_keys)}
                sol = sim.solve([0, 1800], inputs=p_dict)

                V_val = float(np.array(sol["Terminal voltage [V]"].entries).flatten()[-1])
                T_val = float(np.array(sol["Cell temperature [K]"].entries).flatten()[-1])
                Q_nom = float(sim.parameter_values["Nominal cell capacity [A.h]"])
                SOC_val = 1.0 - (float(np.array(sol["Discharge capacity [A.h]"].entries).flatten()[-1]) / Q_nom)

                # Consistent coupling: Pass actual numeric values of theta_s for mechanical check
                eps_val, S_mech_row = self.solve_mechanical_adjoint(T_val, SOC_val, theta_s)
                y = np.array([V_val, T_val, SOC_val, eps_val])

                # Standardize on Adaptive FD for entire Jacobian
                S = self._compute_structural_jacobian(theta_s)
                S = np.vstack([S, S_mech_row])

                # Normalization
                S = S / self.y_scale[:, None]
                for j in range(S.shape[1]):
                    S[:, j] /= (np.linalg.norm(S[:, j]) + 1e-12)

                r = (y - self.target_y) / self.y_scale

                # Regularized Update
                scale = np.linalg.norm(S, ord=2)
                G = S.T @ S + (self.lam + 1e-3 * scale**2) * np.eye(len(theta_s))
                update = np.linalg.solve(G, S.T @ r)
                theta_s = theta_s - self.lr * update

                # Bounds
                theta_s = np.clip(theta_s,
                                  [5e-5, 5e-5, 1e-7, 0.1, 0.1, 0.2, 1.0, 0.4, 0.4, 500.0],
                                  [3e-4, 3e-4, 1e-5, 0.6, 0.6, 0.8, 3.0, 0.8, 0.8, 2000.0])

                print(f"  Iteration {epoch}.{k}: Residual Norm = {np.linalg.norm(r):.4f}")

        self.theta_structural = theta_s
        dopants = self.material_data.get("Cathode_Dopant", [])
        salts = self.material_data.get("Salt", [])

        return {
            "structural_design": theta_s.tolist(),
            "selected_dopant": dopants[self.selected_dopant_idx].name if dopants else "None",
            "selected_salt": salts[self.selected_salt_idx].name if salts else "None",
            "mtms_applied": "Yes" if self.mtms_enabled > 0.5 else "No"
        }

    def _compute_structural_jacobian(self, theta_s):
        S = np.zeros((3, len(theta_s)))
        for i in range(len(theta_s)):
            # Adaptive step
            eps = 1.5e-8 * (1.0 + abs(theta_s[i]))

            def get_y(th):
                s = self.setup_sim(th)
                sol = s.solve([0, 1800])
                v = float(sol["Terminal voltage [V]"].entries[-1])
                t = float(sol["Cell temperature [K]"].entries[-1])
                q = float(s.parameter_values["Nominal cell capacity [A.h]"])
                soc = 1.0 - (float(sol["Discharge capacity [A.h]"].entries[-1]) / q)
                return np.array([v, t, soc])

            try:
                pert = np.zeros(len(theta_s)); pert[i] = eps
                y_p = get_y(theta_s + pert)
                y_m = get_y(theta_s - pert)
                S[:, i] = (y_p - y_m) / (2 * eps)
            except: S[:, i] = 0
        return S

    def solve_mechanical_adjoint(self, T, SOC, theta_s):
        # theta_s[0]: pos thick, theta_s[1]: neg thick, theta_s[3]: pos porosity
        L_p, L_a = theta_s[0], theta_s[1]
        L_tot_val = L_p + L_a + 20e-6
        eps_ref = 1e-6

        # Physical Material-Dependent alpha
        eps_alpha = 1e-7 / (1.0 + theta_s[3])

        if not dolfinx:
            eps = eps_alpha * (T - 298.15) + 1e-6 * (0.5 - SOC)
            deps_dL = (1e-6 / L_tot_val)
            S_mech = np.zeros(len(theta_s))
            S_mech[0] = S_mech[1] = (deps_dL / L_tot_val) / eps_ref
            return (eps / eps_ref), S_mech

        domain = mesh.create_interval(MPI.COMM_WORLD, 20, [0, 1])
        V = fem.functionspace(domain, ("Lagrange", 1))
        L_var = fem.Constant(domain, default_scalar_type(L_tot_val))
        L_ufl = ufl.variable(L_var)
        E = fem.Constant(domain, default_scalar_type(10e9))
        alpha_fem = fem.Constant(domain, default_scalar_type(eps_alpha))
        beta = fem.Constant(domain, default_scalar_type(0.02))
        eps_0 = alpha_fem * (T - 298.15) + beta * (SOC - 0.5)
        u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
        F = (1.0/L_ufl) * E * (u.dx(0) - L_ufl*eps_0) * v.dx(0) * ufl.dx
        a, L_form = ufl.lhs(F), ufl.rhs(F)
        dofs_left = fem.locate_dofs_geometrical(V, lambda x: np.isclose(x[0], 0))
        bc = fem.dirichletbc(default_scalar_type(0), dofs_left, V)
        uh = LinearProblem(a, L_form, bcs=[bc]).solve()
        strain_val = uh.x.array[-1] / L_tot_val
        K_mat = fem.petsc.assemble_matrix(fem.form(a), bcs=[bc])
        K_mat.assemble()
        R_uh = ufl.replace(F, {u: uh})
        dR_dL = ufl.diff(R_uh, L_ufl)
        rhs_sens = fem.petsc.assemble_vector(fem.form(-dR_dL))
        fem.petsc.apply_lifting(rhs_sens, [fem.form(a)], bcs=[[bc]])
        rhs_sens.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
        fem.petsc.set_bc(rhs_sens, [bc])
        du_dL = fem.Function(V)
        ksp = PETSc.KSP().create(domain.comm)
        ksp.setOperators(K_mat)
        ksp.solve(rhs_sens, du_dL.vector)
        dstrain_dL = (1.0/L_tot_val) * du_dL.x.array[-1] - (uh.x.array[-1] / (L_tot_val**2))
        S_mech = np.zeros(len(theta_s))
        S_mech[0] = S_mech[1] = (dstrain_dL / L_tot_val) / eps_ref
        return (float(strain_val) / eps_ref), S_mech

if __name__ == "__main__":
    opt = DSMOptimizer()
    res = opt.run()
    print(res)
