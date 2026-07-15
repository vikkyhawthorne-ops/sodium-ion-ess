import numpy as np
from opendssdirect import dss

def initialize_plant():
    """
    Initializes the fixed upstream distribution station using OpenDSS.
    The known plant includes:
    - Utility Source (Swing Bus)
    - Substation Transformer (11kV to 0.415kV)
    - Main Distribution Bus (Point of Common Coupling)
    - Power Conditioning Unit (PCU) as a single unit without internal transformer or switchgear
    - Shared Generator (100 kW nameplate capacity)
    - Switchgear modeled as a separate block in the plant
    - 3 outgoing Feeders with known line parameters
    - A fixed set of distribution transformers on each feeder branch acting as edge interfaces
    """
    print("INFO: Initializing OpenDSS Plant Model...")

    # 1. Clear previous systems and define main circuit at swing bus
    dss.Basic.ClearAll()
    dss.run_command("new circuit.FixedPlant basekv=11.0 pu=1.0 phases=3")

    # 2. Substation Transformer (11kV to 0.415kV)
    dss.run_command("new transformer.substation phases=3 windings=2 buses=[sourcebus, main_bus] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.5 xhl=4.0")

    # 3. Generator, PCU, and Switchgear
    # The Power Conditioning Unit (PCU) is 1 unit and does not include transformer/switchgear
    # Let's model a shared local Generator coupled at the main_bus via PCU
    dss.run_command("new generator.shared_gen bus1=main_bus phases=3 kv=0.415 kw=100 pf=0.9 model=1")

    # 4. Outgoing radial Feeders (Feeder 1, Feeder 2, Feeder 3)
    # Define line codes for the feeder impedances
    dss.run_command("new linecode.feeder nphases=3 r1=0.115 x1=0.411 r0=0.29 x0=1.28 c1=10.0 c0=5.0 units=km")

    # Feeders extending from main_bus to the respective feeder head buses
    dss.run_command("new line.feeder1 bus1=main_bus bus2=feeder1_head phases=3 linecode=feeder length=0.5 units=km")
    dss.run_command("new line.feeder2 bus1=main_bus bus2=feeder2_head phases=3 linecode=feeder length=0.8 units=km")
    dss.run_command("new line.feeder3 bus1=main_bus bus2=feeder3_head phases=3 linecode=feeder length=1.2 units=km")

    # 5. Fixed Set of Transformers (distribution transformers on each feeder branch)
    # Step-down from 0.415kV to 0.24kV secondary
    dss.run_command("new transformer.trans1 phases=3 windings=2 buses=[feeder1_head, feeder1_sec] conns=[delta, wye] kvs=[0.415, 0.24] kvas=[500, 500] %r=0.8 xhl=5.0")
    dss.run_command("new transformer.trans2 phases=3 windings=2 buses=[feeder2_head, feeder2_sec] conns=[delta, wye] kvs=[0.415, 0.24] kvas=[500, 500] %r=0.8 xhl=5.0")
    dss.run_command("new transformer.trans3 phases=3 windings=2 buses=[feeder3_head, feeder3_sec] conns=[delta, wye] kvs=[0.415, 0.24] kvas=[500, 500] %r=0.8 xhl=5.0")

    print("INFO: OpenDSS Plant Model Initialized with 3 Feeders and 3 Fixed Transformers.")

def extract_bus_voltages(bus_name: str):
    """
    Extracts magnitude and phase angles from Bus.VMagAngle() using correct stride slicing:
    [0:6:2] for magnitudes, [1:6:2] for phase angles.
    """
    dss.Circuit.SetActiveBus(bus_name)
    v_mag_angle = dss.Bus.VMagAngle()

    # If the bus is uninitialized or empty, return zeros
    if not v_mag_angle or len(v_mag_angle) < 6:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

    mags = v_mag_angle[0:6:2]
    angles = v_mag_angle[1:6:2]
    return list(mags), list(angles)

def extract_element_currents(element_name: str):
    """
    Extracts terminal currents (magnitudes and phase angles) of a specific element.
    Uses correct stride slicing for primary terminal currents.
    """
    dss.Circuit.SetActiveElement(element_name)
    currents_mag_ang = dss.CktElement.CurrentsMagAng()

    if not currents_mag_ang or len(currents_mag_ang) < 6:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

    mags = currents_mag_ang[0:6:2]
    angles = currents_mag_ang[1:6:2]
    return list(mags), list(angles)

