import os
import csv
import json
import numpy as np
import pandas as pd
from pathlib import Path

from src.simulation.scenario import KnownLVNetworkScenario, SimulationScenario
from src.simulation.runner import CoSimulationRunner
from src.hidden_network.topology import (
    generate_known_radial_topology,
    identify_candidate_consumer_meters,
    select_metered_consumers
)
from src.hidden_network.loads import distribute_loads
from src.hidden_network.perturbations import apply_latent_parameter_realization
from src.transient.events import (
    SingleEquipmentSwitchEvent,
    SingleLineFaultEvent,
    EquipmentEquipmentCoEvent,
    EquipmentLineFaultCoEvent,
    LineFaultLineFaultCoEvent
)
from src.simulation.kron_reduction import compute_kron_reduced_impedance
from src.estimator.load_estimator import LoadFrequencyReconstructionEstimator
from src.power_plant.transformers import TRANSFORMER_MODELS, BASELINE_TRANSFORMER_MODEL

TRANSFORMER_SPECS = {
    "trans1": {
        "spec_id": TRANSFORMER_MODELS["trans1"]["spec_id"],
        "kva": TRANSFORMER_MODELS["trans1"]["kvas"][0],
        "kv_pri": TRANSFORMER_MODELS["trans1"]["kvs"][0],
        "kv_sec": TRANSFORMER_MODELS["trans1"]["kvs"][1],
        "pct_r": TRANSFORMER_MODELS["trans1"]["r_pct"],
        "pct_x": TRANSFORMER_MODELS["trans1"]["xhl_pct"]
    },
    "trans2": {
        "spec_id": TRANSFORMER_MODELS["trans2"]["spec_id"],
        "kva": TRANSFORMER_MODELS["trans2"]["kvas"][0],
        "kv_pri": TRANSFORMER_MODELS["trans2"]["kvs"][0],
        "kv_sec": TRANSFORMER_MODELS["trans2"]["kvs"][1],
        "pct_r": TRANSFORMER_MODELS["trans2"]["r_pct"],
        "pct_x": TRANSFORMER_MODELS["trans2"]["xhl_pct"]
    },
    "trans3": {
        "spec_id": TRANSFORMER_MODELS["trans3"]["spec_id"],
        "kva": TRANSFORMER_MODELS["trans3"]["kvas"][0],
        "kv_pri": TRANSFORMER_MODELS["trans3"]["kvs"][0],
        "kv_sec": TRANSFORMER_MODELS["trans3"]["kvs"][1],
        "pct_r": TRANSFORMER_MODELS["trans3"]["r_pct"],
        "pct_x": TRANSFORMER_MODELS["trans3"]["xhl_pct"]
    }
}

BASELINE_TX_SPEC = {
    "spec_id": BASELINE_TRANSFORMER_MODEL["spec_id"],
    "kva": BASELINE_TRANSFORMER_MODEL["kvas"][0],
    "kv_pri": BASELINE_TRANSFORMER_MODEL["kvs"][0],
    "kv_sec": BASELINE_TRANSFORMER_MODEL["kvs"][1],
    "pct_r": BASELINE_TRANSFORMER_MODEL["r_pct"],
    "pct_x": BASELINE_TRANSFORMER_MODEL["xhl_pct"]
}


def validate_dataset_1(df_1: pd.DataFrame):
    required_cols = [
        "gt_scenario_id", "gt_feeder_id", "known_number_of_buses", "known_number_of_branches",
        "gt_total_consumer_units", "gt_metered_consumer_units", "gt_unmetered_consumer_units",
        "gt_r_eq_ohm", "gt_x_eq_ohm", "gt_z_eq_ohm",
        "est_total_consumer_units", "est_metered_consumer_units", "est_unmetered_consumer_units",
        "est_unmetered_power_kw", "est_r_eq_ohm", "est_x_eq_ohm", "est_z_eq_ohm",
        "obs_steady_state_time", "obs_steady_state_voltage_abc", "obs_steady_state_current_abc"
    ]
    for col in required_cols:
        if col not in df_1.columns:
            raise ValueError(f"Dataset 1 validation error: missing required column '{col}'")

    for idx, row in df_1.iterrows():
        if row["known_number_of_buses"] <= 0 or row["gt_total_consumer_units"] <= 0:
            raise ValueError(f"Dataset 1 row {idx}: known_number_of_buses and gt_total_consumer_units must be > 0")

    print("INFO: Dataset 1 validation passed successfully.")


