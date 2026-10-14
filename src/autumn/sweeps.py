"""Parameter sweep engines for Autumn Coin simulations.

Implements:
1. I* sweep (log-spaced 25 points from 0.05 to 5.0)
2. Release angle sweep (0 to 90 deg, 19 points)
3. Chaos ensemble (50 drops per I* with Gaussian perturbations)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.metrics import compute_energy_budget, compute_fft_frequency, compute_trajectory_summary
from autumn.params import PlateParams, SimulationConfig
from autumn.plotting import (
    plot_chaos_ensemble,
    plot_energy_budget,
    plot_fft_frequency,
    plot_i_star_sweep,
    plot_release_angle_sweep,
)


def run_i_star_sweep(
    config: SimulationConfig,
    n_points: int = 25,
    i_star_min: float = 0.05,
    i_star_max: float = 5.0,
    L: float = 0.020,
    h: float = 0.0005,
    theta0_deg: float = 5.0,
    perturbation_deg: float = 0.1,
    seed: int = 42,
    out_dir: Path | str = "results/sweeps/i_star_sweep"
) -> Dict[str, object]:
    r"""Execute I* sweep from i_star_min to i_star_max."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    i_star_list = np.geomspace(i_star_min, i_star_max, n_points)

    regimes: List[str] = []
    mean_speeds: List[float] = []
    lateral_drifts: List[float] = []
    re_list: List[float] = []

    flutter_res_sample = None

    for i, i_s in enumerate(i_star_list):
        rho_s = i_s * config.fluid.rho_f * L / h
        plate = PlateParams(f"plate_i_{i_s:.3f}", rho_s, L, h)

        # Release angle with small perturbation
        theta_pert = rng.normal(0.0, np.radians(perturbation_deg))
        th0 = np.radians(theta0_deg) + theta_pert

        res = simulate_drop(
            plate=plate,
            fluid=config.fluid,
            coeffs=config.coefficients,
            numerics=config.numerics,
            theta0=th0
        )

        summary = compute_trajectory_summary(res, config.regime_classifier)
        reg = summary["regime"]
        regimes.append(reg)
        mean_speeds.append(summary["U_mean"])
        lateral_drifts.append(summary["lateral_drift"])
        re_list.append(summary["Re"])

        if reg == "fluttering" and flutter_res_sample is None:
            flutter_res_sample = res

    i_stars_arr = np.array(i_star_list)
    speeds_arr = np.array(mean_speeds)
    drifts_arr = np.array(lateral_drifts)
    re_arr = np.array(re_list)

    # Plot I* sweep metrics
    plot_i_star_sweep(i_stars_arr, regimes, speeds_arr, drifts_arr, out_path, "i_star_sweep")

    # If fluttering sample exists, generate FFT frequency analysis and energy budget
    if flutter_res_sample is None:
        flutter_res_sample = res  # fallback to last run

    summary_sample = compute_trajectory_summary(flutter_res_sample, config.regime_classifier)
    plot_fft_frequency(
        summary_sample["freqs"],
        summary_sample["psd"],
        summary_sample["f_dom"],
        summary_sample["St"],
        out_path,
        "flutter_frequency_analysis"
    )

    energy_data = compute_energy_budget(flutter_res_sample)
    plot_energy_budget(
        energy_data["t"],
        energy_data["E_kin"],
        energy_data["E_pot"],
        energy_data["W_diss"],
        energy_data["E_total"],
        energy_data["delta_e_pot_drop"],
        out_path,
        "energy_budget_reconciliation"
    )

    return {
        "i_stars": i_stars_arr,
        "regimes": regimes,
        "mean_speeds": speeds_arr,
        "lateral_drifts": drifts_arr,
        "Re": re_arr,
        "out_dir": str(out_path)
    }


