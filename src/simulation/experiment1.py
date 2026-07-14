import numpy as np
import opendssdirect as dss
from src.power_plant.plant import OpenDSSMicrogrid

def run_experiment_1():
    print("Running Experiment 1: Hidden Bus Discovery...")
    microgrid = OpenDSSMicrogrid()

    for buses in [10, 20, 40, 80]:
        microgrid.build_base_circuit()
        microgrid.generate_random_downstream_network(num_buses=buses, topology_type="Radial")
        meas = microgrid.get_boundary_measurements()
        print(f"Buses: {buses:2d} | F1 Volt: {meas['f1_voltage']:7.2f} V | F2 Volt: {meas['f2_voltage']:7.2f} V | Phase Coupling (Delta Theta): {meas['delta_theta']:+.4f}° | Total Power: {meas['p_total']:7.2f} kW", flush=True)

if __name__ == "__main__":
    run_experiment_1()
