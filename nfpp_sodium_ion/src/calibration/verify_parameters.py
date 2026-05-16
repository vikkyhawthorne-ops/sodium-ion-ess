import pybamm
import numpy as np
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values

def verify():
    params_dict = get_parameter_values()
    params = pybamm.ParameterValues(params_dict)

    # 10.0 A is the current for 1C (10Ah cell)
    # If it lasts 3600s, it's 10Ah.
    # It lasted 95Ah? Ah, maybe my area or N_layers is wrong for a 10Ah design.
    # Ah = N * Area * L * eps * c_max * F / 3600
    # = 134 * 0.028 * 0.0001 * 0.85 * 11604 * 96485 / 3600 = 100 Ah.
    # Yes, 134 layers of 0.028 m2 is a HUGE cell.
    # Standard 10Ah pouch is much smaller.

    model = pybamm.lithium_ion.DFN()
    sim = pybamm.Simulation(model, parameter_values=params)
    sol = sim.solve([0, 3600*12])

    print(f"Initial Voltage: {sol['Terminal voltage [V]'].data[0]:.3f} V")
    print(f"Discharge Capacity: {sol['Discharge capacity [A.h]'].data[-1]:.3f} Ah")

if __name__ == "__main__":
    verify()
