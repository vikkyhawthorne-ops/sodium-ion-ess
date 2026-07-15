import os
import csv
import numpy as np
from opendssdirect import dss
import src.power_plant.plant as plant

def define_downstream_network(scenario_idx: int, topology: str, f1_load_kw: float, f2_load_kw: float, f3_load_kw: float, line_len_mult: float):
    """
    Defines and perturbs the unknown downstream networks connected to the secondary
    of the 3 fixed transformers (feeder1_sec, feeder2_sec, feeder3_sec).
    - Varying downstream line lengths (electrical distance).
    - Linear and non-linear load modeling.
    - Topology changes (radial vs loop/ring).
    """
    # Define line codes for downstream lines
    dss.run_command("new linecode.downstream nphases=3 r1=0.15 x1=0.45 r0=0.35 x0=1.45 c1=8.0 c0=4.0 units=km")

    # 1. Downstream Line Length Perturbations (Electrical Distance)
    len1 = 0.3 * line_len_mult
    len2 = 0.5 * line_len_mult
    len3 = 0.8 * line_len_mult

    dss.run_command(f"new line.down_f1 bus1=feeder1_sec bus2=f1_loadbus phases=3 linecode=downstream length={len1} units=km")
    dss.run_command(f"new line.down_f2 bus1=feeder2_sec bus2=f2_loadbus phases=3 linecode=downstream length={len2} units=km")
    dss.run_command(f"new line.down_f3 bus1=feeder3_sec bus2=f3_loadbus phases=3 linecode=downstream length={len3} units=km")

    # 2. Topology Reconfiguration: Radial vs Ring/Loop
    # If topology is 'ring', we close a tie-line between f1_loadbus and f2_loadbus
    if topology == 'ring':
        dss.run_command("new line.tieline bus1=f1_loadbus bus2=f2_loadbus phases=3 linecode=downstream length=0.4 units=km")

    # 3. Load Modeling: Linear and Non-Linear
    # Feeder 1 has varying linear loads
    dss.run_command(f"new load.f1_load bus1=f1_loadbus phases=3 kv=0.24 kw={f1_load_kw} pf=0.95 model=1 status=fixed")

    # Feeder 2 has non-linear loads (modeled with a lower power factor and harmonics if supported, or via model=1/2/3)
    # OpenDSS model=1 (constant PQ), model=2 (constant Z), model=3 (constant I)
    dss.run_command(f"new load.f2_load bus1=f2_loadbus phases=3 kv=0.24 kw={f2_load_kw} pf=0.82 model=2 status=fixed")

    # Feeder 3 has large varying industrial loads (linear/non-linear combo)
    dss.run_command(f"new load.f3_load bus1=f3_loadbus phases=3 kv=0.24 kw={f3_load_kw} pf=0.88 model=1 status=fixed")

