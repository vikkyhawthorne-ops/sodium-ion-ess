import numpy as np
import pybamm
import casadi
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

try:
    import dolfinx
    from mpi4py import MPI
    import ufl
    from dolfinx import fem, mesh
except ImportError:
    dolfinx = None

class DSMOptimizer:
    """
    Differentiable Sensitivity Manifold Optimizer (DSMO).
    Expanded Design Space:
    - Structural θₛ: [L_p, L_n, eps_p, eps_n, r_p, bruggeman]
    - Material θₘ: [active_p, active_n, carbon_p, electrolyte_conc]
    """
    def __init__(self, target_y=None, material_deltas=None):
        self.target_y = target_y if target_y is not None else np.array([3.1, 305.0, 0.5, 1e-6])
        self.deltas = material_deltas or {}

        self.lr = 0.05
        self.max_iters = 5
        self.lam = 1e-3

        # Expanded Design Space Keys
        self.theta_keys = [
            "Positive electrode thickness [m]",         # L_p
            "Negative electrode thickness [m]",         # L_n
            "Positive electrode porosity",              # eps_p
            "Negative electrode porosity",              # eps_n
            "Positive particle radius [m]",             # r_p
            "Bruggeman coefficient (electrolyte)",      # tortuosity proxy
            "Positive electrode active material volume fraction", # loading proxy
            "Negative electrode active material volume fraction",
            "Typical electrolyte concentration [mol.m-3]" # composition proxy
        ]

        # Initial guess (Aligned with NFPP base)
        self.theta = np.array([1.2e-4, 1.2e-4, 0.3, 0.3, 1e-6, 1.5, 0.65, 0.65, 1000.0])

    def setup_multiphysics(self):
        param_vals = pybamm.ParameterValues(get_parameter_values())

        # Apply Material deltas from discovery stage
        if "diffusivity" in self.deltas:
            param_vals["Negative particle diffusivity [m2.s-1]"] *= self.deltas["diffusivity"]

        model = pybamm.lithium_ion.DFN()
        inputs = {v: pybamm.InputParameter(v) for v in self.theta_keys}
        param_vals.update(inputs, check_already_exists=False)

        self.solver = pybamm.CasadiSolver(mode="fast", return_solution_as_casadi=True)
        self.sim = pybamm.Simulation(model, parameter_values=param_vals, solver=self.solver)

    def solve_mechanical_adjoint(self, T, SOC):
        if dolfinx:
            return 1e-6, np.zeros(len(self.theta_keys))
        else:
            eps = 1e-7 * (T - 298.15) + 1e-6 * (0.5 - SOC)
            deps_dtheta = np.zeros(len(self.theta_keys))
            deps_dtheta[0] = 1e-3 # Dummy gradient wrt L_p
            return eps, deps_dtheta

    def run(self):
        print(f"Starting DSMO on {len(self.theta_keys)} parameters...")
        self.setup_multiphysics()

        theta_vec = self.theta
        for k in range(self.max_iters):
            p_dict = {self.theta_keys[i]: theta_vec[i] for i in range(len(self.theta_keys))}
            sol = self.sim.solve([0, 1800], inputs=p_dict)

            V = float(sol["Terminal voltage [V]"].entries[-1])
            T = float(sol["Cell temperature [K]"].entries[-1])
            SOC = 1.0 - (float(sol["Discharge capacity [A.h]"].entries[-1]) / 10.0)

            eps, S_mech_row = self.solve_mechanical_adjoint(T, SOC)
            y = np.array([V, T, SOC, eps])

            # Sensitivity Matrix Assembly (4 states x 9 parameters)
            try:
                S_pybamm = np.zeros((3, len(self.theta_keys)))
                for i, key in enumerate(self.theta_keys):
                    S_pybamm[0, i] = sol["Terminal voltage [V]"].sensitivities[key][-1]
                    S_pybamm[1, i] = sol["Cell temperature [K]"].sensitivities[key][-1]
                    S_pybamm[2, i] = -sol["Discharge capacity [A.h]"].sensitivities[key][-1] / 10.0
            except:
                S_pybamm = self.finite_difference_jac(theta_vec)

            S = np.vstack([S_pybamm, S_mech_row])

            # Gauss-Newton Update
            r = y - self.target_y
            G = S.T @ S + self.lam * np.eye(len(self.theta_keys))
            update = np.linalg.solve(G, S.T @ r)
            theta_vec = theta_vec - self.lr * update

            # Physical Clipping
            theta_vec = np.clip(theta_vec,
                [5e-5, 5e-5, 0.1, 0.1, 1e-7, 1.0, 0.4, 0.4, 500.0],
                [3e-4, 3e-4, 0.6, 0.6, 1e-5, 3.0, 0.8, 0.8, 2000.0])

            print(f"  Iteration {k}: Residual Norm = {np.linalg.norm(r):.4f}")
            if np.linalg.norm(r) < 1e-4: break

        return {"design": theta_vec.tolist()}

    def finite_difference_jac(self, theta):
        n_params = len(self.theta_keys)
        S = np.zeros((3, n_params))
        eps = 1e-6
        for i in range(n_params):
            th_p = theta.copy(); th_p[i] += eps
            p_p = {self.theta_keys[j]: th_p[j] for j in range(n_params)}
            sol_p = self.sim.solve([0, 1800], inputs=p_p)
            v_p = float(sol_p["Terminal voltage [V]"].entries[-1])
            t_p = float(sol_p["Cell temperature [K]"].entries[-1])
            soc_p = 1.0 - (float(sol_p["Discharge capacity [A.h]"].entries[-1]) / 10.0)

            th_m = theta.copy(); th_m[i] -= eps
            p_m = {self.theta_keys[j]: th_m[j] for j in range(n_params)}
            sol_m = self.sim.solve([0, 1800], inputs=p_m)
            v_m = float(sol_m["Terminal voltage [V]"].entries[-1])
            t_m = float(sol_m["Cell temperature [K]"].entries[-1])
            soc_m = 1.0 - (float(sol_m["Discharge capacity [A.h]"].entries[-1]) / 10.0)

            S[0, i] = (v_p - v_m) / (2 * eps)
            S[1, i] = (t_p - t_m) / (2 * eps)
            S[2, i] = (soc_p - soc_m) / (2 * eps)
        return S
