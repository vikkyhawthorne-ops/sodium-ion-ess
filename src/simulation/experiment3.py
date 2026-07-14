import numpy as np
import opendssdirect as dss
from src.power_plant.plant import OpenDSSMicrogrid

def run_experiment_3():
    print("Running Experiment 3: Dynamic Load Switching...")
    microgrid = OpenDSSMicrogrid()

    for event in ["Normal", "Load Connected", "Motor Start", "Feeder Disconnected"]:
        microgrid.build_base_circuit()
        microgrid.generate_random_downstream_network(num_buses=20, topology_type="Radial")

        if event == "Load Connected":
            dss.Text.Command("new load.dist_load bus1=h_bus_5 kw=35.0 pf=0.95")
        elif event == "Motor Start":
            dss.Text.Command("new load.starting_motor bus1=h_bus_10 kw=50.0 pf=0.45")
        elif event == "Feeder Disconnected":
            # Safely trip feeder line
            dss.Text.Command("line.line_h_bus_15.enabled=false")

        meas = microgrid.get_boundary_measurements()
        print(f"Event: {event:20s} | Total Power: {meas['p_total']:7.2f} kW | Reactive Power: {meas['q_total']:7.2f} kVAR | PCC Volt: {meas['v_pcc']:7.2f} V", flush=True)

if __name__ == "__main__":
    run_experiment_3()
