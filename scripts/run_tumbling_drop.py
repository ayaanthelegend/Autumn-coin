"""Simulate and plot clean unidirectional tumbling and chaotic alternating tumbling drops."""

from __future__ import annotations

import math
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from autumn.integrate import simulate_drop
from autumn.params import PlateParams, SimulationConfig, get_default_config_path
from autumn.plotting import plot_single_drop, save_figure_and_csv


def plot_tumbling_comparison(res_clean, res_chaotic, out_dir: Path | str) -> None:
    """Generate side-by-side comparison of clean unidirectional tumbling vs chaotic alternating tumbling."""
    fig, axs = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Falling Dynamics: Unidirectional Tumbling vs Chaotic Alternating Tumbling (2D quasi-steady model simulation)", fontsize=13)

    # 1. Clean unidirectional tumbling trajectory (X-Y)
    ax0 = axs[0, 0]
    ax0.plot(res_clean.X * 1000.0, res_clean.Y * 1000.0, color="#1f77b4", lw=1.5, label="Trajectory")
    ax0.set_xlabel("Lateral Position X [mm]")
    ax0.set_ylabel("Vertical Position Y [mm]")
    ax0.set_title(r"(a) Unidirectional Tumbling ($I^*=1.20$): X-Y Trajectory")
    ax0.grid(True)
    ax0.axis("equal")
    ax0.legend(loc="upper right")

    # 2. Clean unidirectional orientation theta(t)
    ax1 = axs[0, 1]
    ax1.plot(res_clean.t, np.degrees(res_clean.theta), color="#2ca02c", lw=1.5)
    ax1.set_xlabel("Time t [s]")
    ax1.set_ylabel(r"Orientation $\theta$ [deg]")
    flips_clean = abs(res_clean.theta[-1] - res_clean.theta[0]) / (2.0 * math.pi)
    ax1.set_title(rf"(b) Unidirectional Tumbling $\theta(t)$ ({flips_clean:.0f} continuous flips, no reversals)")
    ax1.grid(True)

    # 3. Chaotic alternating tumbling trajectory (X-Y)
    ax2 = axs[1, 0]
    ax2.plot(res_chaotic.X * 1000.0, res_chaotic.Y * 1000.0, color="#d62728", lw=1.5, label="Trajectory")
    ax2.set_xlabel("Lateral Position X [mm]")
    ax2.set_ylabel("Vertical Position Y [mm]")
    ax2.set_title(r"(c) Chaotic Alternating Tumbling ($I^*=3.50$): X-Y Trajectory")
    ax2.grid(True)
    ax2.axis("equal")
    ax2.legend(loc="upper right")

    # 4. Chaotic alternating orientation theta(t)
    ax3 = axs[1, 1]
    ax3.plot(res_chaotic.t, np.degrees(res_chaotic.theta), color="#ff7f0e", lw=1.5)
    ax3.set_xlabel("Time t [s]")
    ax3.set_ylabel(r"Orientation $\theta$ [deg]")
    ax3.set_title(r"(d) Chaotic Tumbling $\theta(t)$ (multiple full flips with reversals)")
    ax3.grid(True)

    plt.tight_layout()

    csv_headers = ["t_s", "X_clean_mm", "Y_clean_mm", "theta_clean_deg", "X_chaotic_mm", "Y_chaotic_mm", "theta_chaotic_deg"]
    # Interpolate to common time grid for table
    t_common = np.linspace(0, min(res_clean.t[-1], res_chaotic.t[-1]), 500)
    x_c = np.interp(t_common, res_clean.t, res_clean.X * 1000.0)
    y_c = np.interp(t_common, res_clean.t, res_clean.Y * 1000.0)
    th_c = np.interp(t_common, res_clean.t, np.degrees(res_clean.theta))
    x_ch = np.interp(t_common, res_chaotic.t, res_chaotic.X * 1000.0)
    y_ch = np.interp(t_common, res_chaotic.t, res_chaotic.Y * 1000.0)
    th_ch = np.interp(t_common, res_chaotic.t, np.degrees(res_chaotic.theta))

    csv_rows = np.column_stack([t_common, x_c, y_c, th_c, x_ch, y_ch, th_ch])
    save_figure_and_csv(fig, out_dir, "tumbling_comparison", csv_headers, csv_rows)


def main():
    base_yaml = get_default_config_path("base.yaml")
    config = SimulationConfig.from_yaml(base_yaml)

    # 1. Clean unidirectional tumbling plate (I* = 1.20)
    i_star_clean = 1.20
    L_clean = 0.024
    h_clean = 0.0018
    rho_s_clean = i_star_clean * config.fluid.rho_f * L_clean / h_clean
    plate_clean = PlateParams(f"tumbling_clean_I{i_star_clean:.2f}", rho_s_clean, L_clean, h_clean, notes="Clean unidirectional tumbling showcase")

    # 2. Chaotic alternating tumbling plate (I* = 3.50)
    i_star_chaotic = 3.50
    L_chaotic = 0.024
    h_chaotic = 0.0036
    rho_s_chaotic = i_star_chaotic * config.fluid.rho_f * L_chaotic / h_chaotic
    plate_chaotic = PlateParams(f"tumbling_chaotic_I{i_star_chaotic:.2f}", rho_s_chaotic, L_chaotic, h_chaotic, notes="Chaotic alternating tumbling showcase")

    print(f"Simulating clean unidirectional tumbling drop (I* = {i_star_clean:.2f}, L = {L_clean*1000:.1f} mm, h = {h_clean*1000:.2f} mm)...")
    res_clean = simulate_drop(
        plate=plate_clean,
        fluid=config.fluid,
        coeffs=config.coefficients,
        numerics=config.numerics,
        theta0=np.radians(20.0)
    )

    print(f"Simulating chaotic alternating tumbling drop (I* = {i_star_chaotic:.2f}, L = {L_chaotic*1000:.1f} mm, h = {h_chaotic*1000:.2f} mm)...")
    res_chaotic = simulate_drop(
        plate=plate_chaotic,
        fluid=config.fluid,
        coeffs=config.coefficients,
        numerics=config.numerics,
        theta0=np.radians(20.0)
    )

    out_dir = Path("results/single/tumbling_drop")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Primary Figure 10: Clean unidirectional tumbling
    plot_single_drop(res_clean, out_dir, run_name="tumbling_drop")

    # Comparison Figure: Clean vs Chaotic tumbling
    plot_tumbling_comparison(res_clean, res_chaotic, out_dir)

    flips_clean = abs(res_clean.theta[-1] - res_clean.theta[0]) / (2.0 * math.pi)
    flips_chaotic = abs(res_chaotic.theta[-1] - res_chaotic.theta[0]) / (2.0 * math.pi)
    print("Tumbling simulations complete:")
    print(f"  Clean tumbling:   flips = {flips_clean:.1f}, lateral drift = {abs(res_clean.X[-1])*1000:.1f} mm")
    print(f"  Chaotic tumbling: net flips = {flips_chaotic:.1f}, lateral drift = {abs(res_chaotic.X[-1])*1000:.1f} mm")
    print(f"  Saved to: {out_dir}")


if __name__ == "__main__":
    main()
