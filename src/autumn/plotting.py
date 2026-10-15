"""Matplotlib plotting utilities for Autumn Coin simulations.

Strict specifications:
- Pure white background, high-contrast dark text and axes.
- 300 DPI PNG plus vector PDF output.
- Every figure title/caption explicitly includes: '2D quasi-steady model simulation'.
- Accompanying CSV data saved alongside figures.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence
import matplotlib.pyplot as plt
import numpy as np

# Apply universal formatting defaults for paper-quality graphics
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "text.color": "#111111",
    "axes.labelcolor": "#111111",
    "xtick.color": "#111111",
    "ytick.color": "#111111",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "lines.linewidth": 1.5,
    "grid.color": "#d0d0d0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})


def save_figure_and_csv(
    fig: plt.Figure,
    out_dir: Path | str,
    base_name: str,
    csv_headers: Sequence[str],
    csv_rows: Sequence[Sequence[object]]
) -> None:
    """Save figure as both 300-dpi PNG and PDF, accompanied by underlying CSV data."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    png_file = out_path / f"{base_name}.png"
    pdf_file = out_path / f"{base_name}.pdf"
    csv_file = out_path / f"{base_name}.csv"

    fig.savefig(png_file, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_file, bbox_inches="tight")
    plt.close(fig)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        writer.writerows(csv_rows)


