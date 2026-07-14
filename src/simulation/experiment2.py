import numpy as np
import opendssdirect as dss
from src.power_plant.plant import OpenDSSMicrogrid

def run_experiment_2():
    print("Running Experiment 2: Connectivity / Topology Experiment...")
    microgrid = OpenDSSMicrogrid()

    for topo in ["Radial", "Multi-drop"]:
        microgrid.build_base_circuit()
        microgrid.generate_random_downstream_network(num_buses=20, topology_type=topo)
        meas = microgrid.get_boundary_measurements()
        pf_proxy = meas['p_total'] / (np.sqrt(meas['p_total']**2 + meas['q_total']**2) + 1e-6)
        print(f"Topology: {topo:10s} | F1 Volt: {meas['f1_voltage']:7.2f} V | Phase Coupling (Delta Theta): {meas['delta_theta']:+.4f}° | Power Factor Proxy: {pf_proxy:.4f}", flush=True)

if __name__ == "__main__":
    run_experiment_2()
