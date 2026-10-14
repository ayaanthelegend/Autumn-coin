"""Run configured sweeps from config/sweeps.yaml and output publication figures."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
import yaml

from autumn.params import SimulationConfig, get_default_config_path
from autumn.sweeps import (
    run_chaos_ensemble,
    run_i_star_sweep,
    run_release_angle_sweep
)


def main():
    parser = argparse.ArgumentParser(description="Execute parameter sweeps for 2D plate falling simulation.")
    parser.add_argument(
        "--sweep",
        type=str,
        default="all",
        choices=["all", "i_star", "release_angle", "chaos"],
        help="Sweep experiment to execute"
    )
    args = parser.parse_args()

    base_yaml = get_default_config_path("base.yaml")
    sweeps_yaml = get_default_config_path("sweeps.yaml")

    config = SimulationConfig.from_yaml(base_yaml)

    with open(sweeps_yaml, "r", encoding="utf-8") as f:
        sweep_defs = yaml.safe_load(f)

    print("======================================================================")
    print("Autumn Coin: Parameter Sweep Execution (2D quasi-steady model)")
    print("======================================================================")

    t0 = time.time()

    if args.sweep in ("all", "i_star"):
        print("\n--> Running Experiment 1: I* Sweep (25 log-spaced values)...")
        cfg_i = sweep_defs.get("i_star_sweep", {})
        res_i = run_i_star_sweep(
            config=config,
            n_points=cfg_i.get("n_points", 25),
            i_star_min=cfg_i.get("i_star_min", 0.05),
            i_star_max=cfg_i.get("i_star_max", 5.0),
            L=cfg_i.get("L", 0.024),
            theta0_deg=cfg_i.get("theta0_deg", 5.0),
            perturbation_deg=cfg_i.get("perturbation_deg", 0.1),
            seed=cfg_i.get("seed", 42),
            out_dir="results/sweeps/i_star_sweep"
        )
        print(f"  I* sweep complete. Figures and CSV written to: {res_i['out_dir']}")

    if args.sweep in ("all", "release_angle"):
        print("\n--> Running Experiment 2: Release Angle Sweep (0 to 90 deg, 19 angles)...")
        cfg_ang = sweep_defs.get("release_angle_sweep", {})
        res_ang = run_release_angle_sweep(
            config=config,
            n_points=cfg_ang.get("n_points", 19),
            theta_min_deg=cfg_ang.get("theta_min_deg", 0.0),
            theta_max_deg=cfg_ang.get("theta_max_deg", 90.0),
            i_star_cases=cfg_ang.get("i_star_cases", None),
            L=cfg_ang.get("L", 0.024),
            seed=cfg_ang.get("seed", 42),
            out_dir="results/sweeps/release_angle_sweep"
        )
        print(f"  Release angle sweep complete. Written to: {res_ang['out_dir']}")

    if args.sweep in ("all", "chaos"):
        print("\n--> Running Experiment 3: Chaos & Dispersion Ensemble (50 drops per I*)...")
        cfg_ens = sweep_defs.get("chaos_ensemble", {})
        res_ens = run_chaos_ensemble(
            config=config,
            n_drops=cfg_ens.get("n_drops", 50),
            i_star_cases=cfg_ens.get("i_star_cases", None),
            L=cfg_ens.get("L", 0.024),
            theta0_mean_deg=cfg_ens.get("theta0_mean_deg", 5.0),
            theta0_std_deg=cfg_ens.get("theta0_std_deg", 0.5),
            v_pert_std=cfg_ens.get("v_pert_std", 1.0e-4),
            seed=cfg_ens.get("seed", 12345),
            out_dir="results/sweeps/chaos_ensemble"
        )
        print(f"  Chaos ensemble complete. Written to: {res_ens['out_dir']}")


    elapsed = time.time() - t0
    print(f"\nAll requested sweeps executed successfully in {elapsed:.2f} s.")


if __name__ == "__main__":
    main()
