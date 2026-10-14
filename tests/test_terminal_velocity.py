"""Acceptance Test 3: Broadside terminal velocity balance."""

import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from autumn.model import AutumnModel
from autumn.params import Coefficients, FluidParams, PlateParams


def test_broadside_terminal_velocity():
    """Acceptance Test 3:
    
    Start with the plate horizontal (theta = 0) and tiny noise suppressed.
    Terminal speed must match the drag balance:
        0.5 * rho_f * C_D(pi/2) * L * U^2 = (rho_s - rho_f) * g * A
    within 2 percent.
    """
    fluid = FluidParams(rho_f=998.0, g=9.81)
    coeffs = Coefficients()
    plate = PlateParams(
        name="reference_card",
        rho_s=1200.0,
        L=0.020,
        h=0.002
    )

    model = AutumnModel(
        plate=plate,
        fluid=fluid,
        coeffs=coeffs,
        enable_drag=True,
        enable_circulation=True,
        enable_torque=True,
        enable_gravity=True
    )

    # Theoretical terminal speed from drag-buoyancy balance
    # C_D at alpha = pi/2 is C_D0 + C_D1 = 1.4 + 1.0 = 2.4
    c_d_broadside = coeffs.C_D0 + coeffs.C_D1
    delta_rho = plate.rho_s - fluid.rho_f
    buoyant_force = delta_rho * plate.area * fluid.g
    u_terminal_expected = math.sqrt(2.0 * buoyant_force / (fluid.rho_f * c_d_broadside * plate.L))

    # Integrate long enough to achieve steady state
    state0 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    t_span = (0.0, 10.0)

    sol = solve_ivp(
        fun=model.rhs,
        t_span=t_span,
        y0=state0,
        method="DOP853",
        rtol=1e-9,
        atol=1e-11
    )
    assert sol.success

    v_end = sol.y[4, -1]
    u_end = sol.y[3, -1]
    omega_end = sol.y[5, -1]

    # Broadside descent: u=0, omega=0, v is downward (< 0)
    assert math.isclose(u_end, 0.0, abs_tol=1e-9)
    assert math.isclose(omega_end, 0.0, abs_tol=1e-9)

    speed_sim = abs(v_end)
    rel_error = abs(speed_sim - u_terminal_expected) / u_terminal_expected

    print(f"\nTerminal velocity: Expected = {u_terminal_expected:.5f} m/s, Simulated = {speed_sim:.5f} m/s (rel error = {rel_error*100:.3f}%)")
    assert rel_error < 0.02, f"Terminal speed error {rel_error*100:.2f}% exceeds 2% threshold"
