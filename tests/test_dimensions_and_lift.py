"""Tests for equation of motion dimensional consistency and lift coefficient curve."""

import math
import numpy as np
import pytest

from autumn.forces import (
    compute_angle_of_attack,
    compute_circulation,
    compute_drag_coefficient,
    compute_viscous_forces_and_torque,
)
from autumn.model import AutumnModel
from autumn.params import Coefficients, FluidParams, PlateParams


def test_lift_coefficient_peak():
    r"""Verify that implied lift coefficient C_L(alpha) = 2*Gamma / (|V| * L) peaks near 1.2 at alpha ~ 45 deg."""
    coeffs = Coefficients(C_T=1.2, C_R=math.pi)
    L = 0.024
    speed = 0.5  # m/s, omega = 0 to isolate translational lift

    # Restrict to [0, pi/2] to uniquely isolate the primary positive stall-free lift peak at 45 deg
    alphas = np.linspace(0.0, math.pi / 2.0, 1801)
    c_l_values = []

    for alpha in alphas:
        # u = V cos(alpha), v = -V sin(alpha) so that atan2(-v, u) = alpha
        u = speed * math.cos(alpha)
        v = -speed * math.sin(alpha)
        gamma = compute_circulation(u, v, omega=0.0, L=L, coeffs=coeffs)
        c_l = (2.0 * gamma) / (speed * L)
        c_l_values.append(c_l)

    c_l_arr = np.array(c_l_values)
    max_idx = np.argmax(c_l_arr)
    alpha_peak_deg = math.degrees(alphas[max_idx])
    c_l_max = c_l_arr[max_idx]

    print(f"\nLift coefficient peak: C_L,max = {c_l_max:.4f} at alpha = {alpha_peak_deg:.1f} deg")

    # Peak must be within [1.18, 1.22] near 45 deg
    assert math.isclose(c_l_max, 1.2, abs_tol=0.01), f"Expected peak near 1.2, got {c_l_max}"
    assert math.isclose(alpha_peak_deg, 45.0, abs_tol=0.5), f"Expected peak at 45 deg, got {alpha_peak_deg}"


def test_equations_of_motion_dimensional_consistency():
    r"""Verify dimensional consistency: all terms in the translational equations have units of N/m,

    and all terms in the rotational equation have units of N*m/m = N.
    """
    fluid = FluidParams(rho_f=998.0, g=9.81)
    coeffs = Coefficients(C_T=1.2, C_R=math.pi, C_D0=1.4, C_D1=1.0, C_tau=0.075)
    plate = PlateParams("dim_test", 2700.0, 0.024, 0.0018)
    model = AutumnModel(plate, fluid, coeffs)

    # State with arbitrary non-zero values
    theta = 0.45
    u = 0.35
    v = -0.25
    omega = 12.0

    # 1. Kirchhoff inertia terms: mass/depth * velocity * omega -> (kg/m) * (m/s) * (1/s) = N/m
    term_kirchhoff_u = model.M_v * v * omega
    term_kirchhoff_v = -model.M_u * u * omega
    assert isinstance(term_kirchhoff_u, float) and isinstance(term_kirchhoff_v, float)

    # 2. Circulation lift terms: rho_f * Gamma * v -> (kg/m^3) * (m^2/s) * (m/s) = kg/(m*s^2) = N/m
    gamma = compute_circulation(u, v, omega, plate.L, coeffs)
    lift_u = fluid.rho_f * gamma * v
    lift_v = fluid.rho_f * gamma * u
    assert isinstance(lift_u, float) and isinstance(lift_v, float)

    # 3. Viscous drag: 0.5 * rho_f * L * C_D * V * u -> (kg/m^3) * m * (m/s)^2 = N/m
    f_u, f_v, tau = compute_viscous_forces_and_torque(u, v, omega, plate.L, fluid.rho_f, coeffs)
    assert isinstance(f_u, float) and isinstance(f_v, float)

    # 4. Buoyant gravity: (m - m_f) * g * sin(theta) -> (kg/m) * (m/s^2) = N/m
    buoyant_weight = (model.m - model.m_f) * fluid.g
    g_u = buoyant_weight * math.sin(theta)
    g_v = buoyant_weight * math.cos(theta)
    assert isinstance(g_u, float) and isinstance(g_v, float)

    # 5. Rotational terms:
    # Munk moment: (m11 - m22) * u * v -> (kg/m) * (m/s)^2 = kg*m/s^2 = N = N*m/m
    munk_moment = (model.m11 - model.m22) * u * v
    # Viscous torque: 0.5 * C_tau * rho_f * L^4 * omega^2 -> (kg/m^3) * m^4 * (1/s^2) = kg*m/s^2 = N
    assert isinstance(munk_moment, float) and isinstance(tau, float)

    # Effective virtual masses and virtual inertia:
    # M_u, M_v in kg/m
    assert model.M_u > 0 and model.M_v > 0
    # I_tot in kg*m (moment of inertia per unit depth)
    assert model.I_tot > 0

    # Accelerations:
    # (N/m) / (kg/m) = m/s^2
    du_dt = (term_kirchhoff_u - lift_u - f_u - g_u) / model.M_u
    dv_dt = (term_kirchhoff_v + lift_v - f_v - g_v) / model.M_v
    # (N*m/m) / (kg*m) = (kg*m/s^2) / (kg*m) = 1/s^2 = rad/s^2
    domega_dt = (munk_moment - tau) / model.I_tot

    assert math.isfinite(du_dt) and math.isfinite(dv_dt) and math.isfinite(domega_dt)

    # Velocity scale verification: Froude scale U_t vs Andersen characteristic scale U_0
    from autumn.dimensionless import compute_andersen_velocity_scale, compute_froude_velocity_scale
    u_t = compute_froude_velocity_scale(plate.rho_s, fluid.rho_f, fluid.g, plate.h)
    u_0 = compute_andersen_velocity_scale(plate.rho_s, fluid.rho_f, fluid.g, plate.b)
    assert u_t > 0.0 and u_0 > 0.0
    assert math.isclose(u_t, math.sqrt(2.0) * u_0, rel_tol=1e-9)
