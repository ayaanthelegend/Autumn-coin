"""Bisection study for flutter-to-tumble onset I* across mu_1 and release angles theta_0.

Addresses Review Items A-1 and A-6:
- Implements coarse scan (step 0.05) to find first crossing, then bisection (tol <= 0.005)
- mu_1 in {0.0, 0.01, 0.05, 0.10, 0.20}
- theta0 in {5.0, 20.0, 45.0} deg
- Fixed path h/L rule:
    h/L = I*/1.5 if I* < 0.1125 else max(0.075, I*/20.0)
    L = 24 mm, release from rest, H_fall = 80 L
- Uses regime classifier's 'tumbling' label (net rotation >= 2 turns post-transient)
- Writes results/mu1_sensitivity.csv
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.params import Coefficients, FluidParams, NumericsParams, PlateParams, RegimeClassifierParams

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"


def get_plate_for_istar(i_star: float, L: float = 0.024, rho_f: float = 998.0) -> PlateParams:
    """Construct PlateParams along fixed path h/L rule for given I*."""
    if i_star < 0.1125:
        h_over_L = i_star / 1.5
    else:
        h_over_L = max(0.075, i_star / 20.0)
    h = L * h_over_L
    rho_s = rho_f * i_star / h_over_L
    return PlateParams(name=f"card_I_{i_star:.4f}", rho_s=rho_s, L=L, h=h)


def evaluate_drop(
    i_star: float,
    mu_1: float,
    theta0_deg: float,
    fluid: FluidParams,
    numerics: NumericsParams,
    classifier_params: RegimeClassifierParams,
    L: float = 0.024
) -> Tuple[str, Dict[str, float]]:
    """Simulate a single drop and classify its regime."""
    c_tau = math.pi * 0.20 / 8.0
    coeffs = Coefficients(mu_1=mu_1, mu_2=0.20, C_tau=c_tau)
    plate = get_plate_for_istar(i_star, L=L, rho_f=fluid.rho_f)
    theta0_rad = math.radians(theta0_deg)

    res = simulate_drop(
        plate=plate,
        fluid=fluid,
        coeffs=coeffs,
        numerics=numerics,
        theta0=theta0_rad,
        u0=0.0,
        v0=0.0,
        omega0=0.0
    )
    regime, metrics = classify_regime(
        t=res.t,
        Y=res.Y,
        theta=res.theta,
        omega=res.omega,
        H_fall=res.H_fall,
        params=classifier_params
    )
    return regime, metrics


def find_flutter_tumble_onset(
    mu_1: float,
    theta0_deg: float,
    fluid: FluidParams,
    numerics: NumericsParams,
    classifier_params: RegimeClassifierParams,
    coarse_start: float = 0.50,
    coarse_step: float = 0.05,
    coarse_max: float = 2.50,
    tol: float = 0.005,
    max_bisect_iter: int = 15
) -> Dict[str, object]:
    """Find first flutter-to-tumble onset I* by coarse scan followed by bisection."""
    # 1. Coarse scan to bracket the first crossing to 'tumbling'
    curr_i = coarse_start
    prev_i = coarse_start
    prev_regime = "fluttering"
    found_bracket = False
    low_bracket = coarse_start
    high_bracket = coarse_start

    while curr_i <= coarse_max + 1e-9:
        reg, met = evaluate_drop(curr_i, mu_1, theta0_deg, fluid, numerics, classifier_params)
        if reg == "tumbling":
            low_bracket = prev_i
            high_bracket = curr_i
            found_bracket = True
            break
        prev_i = curr_i
        prev_regime = reg
        curr_i = round(curr_i + coarse_step, 4)

    if not found_bracket:
        return {
            "mu_1": mu_1,
            "theta0_deg": theta0_deg,
            "I_star_c": float("nan"),
            "I_star_lower": prev_i,
            "I_star_upper": curr_i,
            "bracket_width": float("nan"),
            "coarse_bracket_low": prev_i,
            "coarse_bracket_high": curr_i,
            "regime_below": prev_regime,
            "regime_above": "not_reached",
            "diff_vs_120_mid_pct": float("nan")
        }

    coarse_low = low_bracket
    coarse_high = high_bracket

    # 2. Bisection
    low = low_bracket
    high = high_bracket
    for _ in range(max_bisect_iter):
        if (high - low) <= tol:
            break
        mid = 0.5 * (low + high)
        reg, met = evaluate_drop(mid, mu_1, theta0_deg, fluid, numerics, classifier_params)
        if reg == "tumbling":
            high = mid
        else:
            low = mid

    i_star_c = 0.5 * (low + high)
    bracket_width = high - low
    diff_120 = ((i_star_c - 1.20) / 1.20) * 100.0

    return {
        "mu_1": mu_1,
        "theta0_deg": theta0_deg,
        "I_star_c": round(i_star_c, 4),
        "I_star_lower": round(low, 4),
        "I_star_upper": round(high, 4),
        "bracket_width": round(bracket_width, 4),
        "coarse_bracket_low": round(coarse_low, 4),
        "coarse_bracket_high": round(coarse_high, 4),
        "regime_below": "fluttering",
        "regime_above": "tumbling",
        "diff_vs_120_mid_pct": round(diff_120, 2)
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = RESULTS_DIR / "mu1_sensitivity.csv"

    fluid = FluidParams(rho_f=998.0, g=9.81)
    numerics = NumericsParams(H_fall_factor=80.0, perturbation_rad=0.0)
    cla = RegimeClassifierParams()

    mu_1_values = [0.0, 0.01, 0.05, 0.10, 0.20]
    theta0_values = [5.0, 20.0, 45.0]

    rows: List[Dict[str, object]] = []

    print("=" * 70, flush=True)
    print("  AUTUMN COIN: mu_1 SENSITIVITY AND I*_c BISECTION STUDY", flush=True)
    print("=" * 70, flush=True)

    for mu1 in mu_1_values:
        for th0 in theta0_values:
            print(f"Running bisection: mu_1={mu1:4.2f}, theta0={th0:4.1f} deg...", end="", flush=True)
            res = find_flutter_tumble_onset(
                mu_1=mu1,
                theta0_deg=th0,
                fluid=fluid,
                numerics=numerics,
                classifier_params=cla
            )
            rows.append(res)
            print(f" -> I*_c = {res['I_star_c']:.4f} (bracket: [{res['I_star_lower']:.4f}, {res['I_star_upper']:.4f}], diff vs 1.20: {res['diff_vs_120_mid_pct']:+.1f}%)", flush=True)

    fieldnames = [
        "mu_1",
        "theta0_deg",
        "I_star_c",
        "I_star_lower",
        "I_star_upper",
        "bracket_width",
        "coarse_bracket_low",
        "coarse_bracket_high",
        "regime_below",
        "regime_above",
        "diff_vs_120_mid_pct"
    ]

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\nResults successfully saved to:", out_csv, flush=True)


if __name__ == "__main__":
    main()
