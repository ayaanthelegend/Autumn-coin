"""Acceptance Test 6: Regime ordering across I* and threshold sensitivity."""

import math
import numpy as np
import pytest

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.params import PlateParams, RegimeClassifierParams, SimulationConfig


def test_regime_ordering_transition():
    r"""Acceptance Test 6:
    
    Verify that at small I*, the plate undergoes steady descent (or low-amplitude flutter),
    and at large I*, the dynamics transition to unsteady oscillatory motion (fluttering or tumbling).
    Report the exact transition point and whether tumbling emerges with default coefficients.
    """
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.020
    h = 0.0005  # Thin plate ensuring rho_s > rho_f across the entire sweep range

    i_stars = [0.08, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0]
    regimes = []
    ranges = []

    for i_s in i_stars:
        rho_s = i_s * cfg.fluid.rho_f * L / h
        plate = PlateParams(f"test_i_{i_s}", rho_s, L, h)
        # Release with standard angle of 20 deg
        res = simulate_drop(plate, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
        reg, met = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, cfg.regime_classifier)
        regimes.append(reg)
        ranges.append(met["theta_range_rad"])

    print("\n--- Regime Ordering Test Results ---")
    for i_s, reg, rng in zip(i_stars, regimes, ranges):
        print(f"I* = {i_s:4.2f} -> {reg:10s} (theta_range = {rng:.3f} rad)")

    # 1. Smallest I* must be steady or fluttering (per README section 9 test 6)
    assert regimes[0] in ("steady", "fluttering"), f"Smallest I*={i_stars[0]} should be steady or fluttering, got {regimes[0]}"

    # 2. Tumbling must emerge at higher I*
    assert "tumbling" in regimes or "mixed" in regimes, f"Tumbling or mixed rotation should emerge at higher I*, got {regimes}"

    # 3. Identify and report transition I*
    transition_i_star = None
    for i_s, reg in zip(i_stars, regimes):
        if reg in ("tumbling", "mixed"):
            transition_i_star = i_s
            break
    print(f"Reported Transition from fluttering/steady to tumbling/mixed occurs at I* approx {transition_i_star}")


def test_regime_threshold_sensitivity():
    """Verify that regime classifications do not flip under +/- 20% variations in thresholds."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.020
    h = 0.0005

    # Run for a steady case (broadside release) and a fluttering case
    plate_steady = PlateParams("steady_case", 1200.0, L, 0.002)
    plate_flutter = PlateParams("flutter_case", 2.0 * cfg.fluid.rho_f * L / h, L, h)

    res_steady = simulate_drop(plate_steady, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=0.0)
    res_flutter = simulate_drop(plate_flutter, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(15.0))

    base_params = cfg.regime_classifier

    for factor in [0.8, 1.0, 1.2]:
        perturbed_params = RegimeClassifierParams(
            transient_fraction=base_params.transient_fraction,
            theta_range_steady=base_params.theta_range_steady * factor,
            var_theta_steady=base_params.var_theta_steady * factor,
            min_flips_tumble=base_params.min_flips_tumble
        )
        reg_s, _ = classify_regime(res_steady.t, res_steady.Y, res_steady.theta, res_steady.omega, res_steady.H_fall, perturbed_params)
        reg_f, _ = classify_regime(res_flutter.t, res_flutter.Y, res_flutter.theta, res_flutter.omega, res_flutter.H_fall, perturbed_params)

        assert reg_s == "steady", f"Steady classification flipped to {reg_s} at factor {factor}"
        assert reg_f in ("fluttering", "tumbling", "mixed"), f"Unsteady classification flipped to {reg_f} at factor {factor}"

