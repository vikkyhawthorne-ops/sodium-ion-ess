import numpy as np
from scipy.optimize import minimize
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Generator, Dict, Any, Optional, Iterable
import scipy.linalg
import time

class PipelineStatus(Enum):
    INIT = "INIT"
    CALIBRATING = "CALIBRATING"
    STREAMING = "STREAMING"
    REDUCING = "REDUCING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

@dataclass
class PipelineState:
    job_id: str
    status: PipelineStatus = PipelineStatus.INIT
    progress: float = 0.0
    processed_count: int = 0
    retained_count: int = 0

@dataclass
class MaterialCandidate:
    id: str
    features: np.ndarray  # d-dimensional
    V_redox: float
    D_Na: float
    C_adj: float
    S_T: float
    S_grid: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class ThermalModel:
    """
    Discretized thermal model:
    T_{t+1} = T_t + Δt * (Q*/C_th - (T_t - T_amb)/(R_th * C_th))
    """
    def __init__(self):
        self.R_th = 1.5
        self.C_th = 500.0
        self.calibrated = False

    def calibrate(self, t_obs, q_star, t_amb, dt=1.0):
        def objective(params):
            R, C = params
            if R <= 1e-3 or C <= 1e-3: return 1e18
            t_pred = [t_obs[0]]
            for i in range(len(t_obs)-1):
                next_t = t_pred[-1] + dt * (q_star[i]/C - (t_pred[-1] - t_amb[i])/(R*C))
                t_pred.append(next_t)
            return np.sum((np.array(t_pred) - t_obs)**2)

        res = minimize(objective, [self.R_th, self.C_th], method='L-BFGS-B', bounds=[(1e-2, 1e4), (1e1, 1e6)])
        if res.success:
            self.R_th, self.C_th = res.x
            self.calibrated = True
        return res.success

class DPPReductor:
    """
    Online DPP Reduction: Reservoir + Greedy DPP Approximation
    """
    def __init__(self, k=1000, sigma=1.0, epsilon=1e-4):
        self.k = k
        self.sigma = sigma
        self.epsilon = epsilon
        self.reservoir: List[MaterialCandidate] = []
        self.L = None # Cholesky L factor of K

    def _kernel(self, x, y):
        return np.exp(-np.linalg.norm(x - y)**2 / (2 * self.sigma**2))

    def _normalize(self, x):
        norm = np.linalg.norm(x)
        return x / (norm + 1e-12)

    def update(self, m: MaterialCandidate) -> bool:
        x = self._normalize(m.features)

        if len(self.reservoir) < self.k:
            # Initial filling of reservoir
            if len(self.reservoir) == 0:
                self.reservoir.append(m)
                self.L = np.array([[np.sqrt(1.0 + self.epsilon)]])
            else:
                X_res = np.array([self._normalize(r.features) for r in self.reservoir])
                k_vec = np.array([self._kernel(x, rx) for rx in X_res])
                # Solve L * v = k_vec
                v = scipy.linalg.solve_triangular(self.L, k_vec, lower=True)
                s2 = 1.0 + self.epsilon - np.dot(v, v)
                if s2 > 0:
                    s = np.sqrt(s2)
                    new_L = np.zeros((len(self.reservoir) + 1, len(self.reservoir) + 1))
                    new_L[:-1, :-1] = self.L
                    new_L[-1, :-1] = v
                    new_L[-1, -1] = s
                    self.L = new_L
                    self.reservoir.append(m)
                else:
                    # Too similar, don't add
                    return False
            return True

        # Reservoir is full, use Greedy DPP Replacement
        X_res = np.array([self._normalize(r.features) for r in self.reservoir])
        k_vec = np.array([self._kernel(x, rx) for rx in X_res])

        try:
            v = scipy.linalg.solve_triangular(self.L, k_vec, lower=True)
            gain_val = (1.0 + self.epsilon) - np.dot(v, v)

            if gain_val > self.epsilon:
                # Approximate contribution of each reservoir element
                # Using the inverse diagonal of K = L L^T
                # K^-1 = (L^-T) (L^-1)
                Linv = scipy.linalg.solve_triangular(self.L, np.eye(self.k), lower=True)
                Kinv_diag = np.sum(Linv**2, axis=0) # This is actually diag(K^-1) if we sum rows of Linv^T which is cols of Linv

                # Contribution is 1 / Kinv_diag[i]
                contributions = 1.0 / (Kinv_diag + 1e-12)
                idx_to_replace = np.argmin(contributions)

                if gain_val > contributions[idx_to_replace]:
                    self.reservoir[idx_to_replace] = m
                    # Rebuild for stability in replacement
                    self._rebuild_cholesky()
                    return True
        except Exception:
            pass

        return False

    def _rebuild_cholesky(self):
        n = len(self.reservoir)
        if n == 0: return
        X = np.array([self._normalize(r.features) for r in self.reservoir])
        # Use vectorized kernel computation
        # K_ij = exp(-||x_i - x_j||^2 / 2sigma^2)
        # ||x_i - x_j||^2 = ||x_i||^2 + ||x_j||^2 - 2 x_i^T x_j
        sq_norms = np.sum(X**2, axis=1)
        dist_sq = sq_norms[:, np.newaxis] + sq_norms[np.newaxis, :] - 2 * np.dot(X, X.T)
        K = np.exp(-dist_sq / (2 * self.sigma**2))
        K += np.eye(n) * self.epsilon
        self.L = scipy.linalg.cholesky(K, lower=True)

