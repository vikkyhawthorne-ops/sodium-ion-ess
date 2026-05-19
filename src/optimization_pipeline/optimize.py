import numpy as np
from scipy.optimize import minimize
import pybamm
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

class NFPPoptimizer:
    """
    NFPP Cell Optimization Pipeline.
    Implements a two-step optimization:
    1. Electrolyte Optimization (Cost)
    2. Hessian-based Design Space Reduction and Optimal Solution Identification
    Ref: docs/paper.md
    """

    def __init__(self):
        self.base_params = get_parameter_values()
        # Define the full design space theta
        # theta = [L_c, L_a, eps_c, eps_a, r_p, sigma_c, sigma_a, R_contact]
        self.theta_names = [
            "Positive electrode thickness [m]",
            "Negative electrode thickness [m]",
            "Positive electrode porosity",
            "Negative electrode porosity",
            "Positive particle radius [m]",
            "Positive electrode conductivity [S.m-1]",
            "Negative electrode conductivity [S.m-1]",
            "Contact resistance [Ohm]"
        ]
        self.theta_initial = np.array([
            0.0001, 0.00012, 0.3, 0.3, 1e-6, 50.0, 256.0, 0.001
        ])
        self.bounds = [
            (5e-5, 2e-4), (5e-5, 2e-4), (0.1, 0.4), (0.1, 0.4),
            (1e-7, 1e-5), (10, 100), (100, 500), (0, 0.01)
        ]

    def step1_electrolyte_optimization(self):
        """
        Step 1: Electrolyte optimization (main cost optimization).
        Minimizes cost based on salt and additive concentrations.
        """
        print("Running Step 1: Electrolyte Optimization...")
        def electrolyte_cost(x):
            napf6, nadfob, fec, vc = x
            return 10*napf6 + 25*nadfob + 15*fec + 20*vc

        initial_electrolyte = [1.0, 0.2, 3.0, 2.0]
        bounds = [(0.8, 1.2), (0.1, 0.5), (1.0, 5.0), (1.0, 4.0)]
        res = minimize(electrolyte_cost, initial_electrolyte, bounds=bounds)
        print(f"Optimal Electrolyte Composition: {res.x}")
        return res.x

    def approximate_hessian(self, func, x, epsilon=1e-3):
        """
        Approximates the Hessian matrix of func at x using finite differences.
        """
        n = len(x)
        hessian = np.zeros((n, n))
        f_x = func(x)

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    x_plus = np.array(x, copy=True)
                    x_plus[i] += epsilon
                    x_minus = np.array(x, copy=True)
                    x_minus[i] -= epsilon
                    hessian[i, i] = (func(x_plus) - 2*f_x + func(x_minus)) / (epsilon**2)
                else:
                    x_pp = np.array(x, copy=True); x_pp[i] += epsilon; x_pp[j] += epsilon
                    x_pm = np.array(x, copy=True); x_pp[i] += epsilon; x_pp[j] -= epsilon
                    x_mp = np.array(x, copy=True); x_pp[i] -= epsilon; x_pp[j] += epsilon
                    x_mm = np.array(x, copy=True); x_pp[i] -= epsilon; x_pp[j] -= epsilon
                    hessian[i, j] = (func(x_pp) - func(x_pm) - func(x_mp) + func(x_mm)) / (4 * epsilon**2)
                    hessian[j, i] = hessian[i, j]
        return hessian

    def step2_design_optimization(self):
        """
        Step 2: Optimal design parameters using Hessian matrix optimization.
        Includes Curvature-based elimination of weak or non-influential directions.
        """
        print("Running Step 2: Hessian-based Design Space Reduction...")

        def performance_landscape(theta):
            # Surrogate for Energy Density and Efficiency
            L_c, L_a, eps_c, eps_a, r_p, s_c, s_a, r_con = theta
            energy = (L_c * (1-eps_c)) * 500
            loss = (r_p**2 / 1e-12) + (r_con / 0.001)
            return -(energy - 0.1 * loss) # Minimize negative performance

        # 1. Compute Curvature at initial point
        H = self.approximate_hessian(performance_landscape, self.theta_initial)

        # 2. Identify non-influential parameters (Low diagonal values in Hessian)
        diag_h = np.abs(np.diag(H))
        threshold = 0.1 * np.mean(diag_h)
        active_indices = np.where(diag_h > threshold)[0]

        print(f"Design Space Reduction: {len(active_indices)}/{len(self.theta_initial)} influential parameters identified.")
        print(f"Active Parameters: {[self.theta_names[i] for i in active_indices]}")

        # 3. Optimize only over active indices
        def reduced_objective(x_reduced):
            theta = np.array(self.theta_initial, copy=True)
            theta[active_indices] = x_reduced
            return performance_landscape(theta)

        initial_reduced = self.theta_initial[active_indices]
        bounds_reduced = [self.bounds[i] for i in active_indices]

        # Constraints: N/P ratio >= 1.05 (if L_c, L_a, eps_c, eps_a are active)
        def np_ratio_con(x_reduced):
            theta = np.array(self.theta_initial, copy=True)
            theta[active_indices] = x_reduced
            L_c, L_a, eps_c, eps_a = theta[0], theta[1], theta[2], theta[3]
            return L_a*(1-eps_a)/(L_c*(1-eps_c)) - 1.05

        cons = ({'type': 'ineq', 'fun': np_ratio_con})

        res = minimize(reduced_objective, initial_reduced, bounds=bounds_reduced, constraints=cons)

        optimal_theta = np.array(self.theta_initial, copy=True)
        optimal_theta[active_indices] = res.x

        print(f"Optimal Design Solution Identified: {optimal_theta}")
        return optimal_theta

    def run_optimization(self):
        opt_electrolyte = self.step1_electrolyte_optimization()
        opt_design = self.step2_design_optimization()
        return {"electrolyte": opt_electrolyte, "design": opt_design}

if __name__ == "__main__":
    optimizer = NFPPoptimizer()
    optimizer.run_optimization()
