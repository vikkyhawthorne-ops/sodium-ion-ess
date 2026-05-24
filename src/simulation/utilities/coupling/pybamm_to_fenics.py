import numpy as np

def project_to_fenics(pybamm_var, fenics_space):
    """
    Projects a PyBaMM variable (e.g. Temperature or SOC) onto a FEniCS function space.

    Args:
        pybamm_var: The PyBaMM variable from the solution (e.g. sol["Cell temperature [K]"])
        fenics_space: The FEniCS function space (dolfinx.fem.FunctionSpace)

    Returns:
        dolfinx.fem.Function: The variable interpolated on the FEniCS mesh.
    """
    try:
        from dolfinx import fem
        import ufl
    except ImportError:
        return None

    # This is a simplified projection for 1D/lumped cases commonly used in this twin.
    # In a real full 3D case, we would need to map coordinates.
    # For this implementation, we take the average or the last entry if it's a field.

    val = np.mean(pybamm_var.entries)

    f = fem.Function(fenics_space)
    f.interpolate(lambda x: np.full(x.shape[1], val))

    return f