class HardFilters:
    @staticmethod
    def apply(m: MaterialCandidate) -> bool:
        # 1. Cheap scalar checks: Redox window and Na mobility
        if not (1.0 <= m.V_redox <= 4.2): return False
        if m.D_Na < 1e-12: return False

        # 2. Medium: Cost adjustment (simulating Nigerian FX/import)
        if m.C_adj > 2000: return False

        # 3. Expensive: Numerical stability / complex simulations (simulated)
        if np.any(np.isnan(m.features)) or np.any(np.isinf(m.features)): return False

        return True

class MaterialSource:
    def fetch_batches(self) -> Generator[List[MaterialCandidate], None, None]:
        raise NotImplementedError()

class Pipeline:
    def __init__(self, k=1000):
        self.state = PipelineState(job_id="NG-ESS-REDUCTION-001")
        self.reductor = DPPReductor(k=k)
        self.thermal_model = ThermalModel()
        self.observed_states = []

    def _update_state(self, status=None, progress=None):
        if status: self.state.status = status
        if progress is not None: self.state.progress = progress
        self.observed_states.append(self.state.status.value)

    def run_pipeline(self, sources: Iterable[MaterialSource]):
        self._update_state(status=PipelineStatus.CALIBRATING)

        # Phase 0: Calibrate environment using synthetic Nigerian grid data
        t_amb = 27 + 273.15 + np.random.normal(0, 2, 100) # 27C avg
        q_star = np.random.uniform(50, 200, 100)
        # Generate synthetic T_obs based on a "true" model
        R_true, C_true = 1.2, 450.0
        t_obs = [t_amb[0]]
        for i in range(99):
            t_obs.append(t_obs[-1] + 1.0 * (q_star[i]/C_true - (t_obs[-1] - t_amb[i])/(R_true*C_true)))
        self.thermal_model.calibrate(np.array(t_obs), q_star, t_amb)

        self._update_state(status=PipelineStatus.STREAMING, progress=0.1)

        total_processed = 0
        for source in sources:
            for chunk in source.fetch_batches():
                self._update_state(status=PipelineStatus.REDUCING)
                for m in chunk:
                    total_processed += 1
                    self.state.processed_count = total_processed

                    # 4.3 Hard Filter Optimization
                    if HardFilters.apply(m):
                        # 4.4 Online DPP Reduction
                        if self.reductor.update(m):
                            self.state.retained_count = len(self.reductor.reservoir)

                # Update progress
                self._update_state(progress=min(0.9, 0.1 + 0.8 * (total_processed / 10000.0)))

        # 4.6 Environmental Conditioning
        self._update_state(status=PipelineStatus.COMPLETE, progress=1.0)

        # Apply transformation
        # w_thermal_env, w_grid_env
        beta = 0.9 # Thermal correction for Nigerian climate
        grid_stability_factor = 1.1 # Grid impedance penalty
        for m in self.reductor.reservoir:
            m.S_T *= beta
            m.S_grid *= grid_stability_factor

    def getState(self):
        return self.state

    def getReducedSet(self):
        return self.reductor.reservoir
