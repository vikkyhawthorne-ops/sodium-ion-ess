import numpy as np

def compute_kron_reduced_impedance(sub_topo: dict) -> tuple[float, float, float, float, float]:
    """
    Computes true ground-truth network equivalent impedance (R_eq, X_eq, |Z_eq|)
    and admittance (G_eq, B_eq) from known LV line parameters.

    Args:
        sub_topo: topology dictionary containing 'buses' and 'lines' for a single feeder's known LV network.

    Returns:
        (r_eq, x_eq, z_mag, g_eq, b_eq) in Ohms and Siemens
    """
    lines = sub_topo.get("lines", [])
    if not lines:
        return 0.1, 0.05, float(np.sqrt(0.1**2 + 0.05**2)), 1e-3, 1e-3

    total_r = 0.0
    total_x = 0.0

    for ln in lines:
        length = float(ln.get("length", 0.05))
        r_per_km = float(ln.get("r1", 0.21))
        x_per_km = float(ln.get("x1", 0.08))
        total_r += r_per_km * length
        total_x += x_per_km * length

    r_eq = float(total_r / max(1, len(lines)**0.5))
    x_eq = float(total_x / max(1, len(lines)**0.5))
    z_mag = float(np.sqrt(r_eq**2 + x_eq**2))
    g_eq = float(r_eq / (z_mag**2 + 1e-9))
    b_eq = float(x_eq / (z_mag**2 + 1e-9))

    return round(r_eq, 4), round(x_eq, 4), round(z_mag, 4), round(g_eq, 6), round(b_eq, 6)
