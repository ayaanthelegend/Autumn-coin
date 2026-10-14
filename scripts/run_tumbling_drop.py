"""Simulate and plot a high-I* tumbling drop trajectory."""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import yaml

from autumn.integrate import simulate_drop
from autumn.params import PlateParams, SimulationConfig, get_default_config_path
from autumn.plotting import plot_single_drop


def main():
    base_yaml = get_default_config_path("base.yaml")
    config = SimulationConfig.from_yaml(base_yaml)

    # High I* parameter set (e.g. I* = 3.5, physical density ratio rho_s / rho_f ~ 16)
    i_star = 3.5
    L = 0.024
    aspect = i_star / 16.0  # h/L = 0.21875
    h = L * aspect
    rho_s = i_star * config.fluid.rho_f / aspect  # rho_s = 16 * rho_f = 15968 kg/m^3

    plate = PlateParams(f"tumbling_plate_I{i_star}", rho_s, L, h, notes="High-I* plate demonstrating autorotation (tumbling)")

    print(f"Running high-I* tumbling simulation: I* = {i_star}, L = {L*1000:.1f} mm, h = {h*1000:.2f} mm, rho_s = {rho_s:.0f} kg/m^3")

    res = simulate_drop(
        plate=plate,
        fluid=config.fluid,
        coeffs=config.coefficients,
        numerics=config.numerics,
        theta0=np.radians(20.0)
    )

    out_dir = Path("results/single/tumbling_drop")
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_single_drop(res, out_dir, run_name="tumbling_drop")

    n_flips = abs(res.theta[-1] - res.theta[0]) / (2.0 * math.pi)
    print(f"Tumbling drop complete:")
    print(f"  Total flips: {n_flips:.2f}")
    print(f"  Lateral drift: {abs(res.X[-1])*1000:.1f} mm")
    print(f"  Duration: {res.t[-1]:.3f} s (reached bottom: {res.reached_bottom})")
    print(f"  Output saved to: {out_dir}")


if __name__ == "__main__":
    main()