def plot_single_drop(
    res,
    out_dir: Path | str,
    run_name: str = "single_drop"
) -> None:
    r"""Plot single drop trajectory in X-Y plane, theta(t), and speed(t).
    
    Includes orientation directors every N points.
    """
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Single Drop Dynamics: {res.plate.name} (2D quasi-steady model simulation)", fontsize=13)

    # 1. Trajectory in X-Y plane
    ax0 = axs[0]
    ax0.plot(res.X * 1000, res.Y * 1000, color="#1f77b4", label="Center trajectory")
    ax0.set_xlabel("Lateral position X [mm]")
    ax0.set_ylabel("Vertical position Y [mm]")
    ax0.set_title("(a) Trajectory in X-Y Plane")
    ax0.grid(True)
    ax0.axis("equal")

    # Draw orientation director bars at regular intervals
    step = max(len(res.t) // 30, 1)
    half_l_mm = (res.plate.L / 2.0) * 1000.0
    for i in range(0, len(res.t), step):
        xi = res.X[i] * 1000.0
        yi = res.Y[i] * 1000.0
        thi = res.theta[i]
        dx = half_l_mm * np.cos(thi)
        dy = half_l_mm * np.sin(thi)
        ax0.plot([xi - dx, xi + dx], [yi - dy, yi + dy], color="#d62728", lw=1.2, alpha=0.8)

    ax0.scatter([res.X[0]*1000], [res.Y[0]*1000], color="green", zorder=5, label="Release")
    ax0.scatter([res.X[-1]*1000], [res.Y[-1]*1000], color="black", zorder=5, label="Landing")
    ax0.legend(loc="upper right")

    # 2. Angle theta(t)
    ax1 = axs[1]
    ax1.plot(res.t, np.degrees(res.theta), color="#2ca02c")
    ax1.set_xlabel("Time t [s]")
    ax1.set_ylabel(r"Orientation $\theta$ [deg]")
    ax1.set_title(r"(b) Tilt Angle $\theta(t)$")
    ax1.grid(True)

    # 3. Speed vs time
    ax2 = axs[2]
    ax2.plot(res.t, res.speed, color="#9467bd", label="|V| total")
    ax2.plot(res.t, np.abs(res.v_Y), color="#ff7f0e", ls="--", label="|v_Y| vertical")
    ax2.set_xlabel("Time t [s]")
    ax2.set_ylabel("Speed [m/s]")
    ax2.set_title("(c) Descent Speed vs Time")
    ax2.grid(True)
    ax2.legend(loc="lower right")

    plt.tight_layout()

    csv_headers = ["t_s", "X_m", "Y_m", "theta_rad", "u_ms", "v_ms", "omega_rads", "vX_ms", "vY_ms", "speed_ms"]
    csv_rows = np.column_stack([
        res.t, res.X, res.Y, res.theta, res.u, res.v, res.omega, res.v_X, res.v_Y, res.speed
    ])
    save_figure_and_csv(fig, out_dir, f"{run_name}_trajectory", csv_headers, csv_rows)


def plot_energy_budget(
    t: np.ndarray,
    E_kin: np.ndarray,
    E_pot: np.ndarray,
    W_diss: np.ndarray,
    E_total: np.ndarray,
    E_pot_drop: float,
    out_dir: Path | str,
    base_name: str = "energy_budget"
) -> None:
    r"""Plot energy components and budget closure."""
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.suptitle("Energy Budget Reconciliation (2D quasi-steady model simulation)", fontsize=12)

    ax0.plot(t, E_kin, label=r"Kinetic $T = T_{\mathrm{body}} + T_{\mathrm{fluid}}$", color="#1f77b4")
    ax0.plot(t, E_pot - E_pot[0], label=r"Potential $\Delta V_{\mathrm{pot}}$", color="#ff7f0e")
    ax0.plot(t, W_diss, label=r"Dissipated $W_{\mathrm{diss}}$", color="#2ca02c")
    ax0.plot(t, E_total - E_total[0], label=r"Total $\Delta E + W_{\mathrm{diss}}$", color="black", ls="--", lw=1.8)
    ax0.set_xlabel("Time t [s]")
    ax0.set_ylabel("Energy [J/m]")
    ax0.set_title("(a) Energy Evolution")
    ax0.grid(True)
    ax0.legend(loc="center left")

    # Residual normalized by potential energy drop
    residual_pct = np.abs(E_total - E_total[0]) / max(E_pot_drop, 1e-9) * 100.0
    ax1.plot(t, residual_pct, color="#d62728")
    ax1.axhline(1.0, color="gray", ls=":", label="1% acceptance limit")
    ax1.set_xlabel("Time t [s]")
    ax1.set_ylabel(r"Relative Error $|\Delta E| / \Delta V_{\mathrm{pot}}$ [%]")
    ax1.set_title("(b) Energy Closure Residual")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    plt.tight_layout()

    csv_headers = ["t_s", "E_kin_Jm", "E_pot_Jm", "W_diss_Jm", "E_total_Jm", "residual_pct"]
    csv_rows = np.column_stack([t, E_kin, E_pot, W_diss, E_total, residual_pct])
    save_figure_and_csv(fig, out_dir, base_name, csv_headers, csv_rows)


def plot_fft_frequency(
    freqs: np.ndarray,
    spectrum: np.ndarray,
    f_dom: float,
    St: float,
    out_dir: Path | str,
    base_name: str = "flutter_fft"
) -> None:
    r"""Plot power spectral density of tilt angle theta(t) with dominant Strouhal number."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(freqs, spectrum, color="#1f77b4", lw=1.5)
    ax.axvline(f_dom, color="#d62728", ls="--", label=f"Dominant freq: {f_dom:.2f} Hz (St = {St:.3f})")
    ax.set_xlabel("Frequency f [Hz]")
    ax.set_ylabel(r"Power Spectral Density of $\theta(t)$ [$\mathrm{rad}^2/\mathrm{Hz}$]")
    ax.set_title(f"Fluttering Frequency Analysis (2D quasi-steady model simulation: St={St:.3f})")
    ax.grid(True)
    ax.legend(loc="upper right")
    plt.tight_layout()

    csv_headers = ["freq_Hz", "psd"]
    csv_rows = np.column_stack([freqs, spectrum])
    save_figure_and_csv(fig, out_dir, base_name, csv_headers, csv_rows)


def plot_i_star_sweep(
    i_star_list: np.ndarray,
    regimes: Sequence[str],
    mean_speeds: np.ndarray,
    lateral_drifts: np.ndarray,
    out_dir: Path | str,
    base_name: str = "i_star_sweep"
) -> None:
    r"""Plot I* sweep metrics: regime classification, mean descent speed, lateral drift."""
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
    fig.suptitle(r"$I^*$ Sweep Analysis (2D quasi-steady model simulation)", fontsize=13)

    # 1. Regime vs I*
    ax0 = axs[0]
    unique_regimes = ["steady", "fluttering", "mixed", "tumbling"]
    color_map = {"steady": "#1f77b4", "fluttering": "#2ca02c", "mixed": "#ff7f0e", "tumbling": "#d62728"}
    reg_num_map = {r: i for i, r in enumerate(unique_regimes)}
    reg_nums = [reg_num_map.get(r, 2) for r in regimes]

    for reg in unique_regimes:
        idx = [i for i, r in enumerate(regimes) if r == reg]
        if idx:
            ax0.scatter(i_star_list[idx], np.array(reg_nums)[idx], color=color_map[reg], s=60, label=reg, zorder=3)

    ax0.set_xscale("log")
    ax0.set_yticks(range(len(unique_regimes)))
    ax0.set_yticklabels(unique_regimes)
    ax0.set_xlabel(r"Dimensionless Moment of Inertia $I^*$")
    ax0.set_ylabel("Falling Regime")
    ax0.set_title(r"(a) Regime vs $I^*$")
    ax0.grid(True, which="both")
    ax0.legend(loc="upper left")

    # 2. Mean descent speed vs I*
    ax1 = axs[1]
    ax1.plot(i_star_list, mean_speeds, "o-", color="#1f77b4", lw=1.5, markersize=5)
    ax1.set_xscale("log")
    ax1.set_xlabel(r"Dimensionless Moment of Inertia $I^*$")
    ax1.set_ylabel("Mean Descent Speed [m/s]")
    ax1.set_title(r"(b) Mean Descent Speed vs $I^*$")
    ax1.grid(True, which="both")

    # 3. Lateral drift vs I*
    ax2 = axs[2]
    ax2.plot(i_star_list, lateral_drifts * 1000.0, "s-", color="#d62728", lw=1.5, markersize=5)
    ax2.set_xscale("log")
    ax2.set_xlabel(r"Dimensionless Moment of Inertia $I^*$")
    ax2.set_ylabel("Net Lateral Drift |X_final| [mm]")
    ax2.set_title(r"(c) Lateral Drift vs $I^*$")
    ax2.grid(True, which="both")

    plt.tight_layout()

    csv_headers = ["I_star", "regime", "mean_speed_ms", "lateral_drift_m"]
    csv_rows = [[i_s, reg, spd, drf] for i_s, reg, spd, drf in zip(i_star_list, regimes, mean_speeds, lateral_drifts)]
    save_figure_and_csv(fig, out_dir, base_name, csv_headers, csv_rows)


def plot_release_angle_sweep(
    angles_deg: np.ndarray,
    results_by_case: Dict[str, Dict[str, np.ndarray]],
    out_dir: Path | str,
    base_name: str = "release_angle_sweep"
) -> None:
    r"""Plot lateral drift and descent speed vs release angle for flutter, transition, tumble."""
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(12, 4.8))
    fig.suptitle(r"Release Angle Sweep Dynamics (2D quasi-steady model simulation)", fontsize=13)

    colors = {"flutter": "#2ca02c", "transition": "#ff7f0e", "tumble": "#d62728"}

    for case, data in results_by_case.items():
        c = colors.get(case, "#1f77b4")
        i_s = data.get("I_star", 0.0)
        lbl = f"{case.capitalize()} ($I^*={i_s:.2f}$)"
        ax0.plot(angles_deg, data["lateral_drift"] * 1000.0, "o-", color=c, label=lbl, markersize=4)
        ax1.plot(angles_deg, data["mean_speed"], "s-", color=c, label=lbl, markersize=4)

    ax0.set_xlabel(r"Release Angle $\theta_0$ [deg]")
    ax0.set_ylabel("Net Lateral Drift [mm]")
    ax0.set_title(r"(a) Lateral Drift vs Release Angle $\theta_0$")
    ax0.grid(True)
    ax0.legend()

    ax1.set_xlabel(r"Release Angle $\theta_0$ [deg]")
    ax1.set_ylabel("Mean Descent Speed [m/s]")
    ax1.set_title(r"(b) Mean Descent Speed vs $\theta_0$")
    ax1.grid(True)
    ax1.legend()

    plt.tight_layout()

    csv_headers = ["angle_deg"]
    for case in results_by_case.keys():
        csv_headers.extend([f"{case}_drift_mm", f"{case}_speed_ms"])

    csv_rows = []
    for i, ang in enumerate(angles_deg):
        row = [ang]
        for case, data in results_by_case.items():
            row.append(data["lateral_drift"][i] * 1000.0)
            row.append(data["mean_speed"][i])
        csv_rows.append(row)

    save_figure_and_csv(fig, out_dir, base_name, csv_headers, csv_rows)


def plot_chaos_ensemble(
    t_interp: np.ndarray,
    mean_X: np.ndarray,
    std_X: np.ndarray,
    mean_Y: np.ndarray,
    landing_X: np.ndarray,
    i_star: float,
    case_name: str,
    out_dir: Path | str,
    base_name: str = "chaos_ensemble"
) -> None:
    r"""Plot ensemble mean trajectory with 1-sigma band, landing scatter and histogram."""
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"Chaos & Dispersion Ensemble: {case_name} ($I^*={i_star:.2f}$) (2D quasi-steady model simulation)", fontsize=12)

    # 1. Trajectory bundle & 1-sigma band
    ax0.plot(mean_X * 1000.0, mean_Y * 1000.0, color="#1f77b4", lw=2, label="Mean trajectory")
    ax0.fill_betweenx(
        mean_Y * 1000.0,
        (mean_X - std_X) * 1000.0,
        (mean_X + std_X) * 1000.0,
        color="#1f77b4",
        alpha=0.25,
        label=r"$\pm 1\sigma$ Lateral Band"
    )
    ax0.set_xlabel("Lateral Position X [mm]")
    ax0.set_ylabel("Vertical Position Y [mm]")
    ax0.set_title(r"(a) Trajectory Ensemble & $\pm 1\sigma$ Dispersion")
    ax0.grid(True)
    ax0.axis("equal")
    ax0.legend(loc="upper right")

    # 2. Histogram of landing X positions
    ax1.hist(landing_X * 1000.0, bins=15, color="#ff7f0e", edgecolor="black", alpha=0.85)
    mean_lx = np.mean(landing_X) * 1000.0
    std_lx = np.std(landing_X) * 1000.0
    ax1.axvline(mean_lx, color="black", lw=1.5, ls="--", label=f"Mean: {mean_lx:.1f} mm")
    ax1.axvline(mean_lx - std_lx, color="gray", lw=1.2, ls=":", label=f"Std: {std_lx:.1f} mm")
    ax1.axvline(mean_lx + std_lx, color="gray", lw=1.2, ls=":")
    ax1.set_xlabel("Landing Position X [mm]")
    ax1.set_ylabel("Drop Count")
    ax1.set_title("(b) Landing Scatter Histogram")
    ax1.grid(True)
    ax1.legend(loc="upper right")

    plt.tight_layout()

    csv_headers = ["drop_index", "landing_X_mm"]
    csv_rows = [[i+1, lx * 1000.0] for i, lx in enumerate(landing_X)]
    save_figure_and_csv(fig, out_dir, f"{base_name}_{case_name}", csv_headers, csv_rows)


def plot_regime_map(
    i_stars: np.ndarray,
    res: np.ndarray,
    regimes: Sequence[str],
    out_dir: Path | str,
    base_name: str = "regime_map",
    res_in: Optional[np.ndarray] = None,
    extra_cols: Optional[Dict[str, Sequence]] = None,
) -> None:
    r"""Plot phase diagram of I* vs Re with regime colors, Re=5000 fitted threshold, and single clean legend."""
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    fig.suptitle(r"Phase Diagram: Falling Regime Map ($I^*$ vs $\mathrm{Re}$) (2D quasi-steady model simulation)", fontsize=13)

    color_map = {
        "steady": "#1f77b4",
        "fluttering": "#2ca02c",
        "mixed": "#ff7f0e",
        "tumbling": "#d62728"
    }
    marker_map = {
        "steady": "o",
        "fluttering": "^",
        "mixed": "s",
        "tumbling": "D"
    }

    # Shade the extrapolation zone Re > 5000 beyond the fitted quasi-steady coefficient range
    max_re_plot = max(float(np.max(res)) * 1.25, 6000.0)
    ax.axvspan(5000.0, max_re_plot, color="gray", alpha=0.14, label="Extrapolated (Re > 5000)", zorder=1)
    ax.axvline(5000.0, color="#b22222", ls="--", lw=1.5, alpha=0.85, label="Fitted Re Limit (Re = 5000)", zorder=2)

    unique_regimes = ["steady", "fluttering", "mixed", "tumbling"]
    for reg in unique_regimes:
        idx = [i for i, r in enumerate(regimes) if r == reg]
        if idx:
            ax.scatter(
                np.array(res)[idx],
                np.array(i_stars)[idx],
                color=color_map[reg],
                marker=marker_map[reg],
                s=70,
                alpha=0.9,
                edgecolors="black",
                linewidths=0.5,
                label=reg.capitalize(),
                zorder=4
            )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(left=min(150.0, float(np.min(res)) * 0.8), right=max_re_plot)
    ax.set_xlabel(r"Measured Reynolds Number $\mathrm{Re}_{\mathrm{meas}} = \rho_f U_{\mathrm{mean}} L / \mu$ (a posteriori)")
    ax.set_ylabel(r"Dimensionless Moment of Inertia $I^* = (\rho_s h) / (\rho_f L)$")
    ax.grid(True, which="both", alpha=0.35)
    ax.legend(title="Regime & Thresholds", loc="lower right", framealpha=0.95, fontsize=9)

    plt.tight_layout()

    if res_in is not None:
        csv_headers = ["I_star", "Re_in", "Re_meas", "regime"]
        if extra_cols:
            for k in extra_cols.keys():
                csv_headers.append(k)
        csv_rows = []
        for i in range(len(i_stars)):
            row = [i_stars[i], res_in[i], res[i], regimes[i]]
            if extra_cols:
                for k, col in extra_cols.items():
                    row.append(col[i])
            csv_rows.append(row)
    else:
        csv_headers = ["I_star", "Re", "regime"]
        csv_rows = [[i_s, r_val, reg] for i_s, r_val, reg in zip(i_stars, res, regimes)]

    save_figure_and_csv(fig, out_dir, base_name, csv_headers, csv_rows)
