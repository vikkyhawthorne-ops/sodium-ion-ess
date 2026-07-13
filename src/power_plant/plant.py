import os
import json
import random
import numpy as np
import opendssdirect as dss
from typing import Dict, Any, List, Tuple

class MonteCarloMicrogridCampaign:
    """
    Combines a fixed solar-BESS plant with a dynamic Monte Carlo downstream network simulator.
    Evaluates hidden distribution network state realization from boundary electrical signatures.
    """

    def __init__(self):
        self.solar_capacity_kw = 100.0
        self.bess_capacity_kwh = 100.0
        self.base_kv = 11.0 # 11kV MV level
        self.pcc_bus = "plant_pcc"
        self.signature_db: List[Dict[str, Any]] = []

    def build_fixed_plant(self):
        """Builds the static, unchanged plant infrastructure above the PCC."""
        dss.Text.Command("clear")

        # 1. 3-Phase 11kV Substation Source
        dss.Text.Command(f"new circuit.plant_network basekv={self.base_kv} pu=1.0 phases=3")

        # 2. MV/LV Step-up Transformer (11kV to 0.415kV)
        dss.Text.Command("new transformer.sub_xfmr phases=3 windings=2 wdg=1 bus=sourcebus conn=delta kv=11 kva=200 wdg=2 bus=plant_pcc conn=wye kv=0.415 kva=200")

        # 3. PV System: 100 kWp Solar PV subsystem at plant_pcc
        dss.Text.Command("new generator.solar bus1=plant_pcc phases=3 kv=0.415 kw=100.0 pf=1.0 model=1")

        # 4. Battery Storage: 100 kWh AC-coupled BESS coupled at plant_pcc
        dss.Text.Command("new generator.bess bus1=plant_pcc phases=3 kv=0.415 kw=50.0 pf=1.0 model=1")

        # 5. Known Plant Feeders outgoing from PCC (feeder 1 and feeder 2)
        dss.Text.Command("new line.feeder1 bus1=plant_pcc bus2=f1_boundary phases=3 r1=0.15 x1=0.15 length=1.0 units=km")
        dss.Text.Command("new line.feeder2 bus1=plant_pcc bus2=f2_boundary phases=3 r1=0.15 x1=0.15 length=1.0 units=km")

    def generate_random_hidden_network(self, num_buses: int, topology_type: str = "Radial") -> List[str]:
        """
        Generates a random unknown downstream network.
        Uses random line lengths, random conductor types, random load locations and transformers.
        """
        elements = []
        buses = [f"h_bus_{i}" for i in range(1, num_buses + 1)]

        # Define random linecodes (conductor types)
        linecodes = [
            {"r1": 0.25, "x1": 0.20, "name": "cond_light"},
            {"r1": 0.12, "x1": 0.10, "name": "cond_medium"},
            {"r1": 0.06, "x1": 0.05, "name": "cond_heavy"}
        ]
        for lc in linecodes:
            dss.Text.Command(f"new linecode.{lc['name']} nphases=3 r1={lc['r1']} x1={lc['x1']}")

        # Root interface boundary buses
        roots = ["f1_boundary", "f2_boundary"]

        # Build connections dynamically
        for i, bus in enumerate(buses):
            # Select root or parent bus
            if i == 0:
                parent = roots[0]
            elif i == num_buses // 2:
                parent = roots[1]
            else:
                # Random connection to form an unknown topology
                if topology_type == "Radial":
                    parent = buses[i - 1]
                else:
                    # Mesh / Multi-drop connections
                    parent = random.choice(buses[:i] + roots)

            # Random line length and conductor type
            length = random.uniform(0.2, 1.5) # km
            lc = random.choice(linecodes)["name"]

            # Connect the line
            dss.Text.Command(f"new line.line_{bus} bus1={parent} bus2={bus} phases=3 linecode={lc} length={length:.3f} units=km")
            elements.append(f"Line.line_{bus}")

            # Random transformer location (e.g. 15% chance of adding a local distribution step-down xfmr)
            if random.random() < 0.15:
                dss.Text.Command(f"new transformer.xfmr_{bus} phases=3 windings=2 wdg=1 bus={bus} kv=0.415 kva=50 wdg=2 bus={bus}_sec kv=0.208 kva=50")
                load_bus = f"{bus}_sec"
            else:
                load_bus = bus

            # Place consumer loads at random locations with random nominal parameters
            kw = random.uniform(5.0, 30.0)
            pf = random.uniform(0.85, 0.98)
            dss.Text.Command(f"new load.load_{bus} bus1={load_bus} phases=3 kv=0.415 kw={kw:.2f} pf={pf:.2f} model=1")
            elements.append(f"Load.load_{bus}")

        return elements

    def apply_dynamic_load_switching(self):
        """Simulates switching events, motor starts, tap changes, and line outages programmatically."""
        # Get all load names in OpenDSS
        loads = dss.Loads.AllNames()
        lines = dss.Lines.AllNames()

        # 1. Randomly connect/disconnect or scale loads
        for load in loads:
            dss.Loads.Name(load)
            if random.random() < 0.15:
                # Disconnect load (set kW to 0)
                dss.Loads.kW(0.0)
            elif random.random() < 0.15:
                # Motor starting simulation (high starting reactive surge, low PF)
                dss.Loads.kW(dss.Loads.kW() * 1.8)
                dss.Loads.PF(0.45) # Surge PF
            else:
                # Normal operational fluctuations
                dss.Loads.kW(dss.Loads.kW() * random.uniform(0.85, 1.25))

        # 2. Toggle random line switches (line outages)
        for line in lines:
            if "feeder" not in line and random.random() < 0.05:
                # Disconnect line/switch
                dss.Text.Command(f"Line.{line}.enabled=false")

        # 3. Change transformer tap programmatically
        dss.Transformers.First()
        dss.Transformers.Tap(random.choice([0.95, 1.0, 1.05]))

    def collect_boundary_measurements(self) -> Dict[str, Any]:
        """Collects electrical measurements only at the known plant PCC and feeder boundaries."""
        dss.Solution.Solve()

        # Measure plant PCC voltage, current, active/reactive powers, phase angles, frequency
        dss.Circuit.SetActiveBus(self.pcc_bus)
        pcc_volts = dss.Bus.VMagAngle()[0:6:2]
        pcc_angles = dss.Bus.VMagAngle()[1:6:2]
        v_pcc_mean = np.mean(pcc_volts)
        theta_pcc_mean = np.mean(pcc_angles)

        # Output current and power from the transformer
        dss.Circuit.SetActiveElement("Transformer.sub_xfmr")
        currents = dss.CktElement.Currents()[:6]
        i_pcc_mean = np.mean(currents)
        powers = dss.CktElement.Powers()[:6]
        p_pcc = sum(powers[0:6:2])
        q_pcc = sum(powers[1:6:2])

        # Frequency proxy based on nominal voltage frequency
        frequency = 50.0 + random.normalvariate(0, 0.02) # Hz

        # Known plant feeder measurements
        dss.Circuit.SetActiveBus("f1_boundary")
        f1_volts = dss.Bus.VMagAngle()[0:6:2]
        f1_angles = dss.Bus.VMagAngle()[1:6:2]
        v_f1 = np.mean(f1_volts)
        theta_f1 = np.mean(f1_angles)

        dss.Circuit.SetActiveBus("f2_boundary")
        f2_volts = dss.Bus.VMagAngle()[0:6:2]
        f2_angles = dss.Bus.VMagAngle()[1:6:2]
        v_f2 = np.mean(f2_volts)
        theta_f2 = np.mean(f2_angles)

        # Derived boundary phase relationship (feeder-to-feeder coupling)
        delta_theta = theta_f1 - theta_f2

        return {
            "pcc_voltage_v": float(v_pcc_mean),
            "pcc_current_a": float(i_pcc_mean),
            "pcc_active_power_kw": float(p_pcc),
            "pcc_reactive_power_kvar": float(q_pcc),
            "frequency_hz": float(frequency),
            "pcc_phase_angle_deg": float(theta_pcc_mean),
            "f1_voltage_v": float(v_f1),
            "f2_voltage_v": float(v_f2),
            "delta_theta_deg": float(delta_theta)
        }

    def capture_hidden_ground_truth(self, num_buses: int, topology: str) -> Dict[str, Any]:
        """Captures true downstream state including detailed measurements at sufficient transformer nodes."""
        all_loads = dss.Loads.AllNames()
        active_loads = 0
        total_hidden_demand_kw = 0.0

        for load in all_loads:
            dss.Loads.Name(load)
            kw = dss.Loads.kW()
            if kw > 0:
                active_loads += 1
                total_hidden_demand_kw += kw

        # Average electrical impedance distance from the PCC to all hidden buses
        avg_electrical_distance = 0.0
        lines = dss.Lines.AllNames()
        total_len = 0.0
        for line in lines:
            if "feeder" not in line:
                dss.Lines.Name(line)
                total_len += dss.Lines.Length()
        avg_electrical_distance = total_len / max(len(lines), 1)

        # Retrieve measurements at downstream distribution transformer nodes
        transformer_powers_kw = []
        transformer_powers_kvar = []
        all_transformers = dss.Transformers.AllNames()

        for xfmr in all_transformers:
            # Exclude the known PCC substation transformer
            if xfmr != "sub_xfmr":
                dss.Circuit.SetActiveElement(f"Transformer.{xfmr}")
                powers = dss.CktElement.Powers()
                # Wind 1 active and reactive powers
                if len(powers) >= 6:
                    active_p = sum(powers[0:6:2])
                    reactive_q = sum(powers[1:6:2])
                    transformer_powers_kw.append(float(active_p))
                    transformer_powers_kvar.append(float(reactive_q))

        return {
            "num_buses": num_buses,
            "topology_type": topology,
            "active_loads": active_loads,
            "total_hidden_demand_kw": float(total_hidden_demand_kw),
            "avg_electrical_distance_km": float(avg_electrical_distance),
            "transformer_node_count": len(transformer_powers_kw),
            "transformer_total_p_kw": float(sum(transformer_powers_kw)) if transformer_powers_kw else 0.0,
            "transformer_total_q_kvar": float(sum(transformer_powers_kvar)) if transformer_powers_kvar else 0.0
        }

    def run_monte_carlo_campaign(self, num_realizations: int = 120):
        """Executes a Monte Carlo campaign generating hundreds of random realization scenarios."""
        print(f"Starting Monte Carlo realization campaign with {num_realizations} scenarios...", flush=True)
        self.signature_db = []

        topologies = ["Radial", "Multi-drop"]

        for idx in range(1, num_realizations + 1):
            # Step 1: Fixed plant
            self.build_fixed_plant()

            # Step 2: Random hidden network size and connection type
            num_buses = random.choice([10, 20, 40, 80])
            topology = random.choice(topologies)
            self.generate_random_hidden_network(num_buses, topology)

            # Step 3: Dynamic load switching and tap/switch changes
            self.apply_dynamic_load_switching()

            # Step 4: Collect PCC boundary measurements
            meas = self.collect_boundary_measurements()

            # Step 5: Capture ground truth reference state (including downstream xfmr nodes)
            gt = self.capture_hidden_ground_truth(num_buses, topology)

            # Define noise-robust derived signature features
            derived_features = {
                "feeder_phase_coupling": meas["delta_theta_deg"],
                "power_balance_pf": meas["pcc_active_power_kw"] / (np.sqrt(meas["pcc_active_power_kw"]**2 + meas["pcc_reactive_power_kvar"]**2) + 1e-6),
                "aggregate_impedance_proxy": meas["pcc_voltage_v"] / (abs(meas["pcc_active_power_kw"]) + 1e-6),
                "voltage_sensitivity_stiffness": (1.0 - (meas["f1_voltage_v"] / 240.0)) / (abs(meas["pcc_active_power_kw"]) + 1e-6)
            }

            self.signature_db.append({
                "sig_id": f"S{idx:04d}",
                "boundary": meas,
                "features": derived_features,
                "ground_truth": gt
            })

            if idx % 20 == 0:
                print(f"  Processed {idx}/{num_realizations} random scenarios...", flush=True)

        # Export signature database
        os.makedirs("src/power_plant", exist_ok=True)
        with open("src/power_plant/signature_atlas.json", "w") as f:
            json.dump(self.signature_db, f, indent=2)
        print("Signature Atlas successfully populated and saved to src/power_plant/signature_atlas.json", flush=True)


