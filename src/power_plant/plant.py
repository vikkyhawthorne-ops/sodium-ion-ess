import numpy as np
from dataclasses import dataclass
from typing import Optional
from opendssdirect import dss
from src.power_plant.sources import configure_generator, apply_generator_profile
from src.power_plant.transformers import get_distribution_transformer_spec
from src.hidden_network.pcc_meters import extract_consumer_meter_data

@dataclass
class OperatingPoint:
    time_s: float
    generator_p_kw: float
    generator_q_kvar: float
    feeder_p_kw: dict
    feeder_q_kvar: dict
    transformer_loading: dict
    voltage_pu: dict
    frequency_hz: float
    transient_waveforms: Optional[object] = None # Associated ATP transient waveforms for EMT dynamics not provided in OpenDSS
    phase_voltages_v: Optional[dict] = None
    phase_angles_deg: Optional[dict] = None

    def import_atp_cases(self, atp_waveforms):
        """
        Imports and associates high-fidelity ATP-EMTP transient cases
        to provide the transient waveforms not supported by OpenDSS.
        """
        self.transient_waveforms = atp_waveforms

def initialize_known_plant(use_baseline_transformers: bool = False):
    """
    Initializes the fixed upstream distribution station using OpenDSS.
    The known plant has standard distribution voltage levels:
    - Utility Grid Source (33 kV)
    - Injection Substation Transformer (33 kV to 11 kV, 7.5 MVA)
    - Main Distribution Bus (11 kV)
    - PCU / Shared Generator (coupled at 11 kV main_bus)
    - Medium-voltage Switchgear
    - Three 11 kV Feeders (Line 1, Line 2, Line 3)
    - Fixed set of three 11/0.415 kV step-down Distribution Transformers acting as edge interfaces
    """
    print("INFO: Initializing OpenDSS Physics-Based Known Plant Model (33/11/0.415 kV)...")

    # 1. Clear previous systems and define main circuit at swing bus (33 kV)
    dss.Basic.ClearAll()
    dss.run_command("new circuit.FixedPlant basekv=33.0 pu=1.0 phases=3")

    # 2. Substation Transformer (33 kV to 11 kV, delta-wye, 7.5 MVA)
    dss.run_command(
        "new transformer.substation "
        "phases=3 windings=2 "
        "buses=[sourcebus, main_bus] "
        "conns=[delta, wye] "
        "kvs=[33.0, 11.0] "
        "kvas=[7500, 7500] "
        "%r=0.6 "
        "%loadloss=0.667 "
        "%noloadloss=0.1 "
        "%imag=0.8 "
        "xhl=8.33"
    )

    # 3. Configure Controllable Shared Generator (coupled at 11 kV main_bus)
    configure_generator(p_kw=1500.0, q_kvar=0.0)

    # 4. Outgoing radial 11 kV Feeders (Line 1, Line 2, Line 3)
    dss.run_command("new linecode.feeder nphases=3 r1=0.25 x1=0.35 r0=0.75 x0=1.12 c1=12.0 c0=6.0 units=km")

    # Feeders extending from main_bus to the respective 11 kV feeder head buses
    dss.run_command("new line.feeder1 bus1=main_bus bus2=feeder1_head phases=3 linecode=feeder length=4.5 units=km")
    dss.run_command("new line.feeder2 bus1=main_bus bus2=feeder2_head phases=3 linecode=feeder length=6.2 units=km")
    dss.run_command("new line.feeder3 bus1=main_bus bus2=feeder3_head phases=3 linecode=feeder length=8.5 units=km")

    # 5. Fixed Set of Distribution Transformers (11/0.415 kV, delta-wye)
    for f_id in [1, 2, 3]:
        spec = get_distribution_transformer_spec(f_id, use_baseline=use_baseline_transformers)
        dss.run_command(
            f"new transformer.{spec['name']} "
            f"phases={spec['phases']} windings={spec['windings']} "
            f"buses=[{','.join(spec['buses'])}] "
            f"conns=[{','.join(spec['conns'])}] "
            f"kvs=[{','.join(map(str, spec['kvs']))}] "
            f"kvas=[{','.join(map(str, spec['kvas']))}] "
            f"%r={spec['r_pct']} "
            f"xhl={spec['xhl_pct']} "
            f"%noloadloss={spec.get('noloadloss_pct', 0.1)} "
            f"%imag={spec.get('imag_pct', 0.8)}"
        )

    print("INFO: OpenDSS Known Plant Model successfully initialized.")

def solve_operating_point(p_kw: float, q_kvar: float, time_s: float = 0.0) -> OperatingPoint:
    """
    Applies generator profiles, runs OpenDSS power flow, and extracts the electrical operating point.
    """
    apply_generator_profile(p_kw, q_kvar)

    dss.Solution.Solve()
    if not dss.Solution.Converged():
        dss.run_command("Solve mode=direct")
        if not dss.Solution.Converged():
            raise RuntimeError(f"OpenDSS failed to converge at t={time_s}s")

    feeder_p = {}
    feeder_q = {}
    loading = {}
    voltage_pu = {}
    phase_voltages_v = {}
    phase_angles_deg = {}

    for idx in [1, 2, 3]:
        meter = {
            "meter_id": f"trans{idx}_lv_boundary_meter",
            "pcc_id": f"trans{idx}_lv_pcc",
            "bus": f"feeder{idx}_sec",
            "parent_bus": f"feeder{idx}_head",
            "branch_id": f"transformer.trans{idx}",
            "branch_type": "transformer"
        }
        data = extract_consumer_meter_data(meter)

        feeder_p[f"feeder{idx}"] = data["p_kw"]
        feeder_q[f"feeder{idx}"] = data["q_kvar"]
        loading[f"transformer{idx}"] = (data["s_kva"] / 1500.0) * 100.0
        v_avg_lv = float(np.mean(data["v_mags"]))
        v_nom_lv = 415.0 / np.sqrt(3.0)
        voltage_pu[f"transformer{idx}"] = v_avg_lv / v_nom_lv

        phase_voltages_v[f"trans{idx}"] = tuple(data["v_mags"])
        phase_angles_deg[f"trans{idx}"] = tuple(data["v_angs"])

    freq = float(dss.Solution.Frequency())

    return OperatingPoint(
        time_s=time_s,
        generator_p_kw=p_kw,
        generator_q_kvar=q_kvar,
        feeder_p_kw=feeder_p,
        feeder_q_kvar=feeder_q,
        transformer_loading=loading,
        voltage_pu=voltage_pu,
        frequency_hz=freq,
        phase_voltages_v=phase_voltages_v,
        phase_angles_deg=phase_angles_deg
    )
