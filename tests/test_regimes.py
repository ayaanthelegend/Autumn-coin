"""Acceptance Test 6: Regime ordering across I*, detection of regimes, and threshold sensitivity.

Thresholds and benchmark cases are loaded dynamically from results/mu1_sensitivity.csv
and results/coin_regimes.csv, per Amendment 1.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pytest

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.params import Coefficients, FluidParams, NumericsParams, PlateParams, RegimeClassifierParams, SimulationConfig

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"


def load_sensitivity_istar_c(mu_1: float = 0.20, theta0_deg: float = 20.0) -> float:
    """Load critical I*_c from results/mu1_sensitivity.csv."""
    csv_file = RESULTS_DIR / "mu1_sensitivity.csv"
    if not csv_file.exists():
        pytest.skip("results/mu1_sensitivity.csv not yet generated.")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if abs(float(row["mu_1"]) - mu_1) < 1e-4 and abs(float(row["theta0_deg"]) - theta0_deg) < 1e-4:
                return float(row["I_star_c"])
    raise ValueError(f"Could not find row for mu_1={mu_1}, theta0={theta0_deg} in {csv_file}")


def load_coin_regime_row(coin_id: str, theta0_deg: float = 5.0, mu_1: float = 0.20) -> Dict[str, str]:
    """Load row for given coin from results/coin_regimes.csv."""
    csv_file = RESULTS_DIR / "coin_regimes.csv"
    if not csv_file.exists():
        pytest.skip("results/coin_regimes.csv not yet generated.")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["coin"] == coin_id and abs(float(row["theta0_deg"]) - theta0_deg) < 1e-4 and abs(float(row["mu_1"]) - mu_1) < 1e-4:
                return row
    raise ValueError(f"Could not find row for coin={coin_id}, theta0={theta0_deg}, mu_1={mu_1} in {csv_file}")


def test_regimes_detected_and_steady_not_reached():
    r"""Verify detection of fluttering, tumbling, and mixed regimes from coin catalog,
    and assert that steady descent is NOT reached under real perturbation (Amendment 1).
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024

    # 1. Steady check under real perturbation (Amendment 1)
    # The steady test must NOT use theta0 = 0.0 exactly; use a real perturbation.
    # If no genuinely steady case exists, mark steady as not reached with a reason.
    p_low_i = PlateParams("low_i_perturbed", 1180.0, L, 0.0012)
    r_perturbed = simulate_drop(
        p_low_i,
        cfg.fluid,
        cfg.coefficients,
        cfg.numerics,
        theta0=np.radians(5.0)
    )
    reg_pert, met_pert = classify_regime(
        r_perturbed.t, r_perturbed.Y, r_perturbed.theta, r_perturbed.omega, r_perturbed.H_fall, cfg.regime_classifier
    )
    # Under real perturbation (5 deg), plate flutters, it does NOT settle to steady
    assert reg_pert != "steady", f"Expected real perturbation to prevent steady descent, got {reg_pert}"
    assert met_pert["theta_range_deg"] >= 2.0, f"Expected oscillatory flutter (ptp >= 2 deg), got {met_pert['theta_range_deg']:.2f}"
    steady_status = {
        "reached": False,
        "reason": "broadside descent is an unstable equilibrium that only persists under mathematically exact zero perturbation (theta0=0.0); any physical perturbation induces flutter"
    }
    assert not steady_status["reached"]

    # 2. Fluttering: verified from coin_regimes.csv
    row_flutter = load_coin_regime_row("design_aluminium_24x1.5", theta0_deg=5.0, mu_1=0.20)
    assert row_flutter["regime"] == "fluttering"
    p_flutter = PlateParams("design_aluminium_24x1.5", 2700.0, 0.024, 0.0015)
    r_flutter = simulate_drop(p_flutter, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(5.0))
    reg_f, met_f = classify_regime(r_flutter.t, r_flutter.Y, r_flutter.theta, r_flutter.omega, r_flutter.H_fall, cfg.regime_classifier)
    assert reg_f == "fluttering"
    assert met_f["n_flips"] == 0

    # 3. Tumbling: verified from coin_regimes.csv
    row_tumble = load_coin_regime_row("design_brass_24x3.5", theta0_deg=5.0, mu_1=0.20)
    assert row_tumble["regime"] == "tumbling"
    p_tumble = PlateParams("design_brass_24x3.5", 8500.0, 0.024, 0.0035)
    r_tumble = simulate_drop(p_tumble, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(5.0))
    reg_t, met_t = classify_regime(r_tumble.t, r_tumble.Y, r_tumble.theta, r_tumble.omega, r_tumble.H_fall, cfg.regime_classifier)
    assert reg_t == "tumbling"
    assert met_t["n_flips"] >= 2

    # 4. Mixed: verified from coin_regimes.csv
    row_mixed = load_coin_regime_row("design_steel_24x4.5", theta0_deg=5.0, mu_1=0.20)
    assert row_mixed["regime"] == "mixed"
    p_mixed = PlateParams("design_steel_24x4.5", 7850.0, 0.024, 0.0045)
    r_mixed = simulate_drop(p_mixed, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(5.0))
    reg_m, met_m = classify_regime(r_mixed.t, r_mixed.Y, r_mixed.theta, r_mixed.omega, r_mixed.H_fall, cfg.regime_classifier)
    assert reg_m == "mixed"


