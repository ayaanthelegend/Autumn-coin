"""Acceptance Tests 7 and 8: Numerical convergence and byte-identical reproducibility."""

import filecmp
import math
from pathlib import Path
import numpy as np
import pytest

from autumn.integrate import simulate_drop
from autumn.params import NumericsParams, PlateParams, SimulationConfig
from autumn.plotting import save_figure_and_csv
import matplotlib.pyplot as plt


def test_numerical_convergence_tolerance_tightening():
    r"""Acceptance Test 7 (with user amendment 5):
    
    Tightening tolerances by 10x (rtol 1e-9 -> 1e-10, atol 1e-11 -> 1e-12)
    changes the landing position X of a fluttering non-chaotic drop by less than
    0.1 percent of chord L (|Delta X| / L < 1e-3).
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.020
    h = 0.0005
    rho_s = 5.0 * cfg.fluid.rho_f * L / h
    plate = PlateParams("flutter_conv_test", rho_s, L, h)

    # 1. Standard tolerance run
    num_standard = NumericsParams(
        integrator="DOP853",
        rtol=1e-9,
        atol=1e-11,
        dt_out=0.001
    )
    res_std = simulate_drop(
        plate=plate,
        fluid=cfg.fluid,
        coeffs=cfg.coefficients,
        numerics=num_standard,
        theta0=np.radians(20.0)
    )

    # 2. 10x tightened tolerance run
    num_tight = NumericsParams(
        integrator="DOP853",
        rtol=1e-10,
        atol=1e-12,
        dt_out=0.001
    )
    res_tight = simulate_drop(
        plate=plate,
        fluid=cfg.fluid,
        coeffs=cfg.coefficients,
        numerics=num_tight,
        theta0=np.radians(20.0)
    )

    delta_X = abs(res_tight.X[-1] - res_std.X[-1])
    rel_change_L = delta_X / plate.L

    print(f"\nConvergence check: |Delta X| = {delta_X*1000:.6f} mm, |Delta X| / L = {rel_change_L*100:.6f}%")
    assert rel_change_L < 1e-3, f"Tolerance tightening changed landing X by {rel_change_L*100:.4f}% of L (> 0.1%)"


def test_byte_identical_reproducibility(tmp_path: Path):
    """Acceptance Test 8: Same seed and initial parameters produce byte-identical trajectory CSVs."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    plate = PlateParams("repro_test", 1200.0, 0.020, 0.002)

    # Seeded initial condition
    rng1 = np.random.default_rng(seed=12345)
    pert_theta = rng1.normal(0.0, np.radians(0.5))
    pert_u = rng1.normal(0.0, 1e-4)

    rng2 = np.random.default_rng(seed=12345)
    pert_theta2 = rng2.normal(0.0, np.radians(0.5))
    pert_u2 = rng2.normal(0.0, 1e-4)

    res1 = simulate_drop(
        plate=plate,
        fluid=cfg.fluid,
        coeffs=cfg.coefficients,
        numerics=cfg.numerics,
        theta0=np.radians(5.0) + pert_theta,
        u0=pert_u
    )

    res2 = simulate_drop(
        plate=plate,
        fluid=cfg.fluid,
        coeffs=cfg.coefficients,
        numerics=cfg.numerics,
        theta0=np.radians(5.0) + pert_theta2,
        u0=pert_u2
    )

    csv1_path = tmp_path / "run1.csv"
    csv2_path = tmp_path / "run2.csv"

    csv_headers = ["t", "X", "Y", "theta", "u", "v", "omega", "v_X", "v_Y", "speed"]
    data1 = np.column_stack([res1.t, res1.X, res1.Y, res1.theta, res1.u, res1.v, res1.omega, res1.v_X, res1.v_Y, res1.speed])
    data2 = np.column_stack([res2.t, res2.X, res2.Y, res2.theta, res2.u, res2.v, res2.omega, res2.v_X, res2.v_Y, res2.speed])

    import csv
    with open(csv1_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(csv_headers)
        w.writerows(data1)

    with open(csv2_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(csv_headers)
        w.writerows(data2)

    assert filecmp.cmp(csv1_path, csv2_path, shallow=False), "CSVs from identical seeds were not byte-identical!"