def validate_event_pair_dataset(df: pd.DataFrame, dataset_name: str, allow_time_shift: bool, allow_tx_var: bool):
    required_cols = [
        "gt_scenario_id", "gt_transformer_id", "gt_transformer_spec_id", "gt_feeder_id", "gt_meter_id",
        "gt_pair_category",
        "gt_event_1_class", "gt_event_1_type", "gt_event_1_start_timestamp_s",
        "gt_event_2_class", "gt_event_2_type", "gt_event_2_start_timestamp_s",
        "gt_time_offset_s",
        "obs_coevent_time", "obs_coevent_v", "obs_coevent_i",
        "obs_composed_single_event_v", "obs_composed_single_event_i",
        "obs_residual_v", "obs_residual_i",
        "residual_voltage_magnitude", "residual_current_magnitude"
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"{dataset_name} validation error: missing required column '{col}'")

    if not allow_tx_var:
        unique_specs = df["gt_transformer_spec_id"].unique()
        if len(unique_specs) > 1:
            raise ValueError(f"{dataset_name} validation error: must NOT include transformer specification variation! Found: {unique_specs}")

    if not allow_time_shift:
        unique_offsets = df["gt_time_offset_s"].unique()
        if any(abs(off) > 1e-6 for off in unique_offsets):
            raise ValueError(f"{dataset_name} validation error: must NOT include time shift variation! Found: {unique_offsets}")

    for idx, row in df.iterrows():
        v_res = json.loads(row["obs_residual_v"])
        i_res = json.loads(row["obs_residual_i"])
        if len(v_res) != 3 or len(i_res) != 3:
            raise ValueError(f"{dataset_name} row {idx}: residual waveform must have 3 phases")
        if not np.isfinite(row["residual_voltage_magnitude"]) or not np.isfinite(row["residual_current_magnitude"]):
            raise ValueError(f"{dataset_name} row {idx}: non-finite residual magnitude")

    print(f"INFO: {dataset_name} validation passed successfully.")


