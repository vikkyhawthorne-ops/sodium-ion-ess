import numpy as np

def apply_latent_parameter_realization(topology: dict, line_mult: float = 1.0, r_scale: float = 1.0, x_scale: float = 1.0) -> dict:
    """
    Applies latent electrical parameter variations (R_L, X_L, G_L, B_L scaling) to known LV lines.
    Topology structure (buses, branches, connectivity) remains fixed and known.
    """
    modified_topology = {
        "feeder_idx": topology["feeder_idx"],
        "buses": list(topology["buses"]),
        "lines": [dict(ln) for ln in topology["lines"]]
    }

    for ln in modified_topology["lines"]:
        ln["length"] = round(ln["length"] * line_mult, 4)
        # Vary latent line parameters
        ln["r1"] = round(ln.get("r1", 0.21) * r_scale, 4)
        ln["x1"] = round(ln.get("x1", 0.08) * x_scale, 4)
        ln["r0"] = round(ln.get("r0", 0.63) * r_scale, 4)
        ln["x0"] = round(ln.get("x0", 0.24) * x_scale, 4)

    return modified_topology

# Alias for backward compatibility
apply_topology_reconfiguration = apply_latent_parameter_realization
