import pybamm
import numpy as np
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

def verify():
    params_dict = get_parameter_values()
    params = pybamm.ParameterValues(params_dict)

    # Solve model
    # Use sodium_ion model if available, fallback to lithium_ion if not
    try:
        model = pybamm.sodium_ion.DFN()
    except AttributeError:
        model = pybamm.lithium_ion.DFN()

    sim = pybamm.Simulation(model, parameter_values=params)
    sol = sim.solve([0, 3600])

    # Physics check: OCV curve and discharge behavior
    print(f"Initial Voltage: {sol['Terminal voltage [V]'].data[0]:.3f} V")
    print(f"Mean Voltage: {np.mean(sol['Terminal voltage [V]'].data):.3f} V")
    print(f"Final Voltage: {sol['Terminal voltage [V]'].data[-1]:.3f} V")
    print(f"Capacity: {sol['Discharge capacity [A.h]'].data[-1]:.3f} Ah")

    # The OCV should be around 3.0-3.1V for NFPP
    if 2.5 < np.mean(sol['Terminal voltage [V]'].data) < 3.5:
        print("Physics check (Voltage) PASSED")
    else:
        print("Physics check (Voltage) FAILED")

if __name__ == "__main__":
    try:
        verify()
    except Exception as e:
        import traceback
        traceback.print_exc()
