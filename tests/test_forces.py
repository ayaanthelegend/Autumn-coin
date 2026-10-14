"""Acceptance Tests 2 and 4: Conservation laws with no forces, and symmetry/sign check."""

import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from autumn.model import AutumnModel
from autumn.params import Coefficients, FluidParams, PlateParams


def test_no_forces_kirchhoff_conservation():
    """Acceptance Test 2 (Revised per user amendment):
    
    With drag, circulation, torque, and gravity all off:
    - Total kinetic energy T is constant to < 1e-8.
    - Lab-frame linear momentum P_lab is constant to < 1e-8.
    - Special case for circle (a == b): body-frame u, v, omega are individually constant.
    """
    fluid = FluidParams(rho_f=998.0)
    coeffs = Coefficients()
    plate = PlateParams(
        name="test_ellipse",
        rho_s=2700.0,
        L=0.024,
        h=0.0018
    )

    model = AutumnModel(
        plate=plate,
        fluid=fluid,
        coeffs=coeffs,
        enable_drag=False,
        enable_circulation=False,
        enable_torque=False,
        enable_gravity=False
    )

    # Initial condition with non-zero translation and tumbling
    state0 = [0.0, 0.0, 0.3, 0.5, -0.2, 5.0]
    t_span = (0.0, 2.0)
    t_eval = np.linspace(0.0, 2.0, 201)

    sol = solve_ivp(
        fun=model.rhs,
        t_span=t_span,
        y0=state0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12
    )
    assert sol.success

    T0 = model.kinetic_energy(state0)
    px0, py0 = model.lab_linear_momentum(state0)

    for i in range(len(sol.t)):
        state = sol.y[:, i]
        T_curr = model.kinetic_energy(state)
        px_curr, py_curr = model.lab_linear_momentum(state)

        # Kinetic energy relative conservation
        rel_diff_T = abs(T_curr - T0) / T0
        assert rel_diff_T < 1e-8, f"Kinetic energy drift at t={sol.t[i]}: {rel_diff_T}"

        # Lab frame linear momentum conservation
        p_mag0 = math.hypot(px0, py0)
        diff_px = abs(px_curr - px0) / p_mag0
        diff_py = abs(py_curr - py0) / p_mag0
        assert diff_px < 1e-8, f"Lab Px drift at t={sol.t[i]}: {diff_px}"
        assert diff_py < 1e-8, f"Lab Py drift at t={sol.t[i]}: {diff_py}"

    # For non-circular plate, verify that body-frame u, v and omega DO oscillate (Kirchhoff effect)
    u_vals = sol.y[3, :]
    v_vals = sol.y[4, :]
    omega_vals = sol.y[5, :]
    assert np.ptp(u_vals) > 1e-4, "Body u should not be constant when m11 != m22"
    assert np.ptp(omega_vals) > 1e-4, "Omega should not be constant when m11 != m22"


def test_no_forces_circular_plate_constant_velocity():
    """Acceptance Test 2 (Circular limit):
    
    For a == b (circle, m11 == m22), in the absence of forces:
    - Angular velocity omega is constant.
    - Lab-frame velocity vector (dX/dt, dY/dt) is constant.
    - Body speed sqrt(u^2 + v^2) is constant.
    - When omega == 0, body velocity components (u, v) are also individually constant.
    """
    fluid = FluidParams(rho_f=998.0)
    coeffs = Coefficients()
    plate = PlateParams(
        name="test_circle",
        rho_s=2700.0,
        L=0.020,
        h=0.020  # a == b -> m11 == m22
    )

    model = AutumnModel(
        plate=plate,
        fluid=fluid,
        coeffs=coeffs,
        enable_drag=False,
        enable_circulation=False,
        enable_torque=False,
        enable_gravity=False
    )

    # Spinning circle
    state0 = [0.0, 0.0, 0.5, 0.4, -0.3, 2.0]
    t_span = (0.0, 1.0)
    t_eval = np.linspace(0.0, 1.0, 101)
    sol = solve_ivp(
        fun=model.rhs,
        t_span=t_span,
        y0=state0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12
    )
    assert sol.success

    # Check that omega is constant
    omega_vals = sol.y[5, :]
    assert np.allclose(omega_vals, state0[5], atol=1e-9)

    # Check that speed is constant
    speed_vals = np.hypot(sol.y[3, :], sol.y[4, :])
    assert np.allclose(speed_vals, math.hypot(state0[3], state0[4]), atol=1e-9)

    # Check that lab velocity vector (dX/dt, dY/dt) is constant
    th = sol.y[2, :]
    u = sol.y[3, :]
    v = sol.y[4, :]
    vx_lab = u * np.cos(th) - v * np.sin(th)
    vy_lab = u * np.sin(th) + v * np.cos(th)
    assert np.allclose(vx_lab, vx_lab[0], atol=1e-9)
    assert np.allclose(vy_lab, vy_lab[0], atol=1e-9)

    # When omega == 0, body frame does not rotate, so u and v are also constant
    state0_norot = [0.0, 0.0, 0.2, 0.4, -0.3, 0.0]
    sol_norot = solve_ivp(
        fun=model.rhs,
        t_span=t_span,
        y0=state0_norot,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12
    )
    assert sol_norot.success
    state_end = sol_norot.y[:, -1]
    assert math.isclose(state_end[3], state0_norot[3], abs_tol=1e-9)
    assert math.isclose(state_end[4], state0_norot[4], abs_tol=1e-9)
    assert math.isclose(state_end[5], 0.0, abs_tol=1e-9)



def test_sign_check_and_symmetry():
    """Acceptance Test 4:
    
    A plate released with theta = 0 and zero velocity falls straight down in the absence
    of perturbations, never drifting sideways by more than 1e-6 L when noise is off.
    """
    fluid = FluidParams(rho_f=998.0)
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

    # Exactly zero initial velocity, angle theta = 0, zero noise
    state0 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    t_span = (0.0, 3.0)
    t_eval = np.linspace(0.0, 3.0, 100)

    sol = solve_ivp(
        fun=model.rhs,
        t_span=t_span,
        y0=state0,
        t_eval=t_eval,
        method="DOP853",
        rtol=1e-9,
        atol=1e-11
    )
    assert sol.success

    x_vals = sol.y[0, :]
    y_vals = sol.y[1, :]
    theta_vals = sol.y[2, :]
    u_vals = sol.y[3, :]
    v_vals = sol.y[4, :]

    # Lateral drift must be strictly <= 1e-6 * L
    max_drift = np.max(np.abs(x_vals))
    assert max_drift <= 1e-6 * plate.L, f"Lateral drift exceeded: max|X| = {max_drift} > {1e-6 * plate.L}"

    # Angle must remain 0
    assert np.max(np.abs(theta_vals)) <= 1e-9

    # u velocity must remain 0
    assert np.max(np.abs(u_vals)) <= 1e-9

    # Plate must fall downward: Y(t) must decrease, v < 0
    assert y_vals[-1] < -0.05, f"Plate did not fall down: Y_end = {y_vals[-1]}"
    assert v_vals[-1] < 0.0, f"Vertical velocity should be negative, got {v_vals[-1]}"
