"""Run a single plate/coin drop simulation and save trajectory plots and CSV data."""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
import numpy as np
import yaml

from autumn.integrate import simulate_drop
from autumn.params import (
    SimulationConfig,
    load_all_coin_sets,
    get_default_config_path
)
from autumn.plotting import plot_single_drop


def main():
    parser = argparse.ArgumentParser(description="Simulate a single drop of a 2D plate/coin.")
    parser.add_argument("--coin-set", type=str, default="reference_card", help="Name of coin set from config/coin_sets.yaml")
    parser.add_argument("--theta0-deg", type=float, default=15.0, help="Initial release angle in degrees")
    parser.add_argument("--u0", type=float, default=0.0, help="Initial u velocity [m/s]")
    parser.add_argument("--v0", type=float, default=0.0, help="Initial v velocity [m/s]")
    parser.add_argument("--omega0", type=float, default=0.0, help="Initial angular velocity [rad/s]")
    parser.add_argument("--run-id", type=str, default=None, help="Identifier for run output folder")
    args = parser.parse_args()

    base_yaml = get_default_config_path("base.yaml")
    coins_yaml = get_default_config_path("coin_sets.yaml")

    coin_sets = load_all_coin_sets(coins_yaml)
    if args.coin_set not in coin_sets:
        raise ValueError(f"Unknown coin set '{args.coin_set}'. Available sets: {list(coin_sets.keys())}")

    plate = coin_sets[args.coin_set]
    config = SimulationConfig.from_yaml(base_yaml)
    config.plate = plate

    theta0_rad = args.theta0_deg * (3.141592653589793 / 180.0)

    print(f"Starting single drop simulation for '{plate.name}'...")
    print(f"  Chord L = {plate.L*1000:.1f} mm, Thickness h = {plate.h*1000:.2f} mm, rho_s = {plate.rho_s} kg/m^3")
    print(f"  I* = {plate.I_star(config.fluid.rho_f):.4f}, Release angle = {args.theta0_deg} deg")

    res = simulate_drop(
        plate=plate,
        fluid=config.fluid,
        coeffs=config.coefficients,
        numerics=config.numerics,
        theta0=theta0_rad,
        u0=args.u0,
        v0=args.v0,
        omega0=args.omega0
    )

    run_id = args.run_id or f"{args.coin_set}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = Path("results") / "single" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save run configuration
    run_cfg_dict = {
        "coin_set": args.coin_set,
        "run_id": run_id,
        "release_angle_deg": args.theta0_deg,
        "plate": {
            "name": plate.name,
            "rho_s": plate.rho_s,
            "L": plate.L,
            "h": plate.h,
            "notes": plate.notes,
            "I_star": plate.I_star(config.fluid.rho_f)
        },
        "fluid": vars(config.fluid),
        "coefficients": vars(config.coefficients),
        "numerics": vars(config.numerics),
        "outcome": {
            "reached_bottom": res.reached_bottom,
            "timed_out": res.timed_out,
            "duration_s": float(res.t[-1]),
            "final_Y_m": float(res.Y[-1]),
            "final_X_m": float(res.X[-1]),
            "mean_descent_speed_ms": float(np.mean(np.abs(res.v_Y)))
        }
    }
    with open(out_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(run_cfg_dict, f, default_flow_style=False)

    plot_single_drop(res, out_dir, run_name="single_drop")

    print(f"Simulation completed:")
    print(f"  Time: {res.t[-1]:.3f} s (reached bottom: {res.reached_bottom}, timed out: {res.timed_out})")
    print(f"  Landing position: X = {res.X[-1]*1000:.2f} mm, Y = {res.Y[-1]*1000:.2f} mm")
    print(f"  Outputs saved to: {out_dir}")


if __name__ == "__main__":
    main()
