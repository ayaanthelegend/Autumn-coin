"""Reference Reproduction Acceptance Test.

Verifies that the dimensional Autumn model converges to the dimensionless
Andersen-Pesavento-Wang reference card formulation in the thin plate limit (h/L = 0.01)
across all three canonical dynamical regimes at dimensionless time t* = 50:
  1. I* = 1.1: Fluttering -> (x/a, y/a) ~= (7.3, -33.0)
  2. I* = 1.4: Tumbling   -> (x/a, y/a) ~= (-26.1, -24.3)
  3. I* = 1.6: Mixture    -> (x/a, y/a) ~= (6.1, -29.3)

Also verifies that setting mu_1 = 0.01 causes I* = 1.1 to tumble instead of flutter.
Reference literature: Andersen, Pesavento & Wang (2005b) as used in the ondrej-cloud
implementation (equation numbers unchecked in primary text).
"""

import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from autumn.model import AutumnModel
from autumn.params import Coefficients, FluidParams, PlateParams


def run_dimensionless_reference_model(I_star: float, t_end: float = 50.0):
    """Standalone self-contained reference dimensionless ODE solver."""
    C_T = 1.2
    C_R = math.pi
    A = 1.4
    B = 1.0
    mu1 = 0.2
    mu2 = 0.2

    def rhs(t, y):
        x, y_pos, th, vx, vy, w = y
        V_sq = vx * vx + vy * vy
        V = math.sqrt(V_sq)
        if V < 1e-9:
            G = (2.0 / math.pi) * (C_R * w)
            F_mag = 0.0
        else:
            G = (2.0 / math.pi) * (-C_T * vx * vy / V + C_R * w)
            F_mag = (1.0 / math.pi) * (A - B * (vx * vx - vy * vy) / V_sq) * V

        Fx = F_mag * vx
        Fy = F_mag * vy

        dvx = ((I_star + 1.0) * w * vy - G * vy - math.sin(th) - Fx) / I_star
        dvy = (-I_star * w * vx + G * vx - math.cos(th) - Fy) / (I_star + 1.0)
        dw = (-vx * vy - (mu1 + mu2 * abs(w)) * w) / (0.25 * (I_star + 0.5))
        dth = w
        dx = vx * math.cos(th) - vy * math.sin(th)
        dy = vx * math.sin(th) + vy * math.cos(th)
        return [dx, dy, dth, dvx, dvy, dw]

    # Initial state: [x, y, theta, vx, vy, omega] = [0, 0, 0.1, 0, -1, 0]
    y0 = [0.0, 0.0, 0.1, 0.0, -1.0, 0.0]
    sol = solve_ivp(rhs, (0.0, t_end), y0, method="DOP853", rtol=1e-10, atol=1e-12)
    return sol.y[0, -1], sol.y[1, -1], sol.y[2, -1], sol.y[5, -1]


