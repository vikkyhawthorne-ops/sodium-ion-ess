import numpy as np

def generate_known_radial_topology(feeder_idx: int, num_buses: int = 20, rng=None) -> dict:
    """
    Generates a deterministic known radial tree topology represented as a dictionary of buses and lines.
    Uses feeder_idx to determine default bus counts if num_buses is not specified (LV1=20, LV2=25, LV3=30).
    Uses local seeded RNG for perfect reproducibility.
    """
    if num_buses is None or num_buses <= 0:
        default_counts = {1: 20, 2: 25, 3: 30}
        num_buses = default_counts.get(feeder_idx, 20)

    if rng is None:
        rng = np.random.default_rng(42 + feeder_idx)

    root_bus = f"feeder{feeder_idx}_sec"
    buses = [root_bus]
    lines = []

    # Deterministic known line lengths
    for i in range(1, num_buses):
        new_bus = f"f{feeder_idx}_node{i}"
        # Known tree connectivity: connect to a parent bus in the existing tree
        parent_bus = buses[(i - 1) // 2] if i > 1 else root_bus

        l_km = float(0.05 + 0.01 * (i % 5))
        lines.append({
            "name": f"down_{feeder_idx}_{i}",
            "bus1": parent_bus,
            "bus2": new_bus,
            "length": round(l_km, 4),
            "units": "km",
            # Default physical conductor parameters (150 mm2 AAC overhead, 350 A capacity)
            "r1": 0.21,
            "x1": 0.08,
            "r0": 0.63,
            "x0": 0.24,
            "norm_amps": 350.0
        })
        buses.append(new_bus)

    return {
        "feeder_idx": feeder_idx,
        "buses": buses,
        "lines": lines
    }

# Alias for backward compatibility
generate_radial_topology = generate_known_radial_topology

def identify_candidate_consumer_meters(topology: dict) -> list[dict]:
    """
    Identifies candidate consumer meters and edge transformer meters across the known LV network.
    """
    candidate_meters = []

    # 1. Standard branch lines / consumer nodes
    for ln in topology.get("lines", []):
        parent = ln["bus1"]
        child = ln["bus2"]
        line_name = ln["name"]

        candidate_meters.append({
            "meter_id": f"consumer_meter_{line_name}",
            "bus": child,
            "parent_bus": parent,
            "branch_id": line_name,
            "branch_type": "consumer_line",
            "meter_eligible": True
        })

    # 2. LV secondary terminals of the distribution transformers (Feeder boundary meters)
    for idx in [1, 2, 3]:
        candidate_meters.append({
            "meter_id": f"trans{idx}_lv_boundary_meter",
            "bus": f"feeder{idx}_sec",
            "parent_bus": f"feeder{idx}_head",
            "branch_id": f"transformer.trans{idx}",
            "branch_type": "transformer_boundary",
            "meter_eligible": True
        })

    return candidate_meters

# Alias for backward compatibility
identify_candidate_pccs = identify_candidate_consumer_meters

def select_metered_consumers(candidate_meters: list[dict], fraction: float, seed: int) -> list[dict]:
    """
    Selects all transformer boundary meters and a configured fraction of consumer meters.
    """
    if not (0.0 < fraction <= 1.0):
        raise ValueError(f"meter_fraction must be in (0.0, 1.0], got {fraction}")

    transformer_meters = [m for m in candidate_meters if m.get("branch_type") == "transformer_boundary"]
    consumer_meters = [m for m in candidate_meters if m.get("branch_type") != "transformer_boundary"]

    n_consumer_meters = max(1, int(np.ceil(fraction * len(consumer_meters)))) if consumer_meters else 0

    rng = np.random.default_rng(seed)

    if consumer_meters:
        selected_indices = rng.choice(len(consumer_meters), size=n_consumer_meters, replace=False)
        selected_consumer_meters = [consumer_meters[i] for i in selected_indices]
    else:
        selected_consumer_meters = []

    return transformer_meters + selected_consumer_meters

# Alias for backward compatibility
select_metered_pccs = select_metered_consumers
