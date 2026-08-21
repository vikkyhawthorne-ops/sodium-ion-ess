import numpy as np
import pandas as pd
from pathlib import Path

def compute_mae(gt: np.ndarray, est: np.ndarray) -> float:
    gt = np.asarray(gt, dtype=float)
    est = np.asarray(est, dtype=float)
    return float(np.mean(np.abs(gt - est)))

def compute_rmse(gt: np.ndarray, est: np.ndarray) -> float:
    gt = np.asarray(gt, dtype=float)
    est = np.asarray(est, dtype=float)
    return float(np.sqrt(np.mean((gt - est)**2)))

def run_dataset_1_correlation_analysis():
    """
    Evaluates load frequency reconstruction accuracy on Dataset 1 by comparing ground truth unmetered consumer units
    and electrical parameters with estimator predictions across 3 feeder subgroups (feeder_1, feeder_2, feeder_3), reporting MAE and RMSE metrics.
    """
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_1.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 1 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)

    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    results = {}

    mae_unmetered_list = []
    rmse_r_list = []
    rmse_x_list = []
    rmse_z_list = []

    print("--- Running Dataset 1 Load Frequency Reconstruction Unmetered Consumer Unit Testing (MAE & RMSE) ---")

    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            mae_unmetered = compute_mae(sub_df["gt_unmetered_consumer_units"].values, sub_df["est_unmetered_consumer_units"].values)
            rmse_r = compute_rmse(sub_df["gt_r_eq_ohm"].values, sub_df["est_r_eq_ohm"].values)
            rmse_x = compute_rmse(sub_df["gt_x_eq_ohm"].values, sub_df["est_x_eq_ohm"].values)
            rmse_z = compute_rmse(sub_df["gt_z_eq_ohm"].values, sub_df["est_z_eq_ohm"].values)

            mae_unmetered_list.append(mae_unmetered)
            rmse_r_list.append(rmse_r)
            rmse_x_list.append(rmse_x)
            rmse_z_list.append(rmse_z)

            results[sg] = {
                "mae_unmetered_consumer_units": mae_unmetered,
                "rmse_r_eq_ohm": rmse_r,
                "rmse_x_eq_ohm": rmse_x,
                "rmse_z_eq_ohm": rmse_z
            }

            print(f"Subgroup {sg} (N={len(sub_df)}):")
            print(f"  MAE Unmetered Consumer Units: {mae_unmetered:.4f}")
            print(f"  RMSE R_eq:                    {rmse_r:.4f} Ohm")
            print(f"  RMSE X_eq:                    {rmse_x:.4f} Ohm")
            print(f"  RMSE Z_eq:                    {rmse_z:.4f} Ohm")

    avg_mae_unmetered = float(np.mean(mae_unmetered_list)) if mae_unmetered_list else 0.0
    avg_rmse_r = float(np.mean(rmse_r_list)) if rmse_r_list else 0.0
    avg_rmse_x = float(np.mean(rmse_x_list)) if rmse_x_list else 0.0
    avg_rmse_z = float(np.mean(rmse_z_list)) if rmse_z_list else 0.0

    print("\n--- Average Load Frequency Reconstruction Metrics Across All Subgroups ---")
    print(f"Average MAE Unmetered Consumer Units: {avg_mae_unmetered:.4f}")
    print(f"Average RMSE R_eq:                    {avg_rmse_r:.4f} Ohm")
    print(f"Average RMSE X_eq:                    {avg_rmse_x:.4f} Ohm")
    print(f"Average RMSE Z_eq:                    {avg_rmse_z:.4f} Ohm")

    summary = {
        "per_subgroup": results,
        "avg_mae_unmetered_consumer_units": avg_mae_unmetered,
        "avg_rmse_r_eq_ohm": avg_rmse_r,
        "avg_rmse_x_eq_ohm": avg_rmse_x,
        "avg_rmse_z_eq_ohm": avg_rmse_z
    }
    return summary

if __name__ == "__main__":
    run_dataset_1_correlation_analysis()
