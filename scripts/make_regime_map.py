"""Construct 2D Regime Map (I* vs Re) computed a posteriori from mean descent speed.

As established in review: The quasi-steady ODE model has no explicit viscosity dependence
(coefficients C_D, C_T, C_R, C_tau are constant). Therefore, the regime map is constructed
by varying physical plate properties (rho_s, L, h) and calculating the realized Reynolds number
Re = rho_f * U_mean * L / mu a posteriori.
"""

from __future__ import annotations

import argparse
import math
import time
from pathlib import Path
import numpy as np
import yaml

from autumn.dimensionless import classify_regime, compute_reynolds_number
from autumn.integrate import simulate_drop
from autumn.params import NumericsParams, PlateParams, SimulationConfig, get_default_config_path, get_labelling_numerics
from autumn.plotting import plot_regime_map


def generate_regime_map(
    config: SimulationConfig,
    n_i_star: int = 15,
    i_star_min: float = 0.05,
    i_star_max: float = 3.5,
    L_values: list[float] = None,
    theta0_deg: float = 20.0,
    out_dir: Path | str = "results"
) -> dict:
    if L_values is None:
        L_values = [0.008, 0.012, 0.016, 0.020]

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Grid: preserve low-I* geomspace points and add 0.05 steps in [1.0, 1.8], step 0.25 up to 3.5
    geom_low = np.geomspace(i_star_min, i_star_max, n_i_star)
    low_pts = [float(x) for x in geom_low if x < 1.0]
    mid_pts = [round(float(x), 4) for x in np.arange(1.0, 1.801, 0.05)]
    high_pts = [round(float(x), 4) for x in np.arange(2.0, 3.501, 0.25)]
    i_star_grid = sorted(list(set(low_pts + mid_pts + high_pts)))

    # Use unified labelling helper for explicit 1e-3 rad perturbation
    base_num = get_labelling_numerics(config.numerics, perturbation_rad=0.001)
    from dataclasses import replace
    numerics_map = replace(
        base_num,
        H_fall_factor=100.0,
        min_horizon_time_units=config.numerics.min_horizon_time_units
    )

    all_i_stars = []
    all_res_in = []
    all_res_meas = []
    all_regimes = []
    all_speeds = []
    all_u_t = []
    all_L = []
    all_h = []
    all_rho_s = []
    all_perturbations = []
    all_actual_angles = []
    all_window_tu = []
    all_symmetric = []

    print(f"Generating regime map across {len(i_star_grid)} I* values and {len(L_values)} plate chords (fitted Re range [200, 5000]: L in 8-20 mm, I* in 0.05-3.5)...")

    for L in L_values:
        for i_s in i_star_grid:
            # Physical aspect ratio scaling keeping h/L in [0.035, 0.25] and enforcing rho_s/rho_f <= 20
            aspect = float(np.clip(0.045 + 0.05 * np.sqrt(i_s), 0.035, 0.25))
            if i_s <= 0.08:
                aspect = min(aspect, i_s / 1.25)
            aspect = max(aspect, i_s / 20.0)
            h = L * aspect
            rho_s = float(i_s * config.fluid.rho_f / aspect)
            if rho_s <= config.fluid.rho_f:
                continue

            plate = PlateParams(f"map_L{int(L*1000)}_I{i_s:.2f}", rho_s, L, h)
            # Physical perturbed release angle across all points
            th0 = np.radians(theta0_deg)

            res = simulate_drop(
                plate=plate,
                fluid=config.fluid,
                coeffs=config.coefficients,
                numerics=numerics_map,
                theta0=th0
            )

            u0_scale = np.sqrt(max(0.0, (rho_s / config.fluid.rho_f - 1.0)) * config.fluid.g * (h / 4.0))
            tau_0 = (L / 2.0) / (u0_scale if u0_scale > 1e-6 else 1.0)

            regime, metrics = classify_regime(
                res.t, res.Y, res.theta, res.omega, res.H_fall, config.regime_classifier, tau_0=tau_0
            )

            # Compute mean descent speed discarding initial transient window
            t_transient = max(20.0 * tau_0, config.regime_classifier.transient_fraction * res.t[-1])
            transient_depth = config.regime_classifier.transient_fraction * res.H_fall
            valid_mask = (res.t >= t_transient) & (res.Y <= (res.Y[0] - transient_depth))
            if np.sum(valid_mask) < 10:
                valid_mask = res.t >= (0.5 * res.t[-1])
                if np.sum(valid_mask) < 5:
                    valid_mask = np.ones_like(res.Y, dtype=bool)

            u_mean = float(np.mean(res.speed[valid_mask]))
            re_meas = compute_reynolds_number(config.fluid.rho_f, u_mean, plate.L, config.fluid.mu)

            # Input Froude-based terminal velocity scale and Reynolds number
            u_t = float(np.sqrt(max(rho_s / config.fluid.rho_f - 1.0, 0.0) * config.fluid.g * h))
            re_in = float(config.fluid.rho_f * u_t * plate.L / config.fluid.mu)

            all_i_stars.append(i_s)
            all_res_in.append(re_in)
            all_res_meas.append(re_meas)
            all_regimes.append(regime)
            all_speeds.append(u_mean)
            all_u_t.append(u_t)
            all_L.append(L * 1000.0)
            all_h.append(h * 1000.0)
            all_rho_s.append(rho_s)
            all_perturbations.append(res.numerics.perturbation_rad)
            all_actual_angles.append(round(math.degrees(res.actual_theta0_rad), 4))
            all_window_tu.append(round(metrics.get("window_time_units", 0.0), 2))
            all_symmetric.append(res.symmetric_start)

    all_i_stars_arr = np.array(all_i_stars)
    all_res_in_arr = np.array(all_res_in)
    all_res_meas_arr = np.array(all_res_meas)

    extra_cols = {
        "mean_speed_ms": all_speeds,
        "U_t_ms": all_u_t,
        "L_mm": all_L,
        "h_mm": all_h,
        "rho_s": all_rho_s,
        "perturbation_rad": all_perturbations,
        "theta_actual_deg": all_actual_angles,
        "window_time_units": all_window_tu,
        "symmetric_start": all_symmetric
    }

    plot_regime_map(
        i_stars=all_i_stars_arr,
        res=all_res_meas_arr,
        regimes=all_regimes,
        out_dir=out_path,
        base_name="regime_map",
        res_in=all_res_in_arr,
        extra_cols=extra_cols
    )

    # Tally regime distribution
    unique, counts = np.unique(all_regimes, return_counts=True)
    tally = dict(zip(unique, counts))

    print(f"Regime map generated ({len(all_i_stars)} points total):")
    for reg, cnt in tally.items():
        print(f"  {reg.capitalize():12s}: {cnt:3d} ({cnt/len(all_i_stars)*100:.1f}%)")
    print(f"  Reynolds number range (measured): [{min(all_res_meas):.1f}, {max(all_res_meas):.1f}]")
    print(f"  Reynolds number range (input Froude): [{min(all_res_in):.1f}, {max(all_res_in):.1f}]")
    print(f"Outputs written to: {out_path / 'regime_map.png'} and {out_path / 'regime_map.csv'}")

    return {
        "i_stars": all_i_stars_arr,
        "Re_in": all_res_in_arr,
        "Re_meas": all_res_meas_arr,
        "regimes": all_regimes,
        "tally": tally,
        "out_dir": str(out_path)
    }


def main():
    parser = argparse.ArgumentParser(description="Generate 2D Regime Map (I* vs Re).")
    parser.add_argument("--theta0-deg", type=float, default=20.0, help="Release angle [deg]")
    parser.add_argument("--out-dir", type=str, default="results", help="Output directory")
    args = parser.parse_args()

    base_yaml = get_default_config_path("base.yaml")
    config = SimulationConfig.from_yaml(base_yaml)

    t0 = time.time()
    generate_regime_map(config, theta0_deg=args.theta0_deg, out_dir=args.out_dir)
    print(f"Regime map completed in {time.time() - t0:.2f} s.")


if __name__ == "__main__":
    main()
