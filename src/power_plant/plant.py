import os
import json
import random
import numpy as np
import opendssdirect as dss
from typing import Dict, Any, List, Tuple

class OpenDSSMicrogrid:
    """
    Utility-scale OpenDSS plant-network digital twin simulator.
    Represents a multi-feeder microgrid coupled with shared Solar (100 kW) and BESS (100 kWh).
    Manages known plant assets and unknown downstream distribution network realizations.
    """

    def __init__(self):
        # Known fixed parameters
        self.solar_capacity_kw = 100.0
        self.bess_capacity_kwh = 100.0
        self.base_kv = 11.0 # 11kV Distribution level
        self.feeder_impedance = {"r1": 0.15, "x1": 0.15} # Known feeder linecodes

    def build_base_circuit(self):
        """Initializes the OpenDSS circuit and defines the known plant boundary."""
        dss.Text.Command("clear")
        # Define 11kV utility grid connection / plant substation bus
        dss.Text.Command(f"new circuit.microgrid basekv={self.base_kv} pu=1.0 phases=3")

        # Define known transformer at plant interface (Substation Transformer)
        dss.Text.Command("new transformer.sub_xfmr phases=3 windings=2 wdg=1 bus=sourcebus conn=delta kv=11 kva=200 wdg=2 bus=plant_pcc conn=wye kv=0.415 kva=200")

        # Define shared sources (Solar PV and BESS) coupled at plant_pcc
        # Model Solar PV as generator
        dss.Text.Command(f"new generator.solar bus1=plant_pcc.1.2.3 phases=3 kv=0.415 kw={self.solar_capacity_kw} pf=1.0 model=1")
        # Model AC-coupled BESS as storage/generator
        dss.Text.Command(f"new generator.bess bus1=plant_pcc.1.2.3 phases=3 kv=0.415 kw=50.0 pf=1.0 model=1")

        # Define 2 known outgoing feeder branches from plant_pcc to feeder boundaries (Feeder 1 & Feeder 2)
        dss.Text.Command(f"new line.feeder1 bus1=plant_pcc.1.2.3 bus2=f1_boundary.1.2.3 r1={self.feeder_impedance['r1']} x1={self.feeder_impedance['x1']} length=1.0 units=km")
        dss.Text.Command(f"new line.feeder2 bus1=plant_pcc.1.2.3 bus2=f2_boundary.1.2.3 r1={self.feeder_impedance['r1']} x1={self.feeder_impedance['x1']} length=1.0 units=km")

    def generate_random_downstream_network(self, num_buses: int, topology_type: str = "Radial") -> List[str]:
        """
        Generates an unknown downstream topology connected to the f1_boundary and f2_boundary.
        Returns a list of created lines and loads.
        """
        buses = []
        # Downstream buses are unknown and hidden
        for i in range(1, num_buses + 1):
            buses.append(f"h_bus_{i}")

        elements = []
        # Connect first set of hidden buses to known interfaces
        half_buses = num_buses // 2
        f1_root = "f1_boundary"
        f2_root = "f2_boundary"

        # Topology connection building
        if topology_type == "Radial":
            # Deep branching radial structure (cascaded)
            for i, bus in enumerate(buses):
                parent = f1_root if i < half_buses else f2_root
                if i != 0 and i != half_buses:
                    parent = buses[i - 1]
                # Hidden downstream impedances vary slightly
                r = random.uniform(0.1, 0.4)
                x = random.uniform(0.1, 0.3)
                dss.Text.Command(f"new line.line_{bus} bus1={parent}.1.2.3 bus2={bus}.1.2.3 r1={r:.3f} x1={x:.3f} length=0.5 units=km")
                elements.append(f"Line.line_{bus}")
        else:
            # Star / Multi-drop / Ring-like direct connection topology
            for i, bus in enumerate(buses):
                parent = f1_root if i < half_buses else f2_root
                r = random.uniform(0.2, 0.6)
                x = random.uniform(0.2, 0.5)
                dss.Text.Command(f"new line.line_{bus} bus1={parent}.1.2.3 bus2={bus}.1.2.3 r1={r:.3f} x1={x:.3f} length=1.0 units=km")
                elements.append(f"Line.line_{bus}")

        # Add consumer loads dynamically to hidden buses (known load types, unknown magnitudes)
        for bus in buses:
            kw = random.uniform(2.0, 10.0) # Downstream loads continuously change
            pf = random.uniform(0.85, 0.98)
            dss.Text.Command(f"new load.load_{bus} bus1={bus}.1.2.3 phases=3 kv=0.415 kw={kw:.2f} pf={pf:.2f} model=1")
            elements.append(f"Load.load_{bus}")

        return elements

    def get_boundary_measurements(self) -> Dict[str, Any]:
        """Reads physical boundary measurements from the known plant interfaces (f1_boundary & f2_boundary)."""
        dss.Solution.Solve()

        # Extract voltages
        dss.Circuit.SetActiveBus("f1_boundary")
        f1_volts_mag = dss.Bus.VMagAngle()[0:6:2]
        f1_volts_angle = dss.Bus.VMagAngle()[1:6:2]

        dss.Circuit.SetActiveBus("f2_boundary")
        f2_volts_mag = dss.Bus.VMagAngle()[0:6:2]
        f2_volts_angle = dss.Bus.VMagAngle()[1:6:2]

        # Extract feeder line active/reactive powers
        dss.Circuit.SetActiveElement("Line.feeder1")
        f1_powers = dss.CktElement.Powers()[:6] # Active, Reactive per phase for Term1
        f1_p = sum(f1_powers[0:6:2])
        f1_q = sum(f1_powers[1:6:2])

        dss.Circuit.SetActiveElement("Line.feeder2")
        f2_powers = dss.CktElement.Powers()[:6]
        f2_p = sum(f2_powers[0:6:2])
        f2_q = sum(f2_powers[1:6:2])

        # Derived boundary physics features
        v1_mean = np.mean(f1_volts_mag)
        v2_mean = np.mean(f2_volts_mag)
        theta1_mean = np.mean(f1_volts_angle)
        theta2_mean = np.mean(f2_volts_angle)

        delta_theta = theta1_mean - theta2_mean
        p_total = f1_p + f2_p
        q_total = f1_q + f2_q

        # Calculate voltage sensitivity (V_pcc stiffness indicator)
        dss.Circuit.SetActiveBus("plant_pcc")
        v_pcc = np.mean(dss.Bus.VMagAngle()[:3])

        return {
            "f1_voltage": float(v1_mean),
            "f2_voltage": float(v2_mean),
            "f1_phase": float(theta1_mean),
            "f2_phase": float(theta2_mean),
            "f1_kw": float(f1_p),
            "f1_kvar": float(f1_q),
            "f2_kw": float(f2_p),
            "f2_kvar": float(f2_q),
            "delta_theta": float(delta_theta),
            "p_total": float(p_total),
            "q_total": float(q_total),
            "v_pcc": float(v_pcc)
        }