def test_regime_ordering_transition():
    r"""Acceptance Test 6:
    Verify that flutter transitions to tumbling/mixed as I* crosses the dynamically
    bisected critical threshold I*_c loaded from results/mu1_sensitivity.csv.
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024
    h = 0.0018

    # Load critical threshold for baseline mu_1 = 0.20, theta0 = 20 deg
    i_star_c = load_sensitivity_istar_c(mu_1=0.20, theta0_deg=20.0)
    assert 1.10 <= i_star_c <= 1.30, f"Critical I*_c = {i_star_c} outside Andersen literature band [1.10, 1.30]"

    # Sub-critical test (below threshold): must flutter
    i_sub = round(i_star_c - 0.25, 3)
    rho_sub = i_sub * cfg.fluid.rho_f * L / h
    p_sub = PlateParams(f"sub_{i_sub}", rho_sub, L, h)
    r_sub = simulate_drop(p_sub, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    reg_sub, _ = classify_regime(r_sub.t, r_sub.Y, r_sub.theta, r_sub.omega, r_sub.H_fall, cfg.regime_classifier)
    assert reg_sub == "fluttering", f"Expected fluttering below I*_c, got {reg_sub}"

    # Super-critical test (above threshold): must tumble or mixed
    i_super = round(i_star_c + 0.25, 3)
    rho_super = i_super * cfg.fluid.rho_f * L / h
    p_super = PlateParams(f"super_{i_super}", rho_super, L, h)
    r_super = simulate_drop(p_super, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    reg_super, _ = classify_regime(r_super.t, r_super.Y, r_super.theta, r_super.omega, r_super.H_fall, cfg.regime_classifier)
    assert reg_super in ("tumbling", "mixed"), f"Expected tumbling or mixed above I*_c, got {reg_super}"


def test_regime_threshold_sensitivity():
    """Verify that regime classifications are robust to +/- 20% variations in thresholds."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")

    # Load benchmark cases from coin_regimes.csv
    row_f = load_coin_regime_row("design_aluminium_24x1.5", theta0_deg=5.0, mu_1=0.20)
    row_t = load_coin_regime_row("design_brass_24x3.5", theta0_deg=5.0, mu_1=0.20)
    row_m = load_coin_regime_row("design_steel_24x4.5", theta0_deg=5.0, mu_1=0.20)

    p_f = PlateParams("f", 2700.0, 0.024, 0.0015)
    p_t = PlateParams("t", 8500.0, 0.024, 0.0035)
    p_m = PlateParams("m", 7850.0, 0.024, 0.0045)

    r_f = simulate_drop(p_f, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(5.0))
    r_t = simulate_drop(p_t, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(5.0))
    r_m = simulate_drop(p_m, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(5.0))

    base_params = cfg.regime_classifier

    for factor in [0.8, 1.0, 1.2]:
        perturbed_params = RegimeClassifierParams(
            transient_fraction=base_params.transient_fraction,
            transient_t_min=base_params.transient_t_min,
            theta_std_steady_deg=base_params.theta_std_steady_deg * factor,
            theta_ptp_steady_deg=base_params.theta_ptp_steady_deg * factor,
            theta_ptp_flutter_max_deg=base_params.theta_ptp_flutter_max_deg * factor,
            min_flips_tumble=base_params.min_flips_tumble,
            max_reversal_tumble_deg=base_params.max_reversal_tumble_deg * factor,
            min_spin_ratio_tumble=base_params.min_spin_ratio_tumble * factor,
        )
        reg_f, _ = classify_regime(r_f.t, r_f.Y, r_f.theta, r_f.omega, r_f.H_fall, perturbed_params)
        reg_t, _ = classify_regime(r_t.t, r_t.Y, r_t.theta, r_t.omega, r_t.H_fall, perturbed_params)
        reg_m, _ = classify_regime(r_m.t, r_m.Y, r_m.theta, r_m.omega, r_m.H_fall, perturbed_params)

        assert reg_f == "fluttering", f"Fluttering classification flipped to {reg_f} at factor {factor}"
        assert reg_t == "tumbling", f"Tumbling classification flipped to {reg_t} at factor {factor}"
        assert reg_m == "mixed", f"Mixed classification flipped to {reg_m} at factor {factor}"