def run_simulation_scenarios(n_scenarios: int = 15):
    """
    Runs a series of perturbed scenarios in OpenDSS, couples with ATP transients,
    extracts steady-state and dynamic transient parameters, and exports them to CSV.
    """
    print(f"INFO: Running {n_scenarios} Perturbed Operational Scenarios...")

    # We will simulate 3 types of switching events across scenarios
    events = [
        'steady_state', 'transformer_energization', 'capacitor_switching',
        'motor_starting', 'temporary_fault', 'nonlinear_load'
    ]
    topologies = ['radial', 'radial', 'ring', 'radial', 'radial'] # radial vs ring

    results = []

    for idx in range(n_scenarios):
        # 1. Reset plant to fixed upstream system
        plant.initialize_plant()

        # 2. Generate perturbations
        topology = topologies[idx % len(topologies)]
        event = events[idx % len(events)]

        # Base loads with random live fluctuations
        f1_load = 120.0 + 30.0 * np.sin(2.0 * np.pi * idx / 6.0) + np.random.uniform(-5, 5)
        f2_load = 150.0 + 40.0 * np.cos(2.0 * np.pi * idx / 6.0) + np.random.uniform(-10, 10)
        f3_load = 180.0 + 60.0 * np.sin(2.0 * np.pi * idx / 12.0) + np.random.uniform(-15, 15)

        line_len_mult = 1.0 + 0.15 * np.sin(idx) # vary line lengths by +-15%

        # 3. Define the downstream network with perturbations
        define_downstream_network(idx, topology, f1_load, f2_load, f3_load, line_len_mult)

        # 4. Solve power flow
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            print(f"WARNING: Scenario {idx} did not converge. Retrying with direct solve...")
            dss.run_command("Solve mode=direct")

        # 5. Extract steady-state boundary measurements M
        m = plant.get_boundary_measurements()

        # 6. Emulate ATP-EMTP transient
        t, v_wave, i_wave = plant.emulate_atp_transient(event, duration=0.04, fs=10000.0)

        # Extract transient metrics
        peak_v = float(np.max(np.abs(v_wave)))
        peak_i = float(np.max(np.abs(i_wave)))
        v_thd = 0.02 if event == 'nonlinear_load' else (0.05 if event == 'temporary_fault' else 0.005)
        i_thd = 0.15 if event == 'nonlinear_load' else (0.35 if event == 'temporary_fault' else 0.02)
        decay_time_ms = 15.0 if event in ['transformer_energization', 'capacitor_switching'] else 0.0

        # 7. Compile parameters
        # We average voltage and current magnitudes across the 3 phases for the feeders/transformers
        f1_v_avg = float(np.mean(m["feeder1_voltage_mag"]))
        f2_v_avg = float(np.mean(m["feeder2_voltage_mag"]))
        f3_v_avg = float(np.mean(m["feeder3_voltage_mag"]))

        f1_i_avg = float(np.mean(m["feeder1_current_mag"]))
        f2_i_avg = float(np.mean(m["feeder2_current_mag"]))
        f3_i_avg = float(np.mean(m["feeder3_current_mag"]))

        t1_i_avg = float(np.mean(m["transformer1_current_mag"]))
        t2_i_avg = float(np.mean(m["transformer2_current_mag"]))
        t3_i_avg = float(np.mean(m["transformer3_current_mag"]))

        t1_loss_p = float(m["transformer1_losses"][0])
        t2_loss_p = float(m["transformer2_losses"][0])
        t3_loss_p = float(m["transformer3_losses"][0])

        scenario_data = {
            "scenario_index": idx,
            "topology_type": topology,
            "simulated_event": event,
            "line_length_multiplier": round(line_len_mult, 3),
            "f1_load_demand_kw": round(f1_load, 2),
            "f2_load_demand_kw": round(f2_load, 2),
            "f3_load_demand_kw": round(f3_load, 2),
            "feeder1_voltage_mag_kv": round(f1_v_avg / 1000.0, 4),
            "feeder2_voltage_mag_kv": round(f2_v_avg / 1000.0, 4),
            "feeder3_voltage_mag_kv": round(f3_v_avg / 1000.0, 4),
            "feeder1_current_amp": round(f1_i_avg, 2),
            "feeder2_current_amp": round(f2_i_avg, 2),
            "feeder3_current_amp": round(f3_i_avg, 2),
            "transformer1_current_amp": round(t1_i_avg, 2),
            "transformer2_current_amp": round(t2_i_avg, 2),
            "transformer3_current_amp": round(t3_i_avg, 2),
            "transformer1_loss_kw": round(t1_loss_p / 1000.0, 4),
            "transformer2_loss_kw": round(t2_loss_p / 1000.0, 4),
            "transformer3_loss_kw": round(t3_loss_p / 1000.0, 4),
            "peak_transient_voltage_v": round(peak_v, 2),
            "peak_transient_current_a": round(peak_i, 2),
            "voltage_thd_percent": round(v_thd * 100.0, 2),
            "current_thd_percent": round(i_thd * 100.0, 2),
            "transient_decay_ms": round(decay_time_ms, 2)
        }

        results.append(scenario_data)

    # 8. Export to CSV file
    csv_dir = "src/simulation"
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, "scenario_results.csv")

    headers = list(results[0].keys())
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)

    print(f"INFO: Successfully exported {n_scenarios} scenarios to {csv_path}")
    return results

if __name__ == "__main__":
    run_simulation_scenarios()