class LatentNetworkStateEstimator:
    """
    State Estimator mapping boundary measurement signatures to hidden network coordinates:
    X_R = Phi(M)
    Uses a k-NN similarity lookup on the noise-robust features in the Signature Atlas.
    """

    def __init__(self, atlas_path: str = "src/power_plant/signature_atlas.json"):
        with open(atlas_path, "r") as f:
            self.atlas = json.load(f)

    def estimate_latent_state(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """Estimates latent coordinates from boundary measurement vector m."""
        # Calculate derived signature features
        p_act = m["pcc_active_power_kw"]
        p_react = m["pcc_reactive_power_kvar"]
        pf = p_act / (np.sqrt(p_act**2 + p_react**2) + 1e-6)
        impedance = m["pcc_voltage_v"] / (abs(p_act) + 1e-6)
        stiffness = (1.0 - (m["f1_voltage_v"] / 240.0)) / (abs(p_act) + 1e-6)

        query_feat = {
            "feeder_phase_coupling": m["delta_theta_deg"],
            "power_balance_pf": pf,
            "aggregate_impedance_proxy": impedance,
            "voltage_sensitivity_stiffness": stiffness
        }

        # Find closest match in Atlas
        best_match = None
        min_distance = float("inf")

        for entry in self.atlas:
            dist = 0.0
            for k in query_feat:
                dist += (query_feat[k] - entry["features"][k]) ** 2
            dist = np.sqrt(dist)
            if dist < min_distance:
                min_distance = dist
                best_match = entry

        gt = best_match["ground_truth"]

        # Latent state coordinates X_R
        return {
            "estimated_buses": gt["num_buses"],
            "estimated_topology": gt["topology_type"],
            "estimated_active_loads": gt["active_loads"],
            "estimated_hidden_demand_kw": gt["total_hidden_demand_kw"],
            "estimated_electrical_distance_km": gt["avg_electrical_distance_km"],
            "estimated_xfmr_nodes_count": gt["transformer_node_count"],
            "estimated_xfmr_total_p_kw": gt["transformer_total_p_kw"],
            "matching_sig_id": best_match["sig_id"]
        }


def run_full_campaign() -> Tuple[List[Dict[str, Any]], LatentNetworkStateEstimator]:
    """Runs the full OpenDSS Monte Carlo network realization campaign and instantiates the Estimator."""
    campaign = MonteCarloMicrogridCampaign()
    campaign.run_monte_carlo_campaign(num_realizations=120)

    estimator = LatentNetworkStateEstimator()
    return campaign.signature_db, estimator


if __name__ == "__main__":
    random.seed(101)
    np.random.seed(101)
    db, estimator = run_full_campaign()

    # Test state estimator on a query
    test_meas = db[5]["boundary"]
    latent_state = estimator.estimate_latent_state(test_meas)
    print("\n--- LATENT STATE ESTIMATION DEMO ---")
    print("Estimated Latent network state coordinates:")
    for k, v in latent_state.items():
        print(f"  {k:35s}: {v}")
