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
        raise FileNotFoundError(f"Required benchmark file {csv_file} does not exist. Run scripts/run_mu1_sensitivity.py first.")
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
        raise FileNotFoundError(f"Required benchmark file {csv_file} does not exist. Run scripts/run_coin_regimes.py first.")
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


def test_edge_on_release_not_steady():
    """Verify that theta0 = 90 deg + 1e-3 rad is never classified as 'steady'."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024
    for rho_s, h in [(1180.0, 0.0012), (2700.0, 0.0015), (8500.0, 0.0035)]:
        plate = PlateParams("edge_test", rho_s, L, h)
        u0_scale = math.sqrt(max(0.0, (rho_s / cfg.fluid.rho_f) - 1.0) * cfg.fluid.g * plate.b)
        tau_0 = plate.a / u0_scale if u0_scale > 1e-6 else 0.05
        num = NumericsParams(H_fall_factor=80.0, perturbation_rad=0.001)
        res = simulate_drop(plate, cfg.fluid, cfg.coefficients, num, theta0=math.radians(90.0))
        reg, met = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, cfg.regime_classifier, tau_0=tau_0)
        assert reg != "steady", f"Expected edge-on release with 1e-3 rad perturbation not to be steady, got {reg}"


def test_perturbation_applied_at_all_angles():
    """Verify perturbation_rad is applied at 90 and 180 deg, and zero perturbation triggers symmetric warning."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    plate = PlateParams("p_test", 2700.0, 0.024, 0.0015)

    # 1. Perturbation at 90 deg
    num_pert = NumericsParams(H_fall_factor=40.0, perturbation_rad=0.001)
    res_90 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num_pert, theta0=math.radians(90.0))
    assert math.isclose(res_90.actual_theta0_rad, math.radians(90.0) + 0.001, rel_tol=1e-7)
    assert not res_90.symmetric_start

    # 2. Perturbation at 180 deg
    res_180 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num_pert, theta0=math.radians(180.0))
    assert math.isclose(res_180.actual_theta0_rad, math.radians(180.0) + 0.001, rel_tol=1e-7)
    assert not res_180.symmetric_start

    # 3. Zero perturbation at 90 and 180 deg warns and flags symmetric_start = True
    num_zero = NumericsParams(H_fall_factor=40.0, perturbation_rad=0.0)
    with pytest.warns(UserWarning, match="Symmetrically exact release"):
        res_sym90 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num_zero, theta0=math.radians(90.0))
        assert res_sym90.symmetric_start

    with pytest.warns(UserWarning, match="Symmetrically exact release"):
        res_sym180 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num_zero, theta0=math.radians(180.0))
        assert res_sym180.symmetric_start


def test_horizon_doubling_extended_points():
    """Verify N=80 vs N=160 horizon doubling invariance across tungsten, I*=2.0, 3.0, 3.5,
    and boundary points 1.2, 1.25, 1.3, 1.5 at delta_theta = 1e-3 and 1e-2.
    Also explicitly assert that I* >= 3.0 points classify as fluttering.
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024
    test_i_stars = [1.20, 1.25, 1.30, 1.50, 2.00, 2.41, 3.00, 3.50]

    for dt_val in [0.001, 0.01]:
        for i_s in test_i_stars:
            aspect = float(np.clip(0.045 + 0.05 * np.sqrt(i_s), 0.035, 0.25))
            aspect = max(aspect, i_s / 20.0)
            h = L * aspect
            rho_s = float(i_s * cfg.fluid.rho_f / aspect)
            plate = PlateParams(f"conv_{i_s}", rho_s, L, h)
            u0_scale = math.sqrt(max(0.0, (rho_s / cfg.fluid.rho_f) - 1.0) * cfg.fluid.g * plate.b)
            tau_0 = plate.a / u0_scale if u0_scale > 1e-6 else 0.05

            num80 = NumericsParams(H_fall_factor=80.0, min_horizon_time_units=80.0, perturbation_rad=dt_val)
            num160 = NumericsParams(H_fall_factor=160.0, min_horizon_time_units=160.0, perturbation_rad=dt_val)

            r80 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num80, theta0=np.radians(20.0))
            r160 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num160, theta0=np.radians(20.0))

            reg80, _ = classify_regime(r80.t, r80.Y, r80.theta, r80.omega, r80.H_fall, cfg.regime_classifier, tau_0=tau_0)
            reg160, _ = classify_regime(r160.t, r160.Y, r160.theta, r160.omega, r160.H_fall, cfg.regime_classifier, tau_0=tau_0)

            assert reg80 == reg160, f"Horizon doubling mismatch for I*={i_s} at dt={dt_val}: {reg80} vs {reg160}"
            if i_s >= 3.00:
                assert reg80 == "fluttering", f"Expected fluttering for I*={i_s} >= 3.0, got {reg80}"


def test_angle_180_parity():
    """Verify theta0 and theta0 + 180 deg parity over short horizon (approx 10 tau0) within tolerance."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    plate = PlateParams("sym_test", 2700.0, 0.024, 0.0015)
    u0_scale = math.sqrt(max(0.0, (plate.rho_s / cfg.fluid.rho_f) - 1.0) * cfg.fluid.g * plate.b)
    tau_0 = plate.a / u0_scale
    t_10 = 10.0 * tau_0

    num = NumericsParams(H_fall_factor=40.0, perturbation_rad=0.001)
    res1 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num, theta0=math.radians(20.0))
    res2 = simulate_drop(plate, cfg.fluid, cfg.coefficients, num, theta0=math.radians(200.0))

    m1 = res1.t <= t_10
    m2 = res2.t <= t_10
    max_y_diff = float(np.max(np.abs(res1.Y[m1] - res2.Y[m2])))
    assert max_y_diff < 1e-4, f"180-degree parity trajectory deviation {max_y_diff:.2e} m exceeds tolerance 1e-4 m"


def test_chord_scale_invariance():
    """Verify that regime classifications are identical across chord lengths at fixed I* and h/L."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    i_s = 1.40
    aspect = 0.05
    rho_s = i_s * cfg.fluid.rho_f / aspect

    detected_regimes = []
    for L in [0.008, 0.012, 0.016, 0.024]:
        h = L * aspect
        plate = PlateParams(f"scale_L{int(L*1000)}", rho_s, L, h)
        u0_scale = math.sqrt(max(0.0, (rho_s / cfg.fluid.rho_f) - 1.0) * cfg.fluid.g * plate.b)
        tau_0 = plate.a / u0_scale
        num = NumericsParams(H_fall_factor=80.0, min_horizon_time_units=80.0, perturbation_rad=0.001)
        res = simulate_drop(plate, cfg.fluid, cfg.coefficients, num, theta0=math.radians(20.0))
        reg, _ = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, cfg.regime_classifier, tau_0=tau_0)
        detected_regimes.append(reg)

    assert len(set(detected_regimes)) == 1, f"Expected scale invariance across chords, got {detected_regimes}"
