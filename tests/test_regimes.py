"""Acceptance Test 6: Regime ordering across I*, detection of all four regimes, and threshold sensitivity."""

import math
import numpy as np
import pytest

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.params import PlateParams, RegimeClassifierParams, SimulationConfig


def test_all_four_regimes_detected():
    r"""Verify that all four distinct regimes (steady, fluttering, tumbling, mixed)
    are cleanly identified by the classifier across the parameter space.
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024
    h = 0.0018

    # 1. Steady: broadside drop at low I* with theta0 = 0.0
    p_steady = PlateParams("steady_case", 1200.0, 0.020, 0.002)
    r_steady = simulate_drop(p_steady, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=0.0)
    reg_steady, met_steady = classify_regime(
        r_steady.t, r_steady.Y, r_steady.theta, r_steady.omega, r_steady.H_fall, cfg.regime_classifier
    )
    assert reg_steady == "steady", f"Expected steady, got {reg_steady}"

    # 2. Fluttering: moderate I* = 0.50, theta0 = 20 deg
    rho_flutter = 0.50 * cfg.fluid.rho_f * L / h
    p_flutter = PlateParams("flutter_case", rho_flutter, L, h)
    r_flutter = simulate_drop(p_flutter, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    reg_flutter, met_flutter = classify_regime(
        r_flutter.t, r_flutter.Y, r_flutter.theta, r_flutter.omega, r_flutter.H_fall, cfg.regime_classifier
    )
    assert reg_flutter == "fluttering", f"Expected fluttering, got {reg_flutter}"

    # 3. Tumbling: clean autorotation at I* = 1.40, theta0 = 20 deg (literature baseline mu_1 = 0.2)
    rho_tumble = 1.40 * cfg.fluid.rho_f * L / h
    p_tumble = PlateParams("tumble_case", rho_tumble, L, h)
    r_tumble = simulate_drop(p_tumble, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    reg_tumble, met_tumble = classify_regime(
        r_tumble.t, r_tumble.Y, r_tumble.theta, r_tumble.omega, r_tumble.H_fall, cfg.regime_classifier
    )
    assert reg_tumble == "tumbling", f"Expected tumbling, got {reg_tumble}"
    assert met_tumble["n_flips"] >= 2, f"Expected >= 2 flips in tumbling, got {met_tumble['n_flips']}"

    # 4. Mixed / Chaotic tumbling: large I* = 2.00, theta0 = 20 deg
    rho_mixed = 2.00 * cfg.fluid.rho_f * L / h
    p_mixed = PlateParams("mixed_case", rho_mixed, L, h)
    r_mixed = simulate_drop(p_mixed, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    reg_mixed, met_mixed = classify_regime(
        r_mixed.t, r_mixed.Y, r_mixed.theta, r_mixed.omega, r_mixed.H_fall, cfg.regime_classifier
    )
    assert reg_mixed == "mixed", f"Expected mixed, got {reg_mixed}"

    all_regimes = {reg_steady, reg_flutter, reg_tumble, reg_mixed}
    assert all_regimes == {"steady", "fluttering", "tumbling", "mixed"}


def test_regime_ordering_transition():
    r"""Acceptance Test 6:
    
    Verify that at small I*, the plate undergoes steady descent or low-amplitude flutter,
    and at large I*, the dynamics transition to unsteady oscillatory motion (fluttering or tumbling).
    Report the exact transition point and whether tumbling emerges with default coefficients.
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024
    h = 0.0018

    i_stars = [0.2, 0.5, 0.8, 1.4, 2.0, 3.5]
    regimes = []
    ranges = []

    for i_s in i_stars:
        rho_s = i_s * cfg.fluid.rho_f * L / h
        plate = PlateParams(f"test_i_{i_s}", rho_s, L, h)
        res = simulate_drop(plate, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
        reg, met = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, cfg.regime_classifier)
        regimes.append(reg)
        ranges.append(met["theta_range_rad"])

    print("\n--- Regime Ordering Test Results ---")
    for i_s, reg, rng in zip(i_stars, regimes, ranges):
        print(f"I* = {i_s:4.2f} -> {reg:10s} (theta_range = {rng:.3f} rad)")

    # 1. Smallest I* must be steady or fluttering
    assert regimes[0] in ("steady", "fluttering"), f"Smallest I*={i_stars[0]} should be steady or fluttering, got {regimes[0]}"

    # 2. Tumbling and mixed must emerge at higher I*
    assert "tumbling" in regimes, f"Clean tumbling should emerge at intermediate I*, got {regimes}"
    assert "mixed" in regimes, f"Mixed/chaotic motion should emerge at high I*, got {regimes}"


def test_regime_threshold_sensitivity():
    """Verify that all four regime classifications are robust to +/- 20% variations in thresholds."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.024
    h = 0.0018

    # Representative cases spanning all 4 regimes
    plate_steady = PlateParams("steady_case", 1200.0, 0.020, 0.002)
    plate_flutter = PlateParams("flutter_case", 0.68 * cfg.fluid.rho_f * L / h, L, h)
    plate_tumble = PlateParams("tumble_case", 1.35 * cfg.fluid.rho_f * L / h, L, h)
    plate_mixed = PlateParams("mixed_case", 2.00 * cfg.fluid.rho_f * L / h, L, h)

    res_steady = simulate_drop(plate_steady, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=0.0)
    res_flutter = simulate_drop(plate_flutter, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(15.0))
    res_tumble = simulate_drop(plate_tumble, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    res_mixed = simulate_drop(plate_mixed, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))

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
            min_reversal_mixed_deg=base_params.min_reversal_mixed_deg * factor,
            min_spin_ratio_tumble=base_params.min_spin_ratio_tumble * factor,
        )
        reg_s, _ = classify_regime(res_steady.t, res_steady.Y, res_steady.theta, res_steady.omega, res_steady.H_fall, perturbed_params)
        reg_f, _ = classify_regime(res_flutter.t, res_flutter.Y, res_flutter.theta, res_flutter.omega, res_flutter.H_fall, perturbed_params)
        reg_t, _ = classify_regime(res_tumble.t, res_tumble.Y, res_tumble.theta, res_tumble.omega, res_tumble.H_fall, perturbed_params)
        reg_m, _ = classify_regime(res_mixed.t, res_mixed.Y, res_mixed.theta, res_mixed.omega, res_mixed.H_fall, perturbed_params)

        assert reg_s == "steady", f"Steady classification flipped to {reg_s} at factor {factor}"
        assert reg_f == "fluttering", f"Fluttering classification flipped to {reg_f} at factor {factor}"
        assert reg_t == "tumbling", f"Tumbling classification flipped to {reg_t} at factor {factor}"
        assert reg_m == "mixed", f"Mixed classification flipped to {reg_m} at factor {factor}"