def generate_experiments_dataset(n_scenarios: int = 15, write_to_disk: bool = True):
    """
    Orchestrates dataset generation for Dataset 1 (36% consumer meter load group frequency reconstruction of unmetered units),
    Dataset 2 (Q1), Dataset 3 (Q2), and Dataset 4 (Q3).
    """
    print("INFO: Sweeping scenarios and generating Datasets 1, 2, 3, and 4 with 36% consumer coverage...")
    runner = CoSimulationRunner()
    freq_estimator = LoadFrequencyReconstructionEstimator(seed=42)

    rows_1 = []
    rows_2 = []
    rows_3 = []
    rows_4 = []

    signature_catalog = {}

    scenario_configs = [
        {"r_scale": 0.95, "x_scale": 0.95, "load_comp": "linear"},
        {"r_scale": 1.05, "x_scale": 1.05, "load_comp": "non_linear"},
        {"r_scale": 1.15, "x_scale": 1.15, "load_comp": "heavy_duty"},
        {"r_scale": 0.90, "x_scale": 0.90, "load_comp": "linear"},
        {"r_scale": 1.00, "x_scale": 1.00, "load_comp": "non_linear"},
        {"r_scale": 1.10, "x_scale": 1.10, "load_comp": "heavy_duty"},
        {"r_scale": 1.20, "x_scale": 1.20, "load_comp": "linear"},
        {"r_scale": 0.98, "x_scale": 0.98, "load_comp": "non_linear"},
        {"r_scale": 1.02, "x_scale": 1.02, "load_comp": "heavy_duty"},
        {"r_scale": 1.08, "x_scale": 1.08, "load_comp": "linear"},
        {"r_scale": 1.12, "x_scale": 1.12, "load_comp": "non_linear"},
        {"r_scale": 0.92, "x_scale": 0.92, "load_comp": "heavy_duty"},
        {"r_scale": 1.04, "x_scale": 1.04, "load_comp": "linear"},
        {"r_scale": 1.16, "x_scale": 1.16, "load_comp": "non_linear"},
        {"r_scale": 0.88, "x_scale": 0.88, "load_comp": "heavy_duty"}
    ]

    equipment_types = ["ac_motor", "dc_motor_inverter", "microwave", "induction_plate"]
    fault_types = ["LG", "LL", "LLG", "LLL"]
    fault_phase_map = {
        "LG": (0,),
        "LL": (0, 1),
        "LLG": (0, 1),
        "LLL": (0, 1, 2)
    }

    for idx in range(min(n_scenarios, len(scenario_configs))):
        scenario_id = f"scenario_{idx}"
        config = scenario_configs[idx]
        rng = np.random.default_rng(idx + 1000)

        feeder_idx = (idx % 3) + 1
        r_scale = float(config["r_scale"])
        x_scale = float(config["x_scale"])

        topologies = {}
        all_buses = []
        all_lines = []

        for f_idx in [1, 2, 3]:
            num_buses_f = {1: 20, 2: 25, 3: 30}[f_idx]
            base_f = generate_known_radial_topology(f_idx, num_buses_f, rng=rng)
            mod_f = apply_latent_parameter_realization(base_f, line_mult=1.0, r_scale=r_scale, x_scale=x_scale)

            topologies[f_idx] = mod_f
            all_buses.extend(mod_f["buses"])
            all_lines.extend(mod_f["lines"])

        modified_topo = {
            "topologies": topologies,
            "buses": all_buses,
            "lines": all_lines
        }

        loads1 = distribute_loads(topologies[1]["buses"], rng=rng)
        loads2 = distribute_loads(topologies[2]["buses"], rng=rng)
        loads3 = distribute_loads(topologies[3]["buses"], rng=rng)

        loads_dist = {
            "loads": loads1["loads"] + loads2["loads"] + loads3["loads"],
            "capacitors": loads1["capacitors"] + loads2["capacitors"] + loads3["capacitors"],
            "motors": loads1["motors"] + loads2["motors"] + loads3["motors"],
            "ders": loads1["ders"] + loads2["ders"] + loads3["ders"]
        }

        if config["load_comp"] == "linear":
            load_comp = {"linear": 0.7, "non_linear": 0.15, "heavy_duty": 0.15}
        elif config["load_comp"] == "non_linear":
            load_comp = {"linear": 0.15, "non_linear": 0.7, "heavy_duty": 0.15}
        else:
            load_comp = {"linear": 0.15, "non_linear": 0.15, "heavy_duty": 0.7}

        # --- A. DATASET 1 GENERATION (36% Metered Consumer Load Group Frequency Reconstruction of Unmetered Units) ---
        multi_op_consumer_meas = {1: [], 2: [], 3: []}
        multi_op_feeder_meas = {1: [], 2: [], 3: []}
        latest_sim_result = None

        for op_idx in range(5):
            trans_load_val = float(30.0 + 10.0 * op_idx)
            k_net_scen = KnownLVNetworkScenario(
                scenario_id=f"{scenario_id}_op_{op_idx}",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"r_scale": r_scale, "x_scale": x_scale},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": trans_load_val, "trans2": trans_load_val, "trans3": trans_load_val},
                switching_events=[]
            )

            dummy_ev = SingleEquipmentSwitchEvent(
                equipment_type="ac_motor",
                start_time_s=0.02,
                duration_s=0.04,
                target=f"down_{feeder_idx}_1",
                parameters={}
            )

            sim_scen = SimulationScenario(
                known_network=k_net_scen,
                generator_p_kw=1500.0,
                generator_q_kvar=0.0,
                events=[dummy_ev],
                meter_fraction=0.36, # 36% consumer meter coverage
                seed=42 + idx + op_idx * 100
            )

            sim_result = runner.run_scenario(sim_scen, use_baseline_transformers=False)
            latest_sim_result = sim_result

            for f_id in [1, 2, 3]:
                m_id = f"trans{f_id}_lv_boundary_meter"
                pcc_key = f"trans{f_id}_lv_pcc"
                meas = sim_result.steady_state_measurements.get(m_id, sim_result.steady_state_measurements.get(pcc_key, {}))
                multi_op_feeder_meas[f_id].append(meas)

                consumer_meas = [
                    v for k, v in sim_result.steady_state_measurements.items()
                    if k.startswith("consumer_meter_") and f"_{f_id}_" in k
                ]
                if not consumer_meas:
                    consumer_meas = [{"p_kw": float(meas.get("p_kw", 30.0)) * 0.36 / 3.0}]
                multi_op_consumer_meas[f_id].append(consumer_meas)

        time_s = latest_sim_result.time_s

        for f_id in [1, 2, 3]:
            m_id = f"trans{f_id}_lv_boundary_meter"
            pcc_key = f"trans{f_id}_lv_pcc"
            meter_res = latest_sim_result.processed_meters.get(m_id, latest_sim_result.processed_meters.get(pcc_key))

            gt_r, gt_x, gt_z, _, _ = compute_kron_reduced_impedance(topologies[f_id])
            feeder_meas_avg = multi_op_feeder_meas[f_id][-1]
            consumer_meas_last = multi_op_consumer_meas[f_id][-1]

            known_buses_count = len(topologies[f_id]["buses"])
            known_branches_count = len(topologies[f_id]["lines"])

            # Total true consumer units in feeder f_id
            gt_total_units = max(1, len(topologies[f_id]["lines"]))
            gt_metered_units = max(1, int(np.ceil(0.36 * gt_total_units)))
            gt_unmetered_units = gt_total_units - gt_metered_units

            freq_est = freq_estimator.estimate(
                metered_consumer_measurements=consumer_meas_last,
                feeder_measurements=feeder_meas_avg,
                known_num_buses=known_buses_count,
                known_num_branches=known_branches_count
            )

            v_raw_ss = meter_res["raw_voltage"] if meter_res is not None else np.zeros((len(time_s), 3))
            i_raw_ss = meter_res["raw_current"] if meter_res is not None else np.zeros((len(time_s), 3))

            v_ss_abc = [v_raw_ss[:, 0].tolist(), v_raw_ss[:, 1].tolist(), v_raw_ss[:, 2].tolist()]
            i_ss_abc = [i_raw_ss[:, 0].tolist(), i_raw_ss[:, 1].tolist(), i_raw_ss[:, 2].tolist()]

            meas_dict = latest_sim_result.steady_state_measurements.get(m_id, latest_sim_result.steady_state_measurements.get(pcc_key, {}))

            row_1 = {
                "gt_scenario_id": f"{scenario_id}_feeder_{f_id}",
                "gt_feeder_id": f"feeder_{f_id}",
                "known_number_of_buses": known_buses_count,
                "known_number_of_branches": known_branches_count,
                "gt_total_consumer_units": gt_total_units,
                "gt_metered_consumer_units": gt_metered_units,
                "gt_unmetered_consumer_units": gt_unmetered_units,
                "gt_r_eq_ohm": gt_r,
                "gt_x_eq_ohm": gt_x,
                "gt_z_eq_ohm": gt_z,
                "est_total_consumer_units": freq_est.estimated_total_consumer_units,
                "est_metered_consumer_units": freq_est.estimated_metered_consumer_units,
                "est_unmetered_consumer_units": freq_est.estimated_unmetered_consumer_units,
                "est_unmetered_power_kw": freq_est.estimated_unmetered_power_kw,
                "est_r_eq_ohm": freq_est.r_eq_ohm,
                "est_x_eq_ohm": freq_est.x_eq_ohm,
                "est_z_eq_ohm": freq_est.z_eq_ohm,
                "obs_steady_state_time": json.dumps(time_s.tolist()),
                "obs_steady_state_voltage_abc": json.dumps(v_ss_abc),
                "obs_steady_state_current_abc": json.dumps(i_ss_abc),
                f"obs_{pcc_key}_voltage_mag_avg": float(np.mean(v_raw_ss)),
                f"obs_{pcc_key}_current_mag_avg": float(np.mean(i_raw_ss)),
                f"obs_{pcc_key}_p_kw": float(meas_dict.get("p_kw", 0.0)),
                f"obs_{pcc_key}_q_kvar": float(meas_dict.get("q_kvar", 0.0))
            }
            rows_1.append(row_1)

        # Catalog single event signatures for reference baseline composition
        single_events_all = []
        known_line_target = f"down_{feeder_idx}_1"
        for eq in equipment_types:
            single_events_all.append(SingleEquipmentSwitchEvent(eq, 0.02, 0.04, known_line_target, {}))
        for ft in fault_types:
            single_events_all.append(SingleLineFaultEvent(ft, 0.02, 0.04, known_line_target, fault_phase_map[ft], 0.05, {}))

        for s_ev in single_events_all:
            k_net_sig = KnownLVNetworkScenario(
                scenario_id=f"{scenario_id}_sig_{s_ev.event_type}",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"r_scale": r_scale, "x_scale": x_scale},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": 50.0, "trans2": 50.0, "trans3": 50.0},
                switching_events=[]
            )
            sim_sig = runner.run_scenario(
                SimulationScenario(known_network=k_net_sig, generator_p_kw=1500.0, generator_q_kvar=0.0, events=[s_ev], meter_fraction=0.36, seed=42+idx),
                use_baseline_transformers=True
            )
            for f_id in [1, 2, 3]:
                m_id = f"trans{f_id}_lv_boundary_meter"
                pcc_key = f"trans{f_id}_lv_pcc"
                meter_res = sim_sig.processed_meters.get(m_id, sim_sig.processed_meters.get(pcc_key))
                if meter_res is not None:
                    signature_catalog[(s_ev.event_class, s_ev.event_type, f"feeder_{f_id}")] = {
                        "v_sig": meter_res["raw_voltage"],
                        "i_sig": meter_res["raw_current"],
                        "time": sim_sig.time_s
                    }

        # --- B. DEFINING EVENT PAIR SCENARIOS ORIGINATING FROM KNOWN LV LINES ---
        eq1 = SingleEquipmentSwitchEvent("ac_motor", 0.02, 0.04, known_line_target, {})
        eq2 = SingleEquipmentSwitchEvent("dc_motor_inverter", 0.02, 0.04, known_line_target, {})
        eq2_shifted = SingleEquipmentSwitchEvent("dc_motor_inverter", 0.03, 0.04, known_line_target, {})

        pair_ll_simultaneous = EquipmentEquipmentCoEvent(eq1, eq2)
        pair_ll_shifted = EquipmentEquipmentCoEvent(eq1, eq2_shifted)

        flt1 = SingleLineFaultEvent("LG", 0.02, 0.04, known_line_target, (0,), 0.05, {})
        flt2 = SingleLineFaultEvent("LL", 0.02, 0.04, known_line_target, (0, 1), 0.05, {})
        flt2_shifted = SingleLineFaultEvent("LL", 0.03, 0.04, known_line_target, (0, 1), 0.05, {})

        pair_ff_simultaneous = LineFaultLineFaultCoEvent(flt1, flt2)
        pair_ff_shifted = LineFaultLineFaultCoEvent(flt1, flt2_shifted)

        pair_lf_simultaneous = EquipmentLineFaultCoEvent(eq1, flt1)
        pair_lf_shifted = EquipmentLineFaultCoEvent(eq1, flt2_shifted)

        # --- C. DATASET 2 GENERATION (Question 1: Event Observability across Event Pairs, 36% Coverage, Single Baseline Tx Spec) ---
        d2_pairs = [
            ("load_load", pair_ll_simultaneous),
            ("fault_fault", pair_ff_simultaneous),
            ("load_fault", pair_lf_simultaneous)
        ]

        for pair_cat, co_ev in d2_pairs:
            ev1, ev2 = co_ev.event_1, co_ev.event_2
            k_net_d2 = KnownLVNetworkScenario(
                scenario_id=f"{scenario_id}_q1_{pair_cat}",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"r_scale": r_scale, "x_scale": x_scale},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": 50.0, "trans2": 50.0, "trans3": 50.0},
                switching_events=[]
            )
            sim_res_d2 = runner.run_scenario(
                SimulationScenario(known_network=k_net_d2, generator_p_kw=1500.0, generator_q_kvar=0.0, events=[co_ev], meter_fraction=0.36, seed=42+idx),
                use_baseline_transformers=True
            )
            t_s = sim_res_d2.time_s

            for f_id in [1, 2, 3]:
                m_id = f"trans{f_id}_lv_boundary_meter"
                pcc_key = f"trans{f_id}_lv_pcc"
                meter_res = sim_res_d2.processed_meters.get(m_id, sim_res_d2.processed_meters.get(pcc_key))
                if meter_res is not None:
                    v_co, i_co = meter_res["raw_voltage"], meter_res["raw_current"]
                    sig1 = signature_catalog.get((ev1.event_class, ev1.event_type, f"feeder_{f_id}"))
                    sig2 = signature_catalog.get((ev2.event_class, ev2.event_type, f"feeder_{f_id}"))
                    v_comp = (sig1["v_sig"] + sig2["v_sig"]) if (sig1 and sig2) else v_co
                    i_comp = (sig1["i_sig"] + sig2["i_sig"]) if (sig1 and sig2) else i_co
                    res_v, res_i = v_co - v_comp, i_co - i_comp

                    rows_2.append({
                        "gt_scenario_id": f"{scenario_id}_q1_{pair_cat}",
                        "gt_transformer_id": f"trans{f_id}",
                        "gt_transformer_spec_id": BASELINE_TX_SPEC["spec_id"],
                        "gt_feeder_id": f"feeder_{f_id}",
                        "gt_meter_id": m_id,
                        "gt_pcc_id": pcc_key,
                        "gt_pair_category": pair_cat,
                        "gt_event_1_class": ev1.event_class,
                        "gt_event_1_type": ev1.event_type,
                        "gt_event_1_equipment_type": getattr(ev1, "equipment_type", ""),
                        "gt_event_1_fault_type": getattr(ev1, "fault_type", ""),
                        "gt_event_1_start_timestamp_s": float(ev1.start_time_s),
                        "gt_event_2_class": ev2.event_class,
                        "gt_event_2_type": ev2.event_type,
                        "gt_event_2_equipment_type": getattr(ev2, "equipment_type", ""),
                        "gt_event_2_fault_type": getattr(ev2, "fault_type", ""),
                        "gt_event_2_start_timestamp_s": float(ev2.start_time_s),
                        "gt_time_offset_s": 0.0,
                        "obs_coevent_time": json.dumps(t_s.tolist()),
                        "obs_coevent_v": json.dumps([v_co[:, 0].tolist(), v_co[:, 1].tolist(), v_co[:, 2].tolist()]),
                        "obs_coevent_i": json.dumps([i_co[:, 0].tolist(), i_co[:, 1].tolist(), i_co[:, 2].tolist()]),
                        "obs_composed_single_event_v": json.dumps([v_comp[:, 0].tolist(), v_comp[:, 1].tolist(), v_comp[:, 2].tolist()]),
                        "obs_composed_single_event_i": json.dumps([i_comp[:, 0].tolist(), i_comp[:, 1].tolist(), i_comp[:, 2].tolist()]),
                        "obs_residual_v": json.dumps([res_v[:, 0].tolist(), res_v[:, 1].tolist(), res_v[:, 2].tolist()]),
                        "obs_residual_i": json.dumps([res_i[:, 0].tolist(), res_i[:, 1].tolist(), res_i[:, 2].tolist()]),
                        "residual_voltage_magnitude": round(float(np.sqrt(np.mean(res_v**2))), 6),
                        "residual_current_magnitude": round(float(np.sqrt(np.mean(res_i**2))), 6)
                    })

        # --- D. DATASET 3 GENERATION (Question 2: Residual Magnitude Variation with Time Shift Operation, 36% Coverage) ---
        d3_pairs = [
            ("load_load", pair_ll_simultaneous),
            ("load_load", pair_ll_shifted),
            ("fault_fault", pair_ff_simultaneous),
            ("fault_fault", pair_ff_shifted),
            ("load_fault", pair_lf_simultaneous),
            ("load_fault", pair_lf_shifted)
        ]

        for pair_cat, co_ev in d3_pairs:
            ev1, ev2 = co_ev.event_1, co_ev.event_2
            time_offset = co_ev.time_offset_s
            k_net_d3 = KnownLVNetworkScenario(
                scenario_id=f"{scenario_id}_q2_{pair_cat}_{time_offset}s",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"r_scale": r_scale, "x_scale": x_scale},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": 50.0, "trans2": 50.0, "trans3": 50.0},
                switching_events=[]
            )
            sim_res_d3 = runner.run_scenario(
                SimulationScenario(known_network=k_net_d3, generator_p_kw=1500.0, generator_q_kvar=0.0, events=[co_ev], meter_fraction=0.36, seed=42+idx),
                use_baseline_transformers=True
            )
            t_s = sim_res_d3.time_s

            for f_id in [1, 2, 3]:
                m_id = f"trans{f_id}_lv_boundary_meter"
                pcc_key = f"trans{f_id}_lv_pcc"
                meter_res = sim_res_d3.processed_meters.get(m_id, sim_res_d3.processed_meters.get(pcc_key))
                if meter_res is not None:
                    v_co, i_co = meter_res["raw_voltage"], meter_res["raw_current"]
                    sig1 = signature_catalog.get((ev1.event_class, ev1.event_type, f"feeder_{f_id}"))
                    sig2 = signature_catalog.get((ev2.event_class, ev2.event_type, f"feeder_{f_id}"))
                    v_comp = (sig1["v_sig"] + sig2["v_sig"]) if (sig1 and sig2) else v_co
                    i_comp = (sig1["i_sig"] + sig2["i_sig"]) if (sig1 and sig2) else i_co
                    res_v, res_i = v_co - v_comp, i_co - i_comp

                    rows_3.append({
                        "gt_scenario_id": f"{scenario_id}_q2_{pair_cat}_{time_offset}s",
                        "gt_transformer_id": f"trans{f_id}",
                        "gt_transformer_spec_id": BASELINE_TX_SPEC["spec_id"],
                        "gt_feeder_id": f"feeder_{f_id}",
                        "gt_meter_id": m_id,
                        "gt_pcc_id": pcc_key,
                        "gt_pair_category": pair_cat,
                        "gt_event_1_class": ev1.event_class,
                        "gt_event_1_type": ev1.event_type,
                        "gt_event_1_equipment_type": getattr(ev1, "equipment_type", ""),
                        "gt_event_1_fault_type": getattr(ev1, "fault_type", ""),
                        "gt_event_1_start_timestamp_s": float(ev1.start_time_s),
                        "gt_event_2_class": ev2.event_class,
                        "gt_event_2_type": ev2.event_type,
                        "gt_event_2_equipment_type": getattr(ev2, "equipment_type", ""),
                        "gt_event_2_fault_type": getattr(ev2, "fault_type", ""),
                        "gt_event_2_start_timestamp_s": float(ev2.start_time_s),
                        "gt_time_offset_s": float(time_offset),
                        "obs_coevent_time": json.dumps(t_s.tolist()),
                        "obs_coevent_v": json.dumps([v_co[:, 0].tolist(), v_co[:, 1].tolist(), v_co[:, 2].tolist()]),
                        "obs_coevent_i": json.dumps([i_co[:, 0].tolist(), i_co[:, 1].tolist(), i_co[:, 2].tolist()]),
                        "obs_composed_single_event_v": json.dumps([v_comp[:, 0].tolist(), v_comp[:, 1].tolist(), v_comp[:, 2].tolist()]),
                        "obs_composed_single_event_i": json.dumps([i_comp[:, 0].tolist(), i_comp[:, 1].tolist(), i_comp[:, 2].tolist()]),
                        "obs_residual_v": json.dumps([res_v[:, 0].tolist(), res_v[:, 1].tolist(), res_v[:, 2].tolist()]),
                        "obs_residual_i": json.dumps([res_i[:, 0].tolist(), res_i[:, 1].tolist(), res_i[:, 2].tolist()]),
                        "residual_voltage_magnitude": round(float(np.sqrt(np.mean(res_v**2))), 6),
                        "residual_current_magnitude": round(float(np.sqrt(np.mean(res_i**2))), 6)
                    })

        # --- E. DATASET 4 GENERATION (Question 3: Transformer Specification Effect on Event Pairs, 36% Coverage) ---
        d4_pairs = [
            ("load_load", pair_ll_simultaneous),
            ("fault_fault", pair_ff_simultaneous),
            ("load_fault", pair_lf_simultaneous)
        ]

        for pair_cat, co_ev in d4_pairs:
            ev1, ev2 = co_ev.event_1, co_ev.event_2
            k_net_d4 = KnownLVNetworkScenario(
                scenario_id=f"{scenario_id}_q3_{pair_cat}",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"r_scale": r_scale, "x_scale": x_scale},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": 50.0, "trans2": 50.0, "trans3": 50.0},
                switching_events=[]
            )
            sim_res_d4 = runner.run_scenario(
                SimulationScenario(known_network=k_net_d4, generator_p_kw=1500.0, generator_q_kvar=0.0, events=[co_ev], meter_fraction=0.36, seed=42+idx),
                use_baseline_transformers=False
            )
            t_s = sim_res_d4.time_s

            for f_id in [1, 2, 3]:
                tx_id = f"trans{f_id}"
                m_id = f"trans{f_id}_lv_boundary_meter"
                pcc_key = f"trans{f_id}_lv_pcc"
                meter_res = sim_res_d4.processed_meters.get(m_id, sim_res_d4.processed_meters.get(pcc_key))
                tx_spec = TRANSFORMER_SPECS[tx_id]

                if meter_res is not None:
                    v_co, i_co = meter_res["raw_voltage"], meter_res["raw_current"]
                    sig1 = signature_catalog.get((ev1.event_class, ev1.event_type, f"feeder_{f_id}"))
                    sig2 = signature_catalog.get((ev2.event_class, ev2.event_type, f"feeder_{f_id}"))
                    v_comp = (sig1["v_sig"] + sig2["v_sig"]) if (sig1 and sig2) else v_co
                    i_comp = (sig1["i_sig"] + sig2["i_sig"]) if (sig1 and sig2) else i_co
                    res_v, res_i = v_co - v_comp, i_co - i_comp

                    rows_4.append({
                        "gt_scenario_id": f"{scenario_id}_q3_{pair_cat}",
                        "gt_transformer_id": tx_id,
                        "gt_transformer_spec_id": tx_spec["spec_id"],
                        "gt_feeder_id": f"feeder_{f_id}",
                        "gt_meter_id": m_id,
                        "gt_pcc_id": pcc_key,
                        "gt_pair_category": pair_cat,
                        "gt_event_1_class": ev1.event_class,
                        "gt_event_1_type": ev1.event_type,
                        "gt_event_1_equipment_type": getattr(ev1, "equipment_type", ""),
                        "gt_event_1_fault_type": getattr(ev1, "fault_type", ""),
                        "gt_event_1_start_timestamp_s": float(ev1.start_time_s),
                        "gt_event_2_class": ev2.event_class,
                        "gt_event_2_type": ev2.event_type,
                        "gt_event_2_equipment_type": getattr(ev2, "equipment_type", ""),
                        "gt_event_2_fault_type": getattr(ev2, "fault_type", ""),
                        "gt_event_2_start_timestamp_s": float(ev2.start_time_s),
                        "gt_time_offset_s": 0.0,
                        "obs_coevent_time": json.dumps(t_s.tolist()),
                        "obs_coevent_v": json.dumps([v_co[:, 0].tolist(), v_co[:, 1].tolist(), v_co[:, 2].tolist()]),
                        "obs_coevent_i": json.dumps([i_co[:, 0].tolist(), i_co[:, 1].tolist(), i_co[:, 2].tolist()]),
                        "obs_composed_single_event_v": json.dumps([v_comp[:, 0].tolist(), v_comp[:, 1].tolist(), v_comp[:, 2].tolist()]),
                        "obs_composed_single_event_i": json.dumps([i_comp[:, 0].tolist(), i_comp[:, 1].tolist(), i_comp[:, 2].tolist()]),
                        "obs_residual_v": json.dumps([res_v[:, 0].tolist(), res_v[:, 1].tolist(), res_v[:, 2].tolist()]),
                        "obs_residual_i": json.dumps([res_i[:, 0].tolist(), res_i[:, 1].tolist(), res_i[:, 2].tolist()]),
                        "residual_voltage_magnitude": round(float(np.sqrt(np.mean(res_v**2))), 6),
                        "residual_current_magnitude": round(float(np.sqrt(np.mean(res_i**2))), 6)
                    })

    df_1 = pd.DataFrame(rows_1)
    df_2 = pd.DataFrame(rows_2)
    df_3 = pd.DataFrame(rows_3)
    df_4 = pd.DataFrame(rows_4)

    validate_dataset_1(df_1)
    validate_event_pair_dataset(df_2, "Dataset 2", allow_time_shift=False, allow_tx_var=False)
    validate_event_pair_dataset(df_3, "Dataset 3", allow_time_shift=True, allow_tx_var=False)
    validate_event_pair_dataset(df_4, "Dataset 4", allow_time_shift=False, allow_tx_var=True)

    if write_to_disk:
        dir_path = Path("src/simulation")
        dir_path.mkdir(parents=True, exist_ok=True)
        df_1.to_csv(dir_path / "dataset_1.csv", index=False)
        df_2.to_csv(dir_path / "dataset_2.csv", index=False)
        df_3.to_csv(dir_path / "dataset_3.csv", index=False)
        df_4.to_csv(dir_path / "dataset_4.csv", index=False)
        print(f"INFO: Successfully written validated datasets to {dir_path / 'dataset_1.csv'}, {dir_path / 'dataset_2.csv'}, {dir_path / 'dataset_3.csv'}, and {dir_path / 'dataset_4.csv'}")

    return df_1, df_2, df_3, df_4


if __name__ == "__main__":
    generate_experiments_dataset(n_scenarios=15, write_to_disk=True)