def test_three_reference_regimes_reproduction():
    """Verify dimensional model reproduces the three canonical cases within 0.3 a."""
    rho_f = 998.0
    g = 9.81
    mu = 0.001
    L = 0.024
    a = L / 2.0
    h = 0.01 * L  # Thin plate limit h/L = 0.01
    b = h / 2.0

    fluid = FluidParams(rho_f=rho_f, g=g, mu=mu)
    coeffs = Coefficients(
        C_T=1.2,
        C_R=math.pi,
        C_D0=1.4,
        C_D1=1.0,
        mu_1=0.2,
        mu_2=0.2,
        C_tau=math.pi * 0.2 / 8.0
    )

    targets = [
        (1.1, 7.3, -33.0, "fluttering"),
        (1.4, -26.1, -24.3, "tumbling"),
        (1.6, 6.1, -29.3, "periodic mixture"),
    ]

    for I_val, x_ref_expected, y_ref_expected, regime_label in targets:
        # Reference dimensionless run
        x_ref, y_ref, th_ref, w_ref = run_dimensionless_reference_model(I_val, t_end=50.0)
        assert math.isclose(x_ref, x_ref_expected, abs_tol=0.2), f"Reference mismatch in x for I*={I_val}: {x_ref} vs {x_ref_expected}"
        assert math.isclose(y_ref, y_ref_expected, abs_tol=0.2), f"Reference mismatch in y for I*={I_val}: {y_ref} vs {y_ref_expected}"

        # Dimensional simulation
        rho_s = I_val * rho_f * L / h
        U = math.sqrt((rho_s / rho_f - 1.0) * g * b)
        t_dim_50 = 50.0 * (a / U)

        plate = PlateParams(f"plate_I_{I_val}", rho_s, L, h)
        model = AutumnModel(plate, fluid, coeffs)

        # Initial dimensional state: [X, Y, theta, u, v, omega] = [0, 0, 0.1 rad, 0, -U, 0]
        y0_dim = [0.0, 0.0, 0.1, 0.0, -U, 0.0]
        sol_dim = solve_ivp(model.rhs, (0.0, t_dim_50), y0_dim, method="DOP853", rtol=1e-10, atol=1e-12)

        x_dim_a = sol_dim.y[0, -1] / a
        y_dim_a = sol_dim.y[1, -1] / a

        err_x = abs(x_dim_a - x_ref_expected)
        err_y = abs(y_dim_a - y_ref_expected)

        print(f"I*={I_val:.1f} ({regime_label}): dimensional (X/a, Y/a)=({x_dim_a:.2f}, {y_dim_a:.2f}), err_x={err_x:.3f}, err_y={err_y:.3f}")

        assert err_x < 0.3, f"Dimensional X/a for I*={I_val} diverges from reference by {err_x:.3f} a (tolerance: 0.3 a)"
        assert err_y < 0.3, f"Dimensional Y/a for I*={I_val} diverges from reference by {err_y:.3f} a (tolerance: 0.3 a)"


def test_mu1_defect_regime_switch():
    """Assert that setting mu_1 = 0.01 gives a tumbling regime at I* = 1.1 instead of flutter."""
    rho_f = 998.0
    g = 9.81
    mu = 0.001
    L = 0.024
    a = L / 2.0
    h = 0.01 * L
    b = h / 2.0
    I_val = 1.1

    fluid = FluidParams(rho_f=rho_f, g=g, mu=mu)
    rho_s = I_val * rho_f * L / h
    U = math.sqrt((rho_s / rho_f - 1.0) * g * b)
    t_dim_50 = 50.0 * (a / U)
    plate = PlateParams("plate_I11", rho_s, L, h)

    # 1. Baseline mu_1 = 0.20 (fluttering, no full rotation)
    coeffs_baseline = Coefficients(C_T=1.2, C_R=math.pi, C_D0=1.4, C_D1=1.0, mu_1=0.2, mu_2=0.2, C_tau=math.pi * 0.2 / 8.0)
    model_baseline = AutumnModel(plate, fluid, coeffs_baseline)
    sol_base = solve_ivp(model_baseline.rhs, (0.0, t_dim_50), [0.0, 0.0, 0.1, 0.0, -U, 0.0], method="DOP853", rtol=1e-10, atol=1e-12)
    turns_base = abs(sol_base.y[2, -1] - sol_base.y[2, 0]) / (2.0 * math.pi)

    # 2. Defective tuned mu_1 = 0.01 (tumbles with continuous autorotation)
    coeffs_defective = Coefficients(C_T=1.2, C_R=math.pi, C_D0=1.4, C_D1=1.0, mu_1=0.01, mu_2=0.2, C_tau=math.pi * 0.2 / 8.0)
    model_defective = AutumnModel(plate, fluid, coeffs_defective)
    sol_defect = solve_ivp(model_defective.rhs, (0.0, t_dim_50), [0.0, 0.0, 0.1, 0.0, -U, 0.0], method="DOP853", rtol=1e-10, atol=1e-12)
    turns_defect = abs(sol_defect.y[2, -1] - sol_defect.y[2, 0]) / (2.0 * math.pi)

    print(f"I* = 1.1 rotation comparison: mu_1=0.20 -> {turns_base:.2f} turns; mu_1=0.01 -> {turns_defect:.2f} turns")

    # Baseline must not tumble (turns < 0.5)
    assert turns_base < 0.5, f"Baseline mu_1=0.20 should be fluttering, but had {turns_base:.2f} turns"
    # Defective tuned mu_1=0.01 must tumble (turns > 2.0)
    assert turns_defect >= 2.0, f"Defective mu_1=0.01 should tumble, but had only {turns_defect:.2f} turns"
    assert abs(sol_defect.y[0, -1] / a) > 20.0, "Tumbling plate should drift laterally by > 20 a"