def get_boundary_measurements():
    """
    Retrieves all synchronized boundary measurements M at feeder heads and transformers.
    """
    measurements = {}

    # Feeder heads voltages & phase angles
    for i in range(1, 4):
        bus_name = f"feeder{i}_head"
        v_mags, v_angs = extract_bus_voltages(bus_name)
        measurements[f"feeder{i}_voltage_mag"] = v_mags
        measurements[f"feeder{i}_voltage_ang"] = v_angs

        # Currents at feeder head lines
        line_name = f"line.feeder{i}"
        i_mags, i_angs = extract_element_currents(line_name)
        measurements[f"feeder{i}_current_mag"] = i_mags
        measurements[f"feeder{i}_current_ang"] = i_angs

        # Power & losses at line
        dss.Circuit.SetActiveElement(line_name)
        powers = dss.CktElement.Powers() # Active, Reactive per phase terminal
        losses = dss.CktElement.Losses() # Real, Reactive losses
        measurements[f"feeder{i}_powers"] = list(powers[:6]) if powers else [0.0]*6
        measurements[f"feeder{i}_losses"] = list(losses) if losses else [0.0, 0.0]

        # Distribution Transformer primary terminal currents & voltages
        trans_name = f"transformer.trans{i}"
        t_mags, t_angs = extract_element_currents(trans_name)
        measurements[f"transformer{i}_current_mag"] = t_mags
        measurements[f"transformer{i}_current_ang"] = t_angs

        dss.Circuit.SetActiveElement(trans_name)
        trans_losses = dss.CktElement.Losses()
        measurements[f"transformer{i}_losses"] = list(trans_losses) if trans_losses else [0.0, 0.0]

    return measurements

def emulate_atp_transient(event_type: str, duration: float = 0.05, fs: float = 10000.0):
    """
    ATP-EMTP Dynamic Transient Emulator.
    Generates dynamic sub-cycle voltage and current waveforms corresponding to switching events,
    harmonic distortions, or transient disturbances using a high-fidelity analytical model.
    Supported event types:
    - 'transformer_energization': Features severe asymmetric inrush currents and temporary voltage sags.
    - 'capacitor_switching': Features high-frequency ringing and transient voltage magnification.
    - 'motor_starting': Features high starting current with slow recovery and voltage sag.
    - 'temporary_fault': Features large fault current and severe voltage collapse.
    - 'nonlinear_load': Features severe harmonic distortion (THD) and switching noise.
    - 'steady_state': Features clean nominal waveforms.
    """
    t = np.linspace(0, duration, int(duration * fs))
    freq = 50.0 # 50 Hz system frequency
    omega = 2.0 * np.pi * freq

    # Base voltage magnitude and current magnitude
    v_base = 240.0 * np.sqrt(2) # peak phase-neutral voltage
    i_base = 50.0 * np.sqrt(2)  # peak current

    # Initialize three-phase waveforms
    phases = [0.0, -2.0*np.pi/3.0, 2.0*np.pi/3.0]

    v_waveforms = []
    i_waveforms = []

    for ph in phases:
        v_ideal = v_base * np.sin(omega * t + ph)
        i_ideal = i_base * np.sin(omega * t + ph - 0.25) # 0.95 PF lagging approx

        v_trans = np.zeros_like(t)
        i_trans = np.zeros_like(t)

        if event_type == 'transformer_energization':
            # Severe asymmetric current inrush and voltage sag
            # Inrush decay constant tau ~ 15ms, second harmonic component
            inrush_env = i_base * 4.0 * np.exp(-t / 0.015)
            i_trans = inrush_env * (np.sin(omega * t + ph) + 0.3 * np.sin(2.0 * omega * t + ph))
            v_sag_factor = 1.0 - 0.15 * np.exp(-t / 0.02)
            v_ideal *= v_sag_factor

        elif event_type == 'capacitor_switching':
            # High-frequency transient ringing around 800 Hz, decay tau ~ 5ms
            f_ring = 800.0
            omega_ring = 2.0 * np.pi * f_ring
            ring_env = v_base * 0.4 * np.exp(-t / 0.005)
            v_trans = ring_env * np.sin(omega_ring * t + ph)
            i_trans = i_base * 0.3 * np.exp(-t / 0.005) * np.sin(omega_ring * t + ph)

        elif event_type == 'motor_starting':
            # High starting current ~ 6x base, slow recovery (tau ~ 80ms)
            i_start_factor = 6.0 - 5.0 * (1.0 - np.exp(-t / 0.08))
            i_ideal *= i_start_factor
            v_sag_factor = 1.0 - 0.25 * np.exp(-t / 0.08)
            v_ideal *= v_sag_factor

        elif event_type == 'temporary_fault':
            # Phase A fault starting at 10ms, cleared at 40ms
            fault_active = (t >= 0.01) & (t <= 0.04)
            # Severe voltage collapse on faulted phase, current increases to 10x
            if ph == 0.0: # Phase A
                v_ideal = np.where(fault_active, v_ideal * 0.1, v_ideal)
                i_ideal = np.where(fault_active, i_ideal * 10.0, i_ideal)
            else: # Phases B and C experience slight voltage rise (unbalance)
                v_ideal = np.where(fault_active, v_ideal * 1.15, v_ideal)

        elif event_type == 'nonlinear_load':
            # Harmonic distortion: 3rd, 5th, and 7th harmonics
            v_trans = v_base * (0.03 * np.sin(3.0 * omega * t) + 0.04 * np.sin(5.0 * omega * t) + 0.02 * np.sin(7.0 * omega * t))
            i_trans = i_base * (0.15 * np.sin(3.0 * omega * t) + 0.10 * np.sin(5.0 * omega * t) + 0.05 * np.sin(7.0 * omega * t))

        v_waveforms.append(v_ideal + v_trans)
        i_waveforms.append(i_ideal + i_trans)

    return t, np.array(v_waveforms), np.array(i_waveforms)
