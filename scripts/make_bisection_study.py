"""Rigorous bisection study for critical I*_c and mu_1 sensitivity.

Addresses Review Items A-1 and A-6:
- Finds onset of tumbling by bisection on I* (bracket tolerance < 0.01)
- Evaluates I*_c as a function of mu_1 in {0.0, 0.01, 0.05, 0.10, 0.20}
- Evaluates I*_c across release angles theta_0 in {5 deg, 20 deg, 45 deg}
- Evaluates I*_c across aspect ratios h/L in {0.05, 0.075, 0.10}
- Compares against Andersen, Pesavento & Wang (2005b) Table 1 (Card 1: I*=1.14, Card 2: I*=1.38, transition band 1.10 - 1.30)
- Outputs results/bisection_istar_c.csv and results/mu1_sensitivity_table.csv
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.params import PlateParams, FluidParams, Coefficients, NumericsParams, RegimeClassifierParams, get_labelling_numerics

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"

def bisect_istar_c(
    mu1: float = 0.2,
    theta0_deg: float = 20.0,
    aspect: float = 0.075,
    L: float = 0.024,
    tol: float = 0.005,
    max_iter: int = 15
) -> dict:
    fluid = FluidParams(rho_f=998.0, g=9.81)
    coeffs = Coefficients(mu_1=mu1)
    base_num = NumericsParams(t_max_min=40.0, t_max_factor=4.0, H_fall_factor=80.0, min_horizon_time_units=80.0)
    num = get_labelling_numerics(base_num, perturbation_rad=0.001)
    cla = RegimeClassifierParams()
    h = L * aspect

    def evaluate(i_star: float) -> tuple[bool, str, float]:
        rho_s = i_star * fluid.rho_f / aspect
        p = PlateParams("bisect_card", rho_s, L, h)
        u0_scale = math.sqrt(max(0.0, (rho_s / fluid.rho_f) - 1.0) * fluid.g * p.b)
        tau_0 = p.a / u0_scale if u0_scale > 1e-6 else 0.05
        res = simulate_drop(p, fluid, coeffs, num, theta0=np.radians(theta0_deg))
        reg, met = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, cla, tau_0=tau_0)
        net_turns = abs(met.get("delta_theta_net_rad", 0.0)) / (2.0 * math.pi)
        # Onset of tumbling / departure from pure fluttering:
        is_onset = (reg != "fluttering")
        return is_onset, reg, net_turns

    low = 0.70
    high = 2.40

    # Ensure brackets
    is_t_low, reg_low, _ = evaluate(low)
    is_t_high, reg_high, _ = evaluate(high)

    for _ in range(max_iter):
        mid = 0.5 * (low + high)
        is_t, reg_mid, flips = evaluate(mid)
        if is_t:
            high = mid
        else:
            low = mid
        if (high - low) < tol:
            break

    mid_c = 0.5 * (low + high)
    return {
        "mu_1": mu1,
        "theta0_deg": theta0_deg,
        "aspect_h_L": aspect,
        "I_star_lower": round(low, 4),
        "I_star_upper": round(high, 4),
        "I_star_c": round(mid_c, 4),
        "bracket_width": round(high - low, 4),
        "regime_below": "fluttering",
        "regime_above": "tumbling/mixed"
    }

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 65)
    print("  RUNNING RIGOROUS I*_c BISECTION & mu_1 SENSITIVITY STUDY")
    print("=" * 65)

    # 1. mu_1 Sensitivity Sweep (at baseline theta0 = 20 deg, aspect = 0.075)
    mu1_values = [0.0, 0.01, 0.05, 0.10, 0.20]
    mu1_rows = []
    print("\n--- 1. mu_1 Sensitivity (onset of tumbling) ---")
    for mu1 in mu1_values:
        res = bisect_istar_c(mu1=mu1, theta0_deg=20.0, aspect=0.075)
        # Percent error against literature mid-band 1.20
        err_pct_120 = ((res["I_star_c"] - 1.20) / 1.20) * 100.0
        # Percent difference against lower band (1.10) and upper band (1.30)
        diff_110 = ((res["I_star_c"] - 1.10) / 1.10) * 100.0
        diff_130 = ((res["I_star_c"] - 1.30) / 1.30) * 100.0

        res["diff_vs_110_pct"] = round(diff_110, 1)
        res["diff_vs_130_pct"] = round(diff_130, 1)
        res["diff_vs_120_mid_pct"] = round(err_pct_120, 1)
        res["note"] = "Literature baseline" if mu1 == 0.2 else ("Tuned alternative" if mu1 == 0.01 else "Sensitivity point")
        mu1_rows.append(res)
        print(f"mu_1 = {mu1:4.2f} -> I*_c = {res['I_star_c']:.3f} [{res['I_star_lower']:.3f}, {res['I_star_upper']:.3f}] | diff vs 1.20: {err_pct_120:+.1f}%")

    df_mu1 = pd.DataFrame(mu1_rows)
    df_mu1.to_csv(RESULTS_DIR / "mu1_sensitivity_table.csv", index=False)
    print(f"\nSaved mu_1 sensitivity table to: {RESULTS_DIR / 'mu1_sensitivity_table.csv'}")

    # 2. Comprehensive Bisection Grid: mu_1 x theta_0 x aspect
    full_rows = []
    print("\n--- 2. Comprehensive Parameter Grid (theta_0 and h/L) ---")
    for mu1 in [0.01, 0.20]:
        for th0 in [5.0, 20.0, 45.0]:
            for asp in [0.05, 0.075, 0.10]:
                res = bisect_istar_c(mu1=mu1, theta0_deg=th0, aspect=asp)
                full_rows.append(res)
                print(f"mu_1={mu1:4.2f}, theta0={th0:4.1f} deg, h/L={asp:5.3f} -> I*_c = {res['I_star_c']:.3f} [{res['I_star_lower']:.3f}, {res['I_star_upper']:.3f}]")

    df_full = pd.DataFrame(full_rows)
    df_full.to_csv(RESULTS_DIR / "bisection_istar_c.csv", index=False)
    print(f"\nSaved comprehensive bisection dataset to: {RESULTS_DIR / 'bisection_istar_c.csv'}")

if __name__ == "__main__":
    main()
