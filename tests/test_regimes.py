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

    # 1. Smallest I* must be steady
    assert regimes[0] == "steady", f"Smallest I*={i_stars[0]} should be steady, got {regimes[0]}"

    # 2. Largest I* must be unsteady (fluttering or tumbling)
    assert regimes[-1] in ("fluttering", "tumbling"), f"Largest I*={i_stars[-1]} should be unsteady, got {regimes[-1]}"
    assert ranges[-1] > ranges[0], "Oscillation amplitude should grow with I*"

    # 3. Identify and report transition I*
    transition_i_star = None
    for i_s, reg in zip(i_stars, regimes):
        if reg != "steady":
            transition_i_star = i_s
            break
    print(f"Reported Transition from steady to {regimes[-1]} occurs at I* approx {transition_i_star}")


def test_regime_threshold_sensitivity():
    """Verify that regime classifications do not flip under +/- 20% variations in thresholds."""
    cfg = SimulationConfig.from_yaml("config/base.yaml")
    L = 0.020
    h = 0.0005

    # Run for a steady case and a fluttering case
    plate_steady = PlateParams("steady_case", 0.1 * cfg.fluid.rho_f * L / h, L, h)
    plate_flutter = PlateParams("flutter_case", 5.0 * cfg.fluid.rho_f * L / h, L, h)

    res_steady = simulate_drop(plate_steady, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))
    res_flutter = simulate_drop(plate_flutter, cfg.fluid, cfg.coefficients, cfg.numerics, theta0=np.radians(20.0))

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
        assert reg_f == "fluttering", f"Fluttering classification flipped to {reg_f} at factor {factor}"