def run_release_angle_sweep(
    config: SimulationConfig,
    n_points: int = 19,
    theta_min_deg: float = 0.0,
    theta_max_deg: float = 90.0,
    i_star_cases: Dict[str, float] = None,
    L: float = 0.020,
    h: float = 0.0005,
    seed: int = 42,
    out_dir: Path | str = "results/sweeps/release_angle_sweep"
) -> Dict[str, object]:
    r"""Execute release angle sweep (0 to 90 deg) across representative I* cases."""
    if i_star_cases is None:
        i_star_cases = {"flutter": 0.2, "transition": 1.0, "tumble": 4.0}

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    angles_deg = np.linspace(theta_min_deg, theta_max_deg, n_points)
    results_by_case = {}

    for case_name, i_s in i_star_cases.items():
        rho_s = i_s * config.fluid.rho_f * L / h
        plate = PlateParams(f"{case_name}_I_{i_s}", rho_s, L, h)

        drifts = []
        speeds = []

        for ang in angles_deg:
            th0 = np.radians(ang)
            res = simulate_drop(
                plate=plate,
                fluid=config.fluid,
                coeffs=config.coefficients,
                numerics=config.numerics,
                theta0=th0
            )
            summary = compute_trajectory_summary(res, config.regime_classifier)
            drifts.append(summary["lateral_drift"])
            speeds.append(summary["U_mean"])

        results_by_case[case_name] = {
            "I_star": i_s,
            "lateral_drift": np.array(drifts),
            "mean_speed": np.array(speeds)
        }

    plot_release_angle_sweep(angles_deg, results_by_case, out_path, "release_angle_sweep")

    return {
        "angles_deg": angles_deg,
        "results_by_case": results_by_case,
        "out_dir": str(out_path)
    }


def run_chaos_ensemble(
    config: SimulationConfig,
    n_drops: int = 50,
    i_star_cases: Dict[str, float] = None,
    L: float = 0.020,
    h: float = 0.0005,
    theta0_mean_deg: float = 5.0,
    theta0_std_deg: float = 0.5,
    v_pert_std: float = 1.0e-4,
    seed: int = 12345,
    out_dir: Path | str = "results/sweeps/chaos_ensemble"
) -> Dict[str, object]:
    r"""Execute Monte Carlo ensemble of drops with Gaussian perturbations to assess dispersion."""
    if i_star_cases is None:
        i_star_cases = {"flutter": 0.2, "transition": 1.0, "tumble": 4.0}

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    ensemble_results = {}

    for case_name, i_s in i_star_cases.items():
        rho_s = i_s * config.fluid.rho_f * L / h
        plate = PlateParams(f"ens_{case_name}", rho_s, L, h)

        trajectories_X = []
        trajectories_Y = []
        landing_Xs = []

        # Common vertical depth grid for ensemble averaging
        h_fall = config.numerics.H_fall_factor * L
        y_grid = np.linspace(0.0, -h_fall, 200)

        for drop_idx in range(n_drops):
            th_pert = rng.normal(0.0, np.radians(theta0_std_deg))
            u_pert = rng.normal(0.0, v_pert_std)
            v_pert = rng.normal(0.0, v_pert_std)

            res = simulate_drop(
                plate=plate,
                fluid=config.fluid,
                coeffs=config.coefficients,
                numerics=config.numerics,
                theta0=np.radians(theta0_mean_deg) + th_pert,
                u0=u_pert,
                v0=v_pert
            )

            landing_Xs.append(res.X[-1])

            # Interpolate X as a function of Y
            # Ensure Y is monotonically decreasing
            y_sort_idx = np.argsort(res.Y)
            y_sorted = res.Y[y_sort_idx]
            x_sorted = res.X[y_sort_idx]
            x_interp = np.interp(y_grid, y_sorted, x_sorted)
            trajectories_X.append(x_interp)

        arr_X = np.array(trajectories_X)
        mean_X = np.mean(arr_X, axis=0)
        std_X = np.std(arr_X, axis=0)
        landing_X_arr = np.array(landing_Xs)

        plot_chaos_ensemble(
            t_interp=y_grid,
            mean_X=mean_X,
            std_X=std_X,
            mean_Y=y_grid,
            landing_X=landing_X_arr,
            i_star=i_s,
            case_name=case_name,
            out_dir=out_path,
            base_name="chaos_ensemble"
        )

        ensemble_results[case_name] = {
            "I_star": i_s,
            "mean_X": mean_X,
            "std_X": std_X,
            "landing_X": landing_X_arr,
            "landing_mean_mm": float(np.mean(landing_X_arr) * 1000.0),
            "landing_std_mm": float(np.std(landing_X_arr) * 1000.0)
        }

    return {
        "ensemble_results": ensemble_results,
        "out_dir": str(out_path)
    }