class SignatureAtlasBuilder:
    """
    Constructs the Network Signature Atlas from OpenDSS experiments
    and maps boundary measurements to latent states X_R = Phi(M).
    """

    def __init__(self):
        self.atlas: List[Dict[str, Any]] = []

    def add_entry(self, sig_id: str, measurements: Dict[str, Any], hidden_state: Dict[str, Any], realization: Dict[str, Any], event: str):
        # Derive robust signature features
        derived_features = {
            "feeder_phase_coupling": measurements["delta_theta"],
            "power_balance_pf": measurements["p_total"] / (np.sqrt(measurements["p_total"]**2 + measurements["q_total"]**2) + 1e-6),
            "aggregate_impedance_proxy": measurements["v_pcc"] / (measurements["p_total"] + 1e-6),
            "voltage_sensitivity_stiffness": (1.0 - (measurements["f1_voltage"] / 240.0)) / (measurements["p_total"] + 1e-6) # normalized to 240V level
        }

        self.atlas.append({
            "sig_id": sig_id,
            "boundary": measurements,
            "features": derived_features,
            "hidden_state": hidden_state,
            "realization": realization,
            "event": event
        })

    def estimate_state(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """
        Latent State Estimation mapping boundary measurements to latent coordinates:
        X_R = Phi(M)
        Uses minimum Euclidean distance on normalized derived signature features.
        """
        if not self.atlas:
            return {"effective_electrical_distance": 1.0, "aggregate_loading_factor": 1.0, "feeder_coupling_index": 0.0, "hidden_buses": 10}

        # Calculate query features
        m_features = {
            "feeder_phase_coupling": m["delta_theta"],
            "power_balance_pf": m["p_total"] / (np.sqrt(m["p_total"]**2 + m["q_total"]**2) + 1e-6),
            "aggregate_impedance_proxy": m["v_pcc"] / (m["p_total"] + 1e-6),
            "voltage_sensitivity_stiffness": (1.0 - (m["f1_voltage"] / 240.0)) / (m["p_total"] + 1e-6)
        }

        best_sig = None
        min_dist = float("inf")

        for entry in self.atlas:
            dist = 0.0
            for k in m_features:
                dist += (m_features[k] - entry["features"][k]) ** 2
            dist = np.sqrt(dist)
            if dist < min_dist:
                min_dist = dist
                best_sig = entry

        # Map to latent state coordinates X_R
        estimated_latent_state = {
            "effective_electrical_distance": best_sig["hidden_state"]["avg_electrical_distance"],
            "aggregate_loading_factor": best_sig["hidden_state"]["loading_factor"],
            "feeder_coupling_index": best_sig["features"]["feeder_phase_coupling"],
            "estimated_buses": best_sig["realization"]["num_buses"],
            "estimated_topology": best_sig["realization"]["topology_type"],
            "matching_sig_id": best_sig["sig_id"],
            "matching_event": best_sig["event"]
        }
        return estimated_latent_state

def run_pipeline_experiments() -> Tuple[List[Dict[str, Any]], SignatureAtlasBuilder]:
    """Runs the 3 physical experiments to populate the Signature Atlas."""
    random.seed(42) # For repeatability
    np.random.seed(42)

    microgrid = OpenDSSMicrogrid()
    atlas_builder = SignatureAtlasBuilder()
    sig_counter = 1

    # --- EXPERIMENT 1: Hidden Bus Discovery (Varying bus count / complexity) ---
    print("Executing Experiment 1: Hidden Bus Discovery...")
    for bus_count in [10, 20, 40, 80]:
        microgrid.build_base_circuit()
        microgrid.generate_random_downstream_network(num_buses=bus_count, topology_type="Radial")
        meas = microgrid.get_boundary_measurements()

        # Hidden state calculation
        avg_dist = 0.5 * (bus_count / 10.0) # Proxy distance
        loading = float(meas["p_total"] / 100.0)

        atlas_builder.add_entry(
            sig_id=f"S{sig_counter:04d}",
            measurements=meas,
            hidden_state={"avg_electrical_distance": avg_dist, "loading_factor": loading},
            realization={"num_buses": bus_count, "topology_type": "Radial"},
            event="Baseline-Complexity"
        )
        sig_counter += 1

    # --- EXPERIMENT 2: Connectivity / Topology Experiment (Fixed buses, different connections) ---
    print("Executing Experiment 2: Topology Connectivity Experiment...")
    for topo in ["Radial", "Multi-drop"]:
        microgrid.build_base_circuit()
        # Fix downstream buses to 20
        microgrid.generate_random_downstream_network(num_buses=20, topology_type=topo)
        meas = microgrid.get_boundary_measurements()

        avg_dist = 0.8 if topo == "Radial" else 0.4
        loading = float(meas["p_total"] / 100.0)

        atlas_builder.add_entry(
            sig_id=f"S{sig_counter:04d}",
            measurements=meas,
            hidden_state={"avg_electrical_distance": avg_dist, "loading_factor": loading},
            realization={"num_buses": 20, "topology_type": topo},
            event=f"Topology-{topo}"
        )
        sig_counter += 1

    # --- EXPERIMENT 3: Dynamic Load Switching ---
    print("Executing Experiment 3: Dynamic Load Switching Experiment...")
    # Fix topology (Radial, 20 buses) and dynamically switch events
    events = ["Normal", "Load Connected", "Motor Start", "Feeder Disconnected"]
    for event in events:
        microgrid.build_base_circuit()
        # Generate baseline downstream
        microgrid.generate_random_downstream_network(num_buses=20, topology_type="Radial")

        # Apply specific load disturbances to represent switching events
        if event == "Load Connected":
            dss.Text.Command("new load.dist_load bus1=h_bus_5 kw=35.0 pf=0.95")
        elif event == "Motor Start":
            # Low power factor starting surge
            dss.Text.Command("new load.starting_motor bus1=h_bus_10 kw=50.0 pf=0.45")
        elif event == "Feeder Disconnected":
            # Disconnect a downstream line
            dss.Text.Command("line.line_h_bus_15.enabled=false")

        meas = microgrid.get_boundary_measurements()
        avg_dist = 1.0
        loading = float(meas["p_total"] / 100.0)

        atlas_builder.add_entry(
            sig_id=f"S{sig_counter:04d}",
            measurements=meas,
            hidden_state={"avg_electrical_distance": avg_dist, "loading_factor": loading},
            realization={"num_buses": 20, "topology_type": "Radial"},
            event=event
        )
        sig_counter += 1

    # Save constructed atlas to json
    serialized_atlas = [
        {
            "sig_id": entry["sig_id"],
            "boundary": entry["boundary"],
            "features": entry["features"],
            "hidden_state": entry["hidden_state"],
            "realization": entry["realization"],
            "event": entry["event"]
        } for entry in atlas_builder.atlas
    ]

    os.makedirs("src/power_plant", exist_ok=True)
    with open("src/power_plant/signature_atlas.json", "w") as f:
        json.dump(serialized_atlas, f, indent=2)
    print("Network Signature Atlas successfully saved to src/power_plant/signature_atlas.json")

    return serialized_atlas, atlas_builder

if __name__ == "__main__":
    atlas_data, builder = run_pipeline_experiments()
    # Run test query
    test_meas = builder.atlas[0]["boundary"]
    estimated = builder.estimate_state(test_meas)
    print("\n--- TEST QUERY STATE ESTIMATION ---")
    print("Estimated Latent State coordinates:")
    for k, v in estimated.items():
        print(f"  {k:30s}: {v}")
