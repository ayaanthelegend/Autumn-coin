#!/usr/bin/env python
"""Regenerate all publication-quality figures for Autumn Coin research paper.

Design specifications:
  - Width exactly 6.5 in (Word document text column at 100% printed scale).
  - Maximum height 8.0 in.
  - Font STIXGeneral, math stix, text >= 8 pt everywhere.
  - Bold (a), (b) panel letters.
  - Marker size >= 5, line width >= 1.3.
  - Colour-blind-safe palettes (Okabe-Ito inspired).
  - No gridlines by default; very faint grid only where essential.
  - At most TWO panels side by side; 3+ panels stacked vertically.
  - No tags ('2D quasi-steady model simulation', SPH tags, etc.).
  - Output: graphs/*.png (300 DPI) and graphs/*.pdf.
"""

from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

# Ensure project imports resolve
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import plot_style  # Sets universal matplotlib rcParams
from autumn.integrate import simulate_drop
from autumn.params import PlateParams, SimulationConfig, get_default_config_path

RES = ROOT / "results"
SPH = ROOT / "results_sph"
OUT = ROOT / "graphs"
OUT.mkdir(parents=True, exist_ok=True)

COL = plot_style.REGIME_COLORS
MK = plot_style.REGIME_MARKERS
ORDER = plot_style.REGIME_ORDER


def save_fig(fig: plt.Figure, name: str) -> tuple[int, int]:
    """Save figure as PNG (300 dpi) and PDF in graphs/ folder."""
    png_path = OUT / f"{name}.png"
    pdf_path = OUT / f"{name}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    from PIL import Image
    with Image.open(png_path) as im:
        w, h = im.size
    print(f"  [saved] {name}.png ({w}x{h} px) and {name}.pdf")
    return w, h


def regime_legend_handles(present=None, ms=7):
    """Generate clean legend handles for falling regimes."""
    names = present or ORDER
    return [
        Line2D([0], [0], marker=MK[r], color="none", markerfacecolor=COL[r],
               markeredgecolor="#111111", markeredgewidth=0.7, markersize=ms,
               label=r.capitalize())
        for r in names
    ]


# ======================================================================================
# 1. energy_budget
# ======================================================================================
def fig01_energy_budget():
    csv_path = RES / "sweeps" / "i_star_sweep" / "energy_budget_reconciliation.csv"
    d = pd.read_csv(csv_path)
    k = max(1, len(d) // 2500)
    sub = d.iloc[::k]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 2.9))

    # (a) Energy Evolution
    ax1.plot(sub.t_s, sub.E_kin_Jm, color="#0072B2", lw=1.3, label=r"Kinetic $T$")
    ax1.plot(sub.t_s, sub.E_pot_Jm, color="#E69F00", lw=1.3, label=r"Potential $\Delta V$")
    ax1.plot(sub.t_s, sub.W_diss_Jm, color="#009E73", lw=1.3, label=r"Dissipated $W_{\mathrm{diss}}$")
    ax1.plot(sub.t_s, sub.E_total_Jm, color="#111111", ls="--", lw=1.4, label=r"Total $\Delta E + W$")
    ax1.set_xlim(0, float(d.t_s.max()))
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel("Energy per depth [J/m]")
    ax1.set_title(r"$\mathbf{(a)}$ Energy budget evolution")
    ax1.legend(loc="lower left", fontsize=8.0, handlelength=1.4, labelspacing=0.25)

    # (b) Energy Residual
    res_abs = d.residual_pct.abs()
    max_res = float(res_abs.max())
    ax2.plot(sub.t_s, sub.residual_pct.abs(), color="#D55E00", lw=1.3)
    ax2.axhline(1.0, color="#666666", ls=":", lw=1.1, label="1% acceptance limit")
    ax2.text(0.05, 0.82, f"Max error: {max_res:.1e}%", transform=ax2.transAxes,
             fontsize=8.5, va="top", bbox=dict(boxstyle="square,pad=0.2", facecolor="#f5f5f5", edgecolor="none"))
    ax2.set_xlim(0, float(d.t_s.max()))
    ax2.set_ylim(0, 1.15)
    ax2.set_xlabel("Time [s]")
    ax2.set_ylabel(r"Relative closure error $|\Delta E| / \Delta V_{\mathrm{pot}}$ [%]")
    ax2.set_title(r"$\mathbf{(b)}$ Energy closure residual")
    ax2.legend(loc="upper right", fontsize=8.0)

    plt.tight_layout()
    return save_fig(fig, "energy_budget")


# ======================================================================================
# 2. threshold_vs_inertia
# ======================================================================================
def fig02_threshold_vs_inertia():
    rm = pd.read_csv(RES / "regime_map.csv").groupby("I_star", as_index=False).first()
    sens = pd.read_csv(RES / "mu1_sensitivity.csv")
    sens = sens[sens.theta0_deg == sens.theta0_deg.min()].sort_values("mu_1")

    fig, (a1, a2, a3) = plt.subplots(
        3, 1, figsize=(6.5, 5.6),
        gridspec_kw={"height_ratios": [1.0, 1.0, 1.6], "hspace": 0.50}
    )

    def draw_strip(ax, lo, hi, ms):
        for r in ORDER:
            s = rm[(rm.regime == r) & (rm.I_star >= lo) & (rm.I_star <= hi)]
            if len(s):
                ax.scatter(s.I_star, np.zeros(len(s)), s=ms, marker=MK[r], c=COL[r],
                           edgecolors="#111111", linewidths=0.7, zorder=3)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])

    # (a) Full range strip
    draw_strip(a1, 0.045, 4.0, 45)
    a1.set_xscale("log")
    a1.set_xlim(0.045, 4.2)
    a1.axvspan(1.10, 1.30, color="#d8d8d8", alpha=0.5, zorder=0)
    a1.set_title(r"$\mathbf{(a)}$ Regime sequence over $I^*$ ($\mu_1=0.20$, $\theta_0=20^\circ$)")
    a1.set_xlabel(r"$I^* = \rho_s h / (\rho_f L)$")

    # (b) Zoom on transition
    draw_strip(a2, 0.95, 1.9, 65)
    a2.set_xlim(0.95, 1.90)
    a2.axvspan(1.10, 1.30, color="#d8d8d8", alpha=0.5, zorder=0)
    a2.text(1.20, 0.28, "Experimental transition bracket\n[1.10, 1.30]",
            ha="center", va="bottom", fontsize=8.0)
    a2.set_title(r"$\mathbf{(b)}$ Transition region zoom ($I^* \in [0.95, 1.90]$)")
    a2.set_xlabel(r"$I^*$")

    # (c) Critical I*_c versus mu_1
    ypos = np.arange(len(sens))
    for y, (_, row) in zip(ypos, sens.iterrows()):
        a3.errorbar([row.I_star_c], [y],
                    xerr=[[row.I_star_c - row.I_star_lower], [row.I_star_upper - row.I_star_c]],
                    fmt="o", color="#111111", ms=5.5, capsize=3, lw=1.2)
        a3.text(row.I_star_c + 0.015, y, f"{row.I_star_c:.3f}", va="center", fontsize=8.5)

    a3.axvspan(1.10, 1.30, color="#d8d8d8", alpha=0.5, zorder=0, label="Experimental bracket [1.10, 1.30]")
    a3.set_xlim(0.95, 1.90)
    a3.set_yticks(ypos)
    a3.set_yticklabels([rf"$\mu_1 = {m:g}$" for m in sens.mu_1])
    a3.set_xlabel(r"Critical threshold $I^*_c$")
    a3.set_title(r"$\mathbf{(c)}$ Critical threshold $I^*_c$ versus rotational damping $\mu_1$")
    a3.set_ylim(-0.6, len(sens) - 0.4)

    present = [r for r in ORDER if r in set(rm.regime)]
    h_reg = regime_legend_handles(present, ms=6)
    h_reg.append(Line2D([0], [0], color="#d8d8d8", lw=6, label="Exp. bracket [1.10, 1.30]"))
    fig.legend(handles=h_reg, loc="lower center", ncol=len(h_reg), frameon=False,
               bbox_to_anchor=(0.5, -0.01), fontsize=8.0)

    plt.subplots_adjust(left=0.10, right=0.98, top=0.95, bottom=0.08)
    return save_fig(fig, "threshold_vs_inertia")


# ======================================================================================
# 3. speed_drift_sweep
# ======================================================================================
def fig03_speed_drift_sweep():
    csv_path = RES / "sweeps" / "i_star_sweep" / "i_star_sweep.csv"
    d = pd.read_csv(csv_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 2.9))

    # (a) Mean descent speed
    ax1.plot(d.I_star, d.mean_speed_ms, color="#777777", lw=1.1, zorder=1)
    for r in ORDER:
        s = d[d.regime == r]
        if len(s):
            ax1.scatter(s.I_star, s.mean_speed_ms, s=35, marker=MK[r], c=COL[r],
                        edgecolors="#111111", linewidths=0.6, zorder=3)
    ax1.set_xscale("log")
    ax1.set_xlabel(r"Dimensionless moment of inertia $I^*$")
    ax1.set_ylabel("Mean descent speed [m/s]")
    ax1.set_title(r"$\mathbf{(a)}$ Mean descent speed")

    # (b) Net lateral drift
    ax2.plot(d.I_star, d.lateral_drift_m, color="#777777", lw=1.1, zorder=1)
    for r in ORDER:
        s = d[d.regime == r]
        if len(s):
            ax2.scatter(s.I_star, s.lateral_drift_m, s=35, marker=MK[r], c=COL[r],
                        edgecolors="#111111", linewidths=0.6, zorder=3)
    ax2.set_xscale("log")
    ax2.set_xlabel(r"Dimensionless moment of inertia $I^*$")
    ax2.set_ylabel(r"Net lateral drift $|X_{\mathrm{final}}|$ [m]")
    ax2.set_title(r"$\mathbf{(b)}$ Net lateral drift")

    present = [r for r in ORDER if r in set(d.regime)]
    fig.legend(handles=regime_legend_handles(present, ms=6), loc="lower center",
               ncol=len(present), frameon=False, bbox_to_anchor=(0.5, -0.05), fontsize=8.0)

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    return save_fig(fig, "speed_drift_sweep")


# ======================================================================================
# 4. flutter_spectrum
# ======================================================================================
def fig04_flutter_spectrum():
    csv_path = RES / "sweeps" / "i_star_sweep" / "flutter_frequency_analysis.csv"
    d = pd.read_csv(csv_path)

    m = d.freq_Hz <= 6.0
    f, p = d.freq_Hz[m].values, d.psd[m].values
    i_peak = int(np.argmax(p[1:]) + 1)
    peak_f = f[i_peak]
    peak_p = p[i_peak]

    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    ax.plot(f, p, color="#0072B2", lw=1.4)
    ax.axvline(peak_f, color="#D55E00", ls="--", lw=1.1)
    ax.annotate(f"Peak frequency: {peak_f:.2f} Hz",
                xy=(peak_f, peak_p),
                xytext=(peak_f + 0.5, peak_p * 0.85),
                arrowprops=dict(arrowstyle="->", color="#111111", lw=1.0),
                fontsize=8.5, fontweight="bold")

    ax.set_xlim(0, 6.0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel(r"Power spectral density of $\theta(t)$ [$\mathrm{rad}^2/\mathrm{Hz}$]")
    ax.set_title(r"Fluttering orientation spectrum ($0\text{--}6$ Hz)")

    plt.tight_layout()
    return save_fig(fig, "flutter_spectrum")


# ======================================================================================
# 5. regime_map
# ======================================================================================
def fig05_regime_map():
    d = pd.read_csv(RES / "regime_map.csv")
    fig, ax = plt.subplots(figsize=(6.5, 4.4))

    # Extrapolation zone
    re_max = float(d.Re_meas.max()) * 1.3
    ax.axvspan(5000, re_max, color="#f0f0f0", alpha=0.9, zorder=0)
    ax.axvline(5000, color="#8b0000", ls="--", lw=1.2, zorder=1)
    ax.text(5300, 0.058, r"$\mathrm{Re} > 5000$: extrapolated beyond" + "\n" + "fitted aerodynamic laws",
            fontsize=8.0, color="#8b0000", va="bottom")

    # Regime scatter
    for r in ORDER:
        s = d[d.regime == r]
        if len(s):
            ax.scatter(s.Re_meas, s.I_star, s=55, marker=MK[r], c=COL[r],
                       edgecolors="#111111", linewidths=0.6, alpha=0.95,
                       label=r.capitalize(), zorder=3)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(120, re_max)
    ax.set_ylim(0.04, 4.5)
    ax.set_xlabel(r"Measured Reynolds number $\mathrm{Re}_{\mathrm{meas}} = \rho_f U_{\mathrm{mean}} L / \mu$")
    ax.set_ylabel(r"Dimensionless moment of inertia $I^* = \rho_s h / (\rho_f L)$")
    ax.set_title(r"Falling regime map in $(\mathrm{Re}_{\mathrm{meas}},\,I^*)$ space ($L = 8, 12, 16, 20$ mm)")

    # Faint grid for dense regime map
    ax.grid(True, which="both", color="#e8e8e8", linestyle=":", lw=0.6, zorder=0)
    ax.legend(loc="lower right", fontsize=8.0, handletextpad=0.2, framealpha=0.9)

    plt.tight_layout()
    return save_fig(fig, "regime_map")


# ======================================================================================
# 6. release_angle_sensitivity
# ======================================================================================
def fig06_release_angle_sensitivity():
    csv_path = RES / "sweeps" / "release_angle_sweep" / "release_angle_sweep.csv"
    d = pd.read_csv(csv_path)

    cases = [
        ("low_I_0.2", r"$\mathbf{(a)}\ I^* = 0.20$ (fluttering)"),
        ("mid_I_0.8", r"$\mathbf{(b)}\ I^* = 0.80$ (fluttering)"),
        ("high_I_3.5", r"$\mathbf{(c)}\ I^* = 3.50$ (mixed / tumbling)"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(6.5, 6.2), sharex=True)

    for i, (k, title) in enumerate(cases):
        ax1 = axes[i]
        ax2 = ax1.twinx()

        drift = d[f"{k}_drift_mm"].abs()
        speed = d[f"{k}_speed_ms"]

        l1 = ax1.plot(d.angle_deg, drift, "o-", color="#0072B2", ms=4.5, lw=1.3, label="Lateral drift")
        l2 = ax2.plot(d.angle_deg, speed, "s--", color="#D55E00", ms=4.5, lw=1.3, label="Descent speed")

        ax1.set_ylabel("Lateral drift [mm]", color="#0072B2")
        ax2.set_ylabel(r"$U_{\mathrm{mean}}$ [m/s]", color="#D55E00")
        ax1.tick_params(axis="y", labelcolor="#0072B2")
        ax2.tick_params(axis="y", labelcolor="#D55E00")
        ax1.set_title(title, loc="left", fontsize=9.5)

        if i == 0:
            lines = l1 + l2
            labs = [l.get_label() for l in lines]
            ax1.legend(lines, labs, loc="upper center", ncol=2, fontsize=8.0)

    axes[-1].set_xlabel(r"Initial release angle $\theta_0$ [deg]")
    axes[-1].set_xlim(-2, 92)
    axes[-1].set_xticks(np.arange(0, 95, 15))

    plt.tight_layout()
    return save_fig(fig, "release_angle_sensitivity")


# ======================================================================================
# 7. landing_histograms
# ======================================================================================
def fig07_landing_histograms():
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    cases = [
        ("low_I_0.2", r"$\mathbf{(a)}\ I^* = 0.20$ (fluttering)"),
        ("mid_I_0.8", r"$\mathbf{(b)}\ I^* = 0.80$ (fluttering)"),
        ("high_I_3.5", r"$\mathbf{(c)}\ I^* = 3.50$ (chaotic / mixed)"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(6.5, 5.8), sharex=True)

    for i, (k, title) in enumerate(cases):
        ax = axes[i]
        d = pd.read_csv(RES / "sweeps" / "chaos_ensemble" / f"chaos_ensemble_{k}.csv")
        x = d.landing_X_mm.values
        m = float(np.mean(x))
        s = float(np.std(x, ddof=1))

        # Histogram
        ax.hist(x, bins=14, color="#56B4E9", edgecolor="#111111", lw=0.6, alpha=0.85)

        # Computed mean and std lines
        ax.axvline(m, color="#111111", ls="--", lw=1.3, label=f"Mean: {m:+.1f} mm")
        ax.axvspan(m - s, m + s, color="#999999", alpha=0.25, label=rf"$\pm 1\sigma$: {s:.1f} mm")

        ax.set_ylabel("Drop count")
        ax.set_title(title, loc="left", fontsize=9.5)
        ax.legend(loc="upper right", fontsize=8.0)
        ax.grid(True, axis="x", color="#e8e8e8", linestyle=":", lw=0.6)

    axes[-1].set_xlabel("Landing position $X$ at 1 m depth [mm]")
    axes[-1].set_xlim(-1300, 1500)

    # Perform tight layout BEFORE inset to avoid layout warning
    plt.tight_layout()

    # Inset zoom for intermediate case to reveal arcsine distribution (all fonts >= 8.0 pt)
    ax_mid = axes[1]
    d_mid = pd.read_csv(RES / "sweeps" / "chaos_ensemble" / "chaos_ensemble_mid_I_0.8.csv")
    x_mid = d_mid.landing_X_mm.values
    ax_ins = inset_axes(ax_mid, width="32%", height="62%", loc="upper left", borderpad=1.2)
    ax_ins.hist(x_mid, bins=10, color="#E69F00", edgecolor="#111111", lw=0.5, alpha=0.9)
    ax_ins.set_xlim(-25, 25)
    ax_ins.set_title(r"Zoom: $\pm 25$ mm", fontsize=8.0, pad=2)
    ax_ins.tick_params(labelsize=8.0)

    return save_fig(fig, "landing_histograms")


# ======================================================================================
# 8. nine_coins
# ======================================================================================
def fig08_nine_coins(cfg: SimulationConfig):
    labels = pd.read_csv(RES / "coin_regimes.csv")
    labels = labels[(np.isclose(labels.mu_1, 0.2)) & (np.isclose(labels.theta0_deg, 5.0))].set_index("coin")

    coin_meta = [
        ("design_acrylic_24x1.2", "Acrylic coin 24 x 1.2 mm", 0.024, 0.0012, 1180.0),
        ("design_aluminium_24x1.5", "Aluminium coin 24 x 1.5 mm", 0.024, 0.0015, 2700.0),
        ("pk_rs10", "Rs 10 coin (brass) 25.5 x 1.5 mm", 0.0255, 0.0015, 7183.0),
        ("pk_rs5_2002", "Rs 5 coin, 2002 (cupronickel) 24 x 2.1 mm", 0.024, 0.0021, 6835.0),
        ("design_brass_24x3.0", "Brass coin 24 x 3.0 mm", 0.024, 0.0030, 8500.0),
        ("design_brass_24x3.5", "Brass coin 24 x 3.5 mm", 0.024, 0.0035, 8500.0),
        ("design_steel_24x4.5", "Steel coin 24 x 4.5 mm", 0.024, 0.0045, 7850.0),
        ("design_lead_24x3.5", "Lead coin 24 x 3.5 mm", 0.024, 0.0035, 11340.0),
        ("design_tungsten_24x3.0", "Tungsten coin 24 x 3.0 mm", 0.024, 0.0030, 19250.0),
    ]

    panel_letters = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)", "(h)", "(i)"]
    fig, axs = plt.subplots(3, 3, figsize=(6.5, 7.5))

    for ax, plet, (cid, title_str, L, h, rho) in zip(axs.ravel(), panel_letters, coin_meta):
        a = L / 2.0
        u0_scale = math.sqrt(max(rho / cfg.fluid.rho_f - 1.0, 0.0) * cfg.fluid.g * h / 2.0)
        tau0 = a / (u0_scale if u0_scale > 1e-6 else 1.0)

        num = dataclasses.replace(cfg.numerics, H_fall_factor=1e6, perturbation_rad=1e-3, dt_out=0.02 * tau0)
        r = simulate_drop(PlateParams(cid, rho, L, h), cfg.fluid, cfg.coefficients, num,
                          theta0=math.radians(5.0), t_max_override=60.0 * tau0)

        x, y, th, t = r.X / a, r.Y / a, r.theta, r.t / tau0

        # Trajectory
        ax.plot(x, y, color="#0072B2", lw=1.2)

        # Ghost chords every 2 time units
        for tg in np.arange(0, 60.01, 2.0):
            idx = int(np.argmin(np.abs(t - tg)))
            dx = np.cos(th[idx])
            dy = np.sin(th[idx])
            ax.plot([x[idx] - dx, x[idx] + dx], [y[idx] - dy, y[idx] + dy],
                    color="#888888", lw=0.8, alpha=0.8)

        # Release and landing points
        ax.plot(x[0], y[0], "o", color="#009E73", ms=4.5, zorder=5)
        ax.plot(x[-1], y[-1], "o", color="#D55E00", ms=4.0, zorder=5)

        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xlabel(r"$x/a$")
        ax.set_ylabel(r"$y/a$")

        reg = labels.loc[cid, "regime"] if cid in labels.index else "undetermined"
        ist = rho * h / (cfg.fluid.rho_f * L)
        reg_cap = reg.capitalize()
        ax.set_title(f"$\\mathbf{{{plet}}}$ {title_str}\n{reg_cap}, $I^*={ist:.3f}$",
                     fontsize=8.0, pad=3)

    plt.tight_layout()
    return save_fig(fig, "nine_coins")


# ======================================================================================
# 9. literature_comparison
# ======================================================================================
def fig09_literature_comparison():
    rm = pd.read_csv(RES / "regime_map.csv")
    lit = pd.read_csv(RES / "literature_validation.csv")

    CZK = [
        ("1 CZK", 8291, 0.0284), ("2 CZK", 9337, 0.0235), ("5 CZK", 10488, 0.0249),
        ("10 CZK", 11760, 0.0323), ("20 CZK", 11291, 0.0303), ("50 CZK", 10904, 0.0295),
    ]
    WASH = [
        ("small hole", 11895, 0.0111), ("medium hole", 10133, 0.0111),
        ("large hole", 9434, 0.0124), ("original", 16290, 0.0346)
    ]
    G32 = 64.0 / math.pi

    fig = plt.figure(figsize=(6.5, 6.2))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1.3, 1.0], hspace=0.36, wspace=0.30,
                           left=0.09, right=0.98, top=0.95, bottom=0.08)

    # (a) Full width on top
    ax_a = fig.add_subplot(gs[0, :])
    ax_a.axvspan(5000, 60000, color="#f0f0f0", alpha=0.9, zorder=0)
    ax_a.axvline(5000, color="#8b0000", ls="--", lw=1.1)

    for r in ORDER:
        s = rm[rm.regime == r]
        if len(s):
            ax_a.scatter(s.Re_meas, s.I_star, s=30, marker=MK[r], c=COL[r],
                         edgecolors="#111111", linewidths=0.5, alpha=0.85, zorder=3)

    # 3D coins
    ys = [0.85, 0.72, 0.61, 0.52, 0.44, 0.37]
    pts = sorted([(n, re, i * G32) for n, re, i in CZK], key=lambda p: -p[2])
    for (n, re, i2), yt in zip(pts, ys):
        ax_a.scatter(re, i2, marker="o", s=45, c="white", edgecolors="#111111", linewidths=1.2, zorder=5)
        ax_a.annotate(n, (re, i2), xytext=(22000, yt), textcoords="data", fontsize=8.0, va="center",
                      arrowprops=dict(arrowstyle="-", color="#777777", lw=0.7))

    # 3D washers
    wy = {"small hole": 0.18, "medium hole": 0.14, "large hole": 0.11, "original": 1.15}
    for n, re, i3 in WASH:
        ax_a.scatter(re, i3 * G32, marker="P", s=50, c="white", edgecolors="#111111", linewidths=1.2, zorder=5)
        ax_a.annotate(f"washer: {n}", (re, i3 * G32), xytext=(22000, wy[n]), textcoords="data",
                      fontsize=8.0, va="center", arrowprops=dict(arrowstyle="-", color="#777777", lw=0.7))

    ax_a.set_xscale("log")
    ax_a.set_yscale("log")
    ax_a.set_xlim(200, 60000)
    ax_a.set_ylim(0.05, 5.0)
    ax_a.set_xlabel(r"$\mathrm{Re}$")
    ax_a.set_ylabel(r"$I^*_{2D} = (64/\pi)\,I^*_{3D}$")
    ax_a.set_title(r"$\mathbf{(a)}$ 2D ODE regimes and 3D disk/washer experiments (open symbols)")

    h_a = regime_legend_handles([r for r in ORDER if r in set(rm.regime)], ms=5)
    h_a += [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor="#111111", markersize=6, label="Coin (3D exp)"),
        Line2D([0], [0], marker="P", color="none", markerfacecolor="white", markeredgecolor="#111111", markersize=6, label="Washer (3D exp)"),
    ]
    ax_a.legend(handles=h_a, loc="lower left", ncol=4, fontsize=8.0, framealpha=0.9)

    # (b) Descent speed ratio
    ax_b = fig.add_subplot(gs[1, 0])
    ax_b.plot(lit.I_star, lit.U_mean_div_Ut, "o-", color="#0072B2", ms=4, lw=1.2, label="2D ODE")
    ax_b.errorbar([1.14], [0.54], yerr=[0.05], fmt="s", color="#009E73", ms=6, capsize=3, label="Card 1, flutter")
    ax_b.errorbar([1.38], [0.62], yerr=[0.06], fmt="D", color="#D55E00", ms=6, capsize=3, label="Card 2, tumble")
    ax_b.set_xscale("log")
    ax_b.set_xlabel(r"$I^*$")
    ax_b.set_ylabel(r"$U_{\mathrm{mean}} / U_t$")
    ax_b.set_title(r"$\mathbf{(b)}$ Descent speed ratio vs Andersen (2005b)")
    ax_b.legend(loc="upper left", fontsize=8.0)

    # (c) Flutter Strouhal number
    ax_c = fig.add_subplot(gs[1, 1])
    fl = lit[lit.regime == "fluttering"]
    ax_c.plot(fl.I_star, fl.Strouhal_St, "s-", color="#0072B2", ms=4, lw=1.2, label="2D ODE (fluttering)")
    ax_c.axhspan(0.18, 0.22, color="#999999", alpha=0.35, label=r"Belmonte band $0.18\text{--}0.22$")
    ax_c.set_xscale("log")
    ax_c.set_ylim(0, float(fl.Strouhal_St.max()) * 1.1)
    ax_c.set_xlabel(r"$I^*$")
    ax_c.set_ylabel(r"$\mathrm{St} = f L / U_{\mathrm{mean}}$")
    ax_c.set_title(r"$\mathbf{(c)}$ Flutter Strouhal number")
    ax_c.legend(loc="upper right", fontsize=8.0)

    return save_fig(fig, "literature_comparison")


# ======================================================================================
# 10. sph_vs_ode_tilt
# ======================================================================================
def fig10_sph_vs_ode_tilt(cfg: SimulationConfig):
    cases = [
        ("flutter_I068", 0.68, r"$\mathbf{(a)}$ Fluttering case ($I^* = 0.68$)"),
        ("tumble_I135", 1.35, r"$\mathbf{(b)}$ Tumbling case ($I^* = 1.35$)"),
    ]
    L, h = 0.024, 0.0018

    fig, axs = plt.subplots(1, 2, figsize=(6.5, 2.9))

    for ax, (cname, ist, title_str) in zip(axs, cases):
        sph_df = pd.read_csv(SPH / "drops" / f"sph_{cname}.csv")
        rho = ist * cfg.fluid.rho_f * L / h
        th0 = float(sph_df.theta.iloc[0])

        num = dataclasses.replace(cfg.numerics, H_fall_factor=1e6, perturbation_rad=0.0, dt_out=0.002)
        r = simulate_drop(PlateParams(cname, rho, L, h), cfg.fluid, cfg.coefficients, num,
                          theta0=th0, t_max_override=0.55)

        ax.plot(r.t, np.degrees(r.theta), "--", color="#333333", lw=1.3, label="2D ODE")
        ax.plot(sph_df.t, np.degrees(sph_df.theta), color="#D55E00", lw=1.6, label="2D SPH")

        ax.set_xlim(0.0, 0.50)
        ax.set_xlabel("Time [s]")
        ax.set_ylabel(r"Tilt angle $\theta$ [deg]")
        ax.set_title(title_str)
        ax.legend(loc="upper left" if "flutter" in cname else "lower left", fontsize=8.0)

    plt.tight_layout()
    return save_fig(fig, "sph_vs_ode_tilt")


# ======================================================================================
# 11. sph_viscosity_sweep
# ======================================================================================
def fig11_sph_viscosity_sweep():
    colors = ["#0072B2", "#009E73", "#E69F00", "#D55E00"]
    re_vals = [25, 100, 300, 800]

    fig, ax = plt.subplots(figsize=(6.5, 3.1))

    for re, c in zip(re_vals, colors):
        df = pd.read_csv(SPH / "drops" / f"sph_visc_Re{re}.csv")
        ax.plot(df.t, np.degrees(df.theta), color=c, lw=1.3,
                label=rf"$\mathrm{{Re}}_{{\mathrm{{in}}}} = {re}$")

    ax.set_xlim(0, 0.35)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel(r"Tilt angle $\theta$ [deg]")
    ax.set_title(r"SPH tilt angle across inlet Reynolds numbers ($I^* = 0.65$, $0.35$ s runs)")
    ax.legend(loc="upper right", ncol=2, fontsize=8.0)

    plt.tight_layout()
    return save_fig(fig, "sph_viscosity_sweep")


# ======================================================================================
# 12. sph_benchmarks
# ======================================================================================
def fig12_sph_benchmarks():
    t4 = pd.read_csv(SPH / "validation" / "test4_dam_break.csv")
    t5 = pd.read_csv(SPH / "validation" / "test5_cylinder_drag.csv")
    t7 = pd.read_csv(SPH / "validation" / "test7_resolution_study.csv")

    fig = plt.figure(figsize=(6.5, 5.5))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1.1, 1.0], hspace=0.36, wspace=0.30,
                           left=0.09, right=0.98, top=0.94, bottom=0.08)

    # (a) Dam break surge front
    ax_a = fig.add_subplot(gs[0, :])
    ax_a.plot(t4.tau_dimensionless, t4.x_front_over_w0, color="#0072B2", lw=1.5, label="SPH front")
    ax_a.set_xlim(0, float(t4.tau_dimensionless.max()))
    ax_a.set_xlabel(r"Dimensionless time $\tau = t \sqrt{g/W_0}$")
    ax_a.set_ylabel(r"Front position $X_{\mathrm{front}} / W_0$")
    ax_a.set_title(r"$\mathbf{(a)}$ Test 4: Dam-break surge front evolution")
    ax_a.legend(loc="lower right", fontsize=8.0)

    # (b) Cylinder drag
    ax_b = fig.add_subplot(gs[1, 0])
    bench = {}
    for _, row in t5.iterrows():
        parts = str(row["steady_benchmark"]).split("-")
        bench[int(row["Re"])] = (float(parts[0]), float(parts[1]))

    xs = np.arange(len(t5))
    cd_col = "CD_measured_t002s" if "CD_measured_t002s" in t5.columns else t5.columns[1]
    ax_b.bar(xs - 0.18, t5[cd_col], 0.35, color="#0072B2", label="SPH measured ($t=0.02$ s)")

    for x, re in zip(xs, t5.Re):
        lo, hi = bench[int(re)]
        mid = (lo + hi) / 2.0
        ax_b.bar(x + 0.18, mid, 0.35, color="#E69F00", yerr=(hi - lo) / 2.0, capsize=3,
                 label="Literature benchmark" if x == 0 else None)

    for x, (_, row) in zip(xs, t5.iterrows()):
        lo, hi = bench[int(row.Re)]
        meas = float(row[cd_col])
        ratio = meas / ((lo + hi) / 2.0)
        ax_b.text(x - 0.18, meas * 1.08, rf"$\times{ratio:.1f}$", ha="center", fontsize=8.0, fontweight="bold")

    ax_b.set_yscale("log")
    ax_b.set_ylim(1.0, 25.0)
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels([rf"$\mathrm{{Re}} = {int(r)}$" for r in t5.Re])
    ax_b.set_ylabel(r"Drag coefficient $C_D$")
    ax_b.set_title(r"$\mathbf{(b)}$ Test 5: Cylinder drag ($C_D$)")
    ax_b.legend(loc="upper right", fontsize=8.0)

    # (c) Grid convergence
    ax_c = fig.add_subplot(gs[1, 1])
    ax_c.plot(t7.N_h, t7.U_mean_m_s, "o-", color="#0072B2", ms=5.5, lw=1.3)
    for _, r in t7.iterrows():
        label_text = str(r.grid_label).split(" ")[0]
        ax_c.annotate(label_text, (r.N_h, r.U_mean_m_s), xytext=(5, 5), textcoords="offset points", fontsize=8.0)

    ax_c.set_xlim(0.75, 1.70)
    ax_c.set_xlabel(r"Particles across thickness $N_h$")
    ax_c.set_ylabel(r"Mean speed $U_{\mathrm{mean}}$ [m/s]")
    ax_c.set_title(r"$\mathbf{(c)}$ Test 7: Spatial resolution study")

    return save_fig(fig, "sph_benchmarks")


# ======================================================================================
# 13. regime_map_labelled
# ======================================================================================
def fig13_regime_map_labelled():
    d = pd.read_csv(RES / "regime_map.csv")
    fig, ax = plt.subplots(figsize=(6.5, 4.4))

    # Extrapolation zone
    re_max = float(d.Re_meas.max()) * 1.3
    ax.axvspan(5000, re_max, color="#f0f0f0", alpha=0.9, zorder=0)
    ax.axvline(5000, color="#8b0000", ls="--", lw=1.2, zorder=1)
    ax.text(5300, 0.058, r"$\mathrm{Re} > 5000$: extrapolated beyond" + "\n" + "fitted aerodynamic laws",
            fontsize=8.0, color="#8b0000", va="bottom")

    # Regime scatter
    for r in ORDER:
        s = d[d.regime == r]
        if len(s):
            ax.scatter(s.Re_meas, s.I_star, s=55, marker=MK[r], c=COL[r],
                       edgecolors="#111111", linewidths=0.6, alpha=0.95,
                       label=r.capitalize(), zorder=3)

    # Labelled points A, B, C, D from figure 14
    pts = [
        ("A", 2195.57, 0.2280, (8, -6)),
        ("B", 4690.76, 0.6764, (8, -6)),
        ("C", 7840.24, 1.3500, (8, -9)),
        ("D", 8571.82, 2.0000, (8, 4)),
    ]

    for letter, re_val, ist_val, text_off in pts:
        ax.scatter([re_val], [ist_val], s=140, facecolors="none",
                   edgecolors="#111111", linewidths=1.8, zorder=10)
        ax.annotate(rf"$\mathbf{{{letter}}}$", (re_val, ist_val),
                    xytext=text_off, textcoords="offset points",
                    fontsize=10, fontweight="bold", zorder=11)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(120, re_max)
    ax.set_ylim(0.04, 4.5)
    ax.set_xlabel(r"Measured Reynolds number $\mathrm{Re}_{\mathrm{meas}} = \rho_f U_{\mathrm{mean}} L / \mu$")
    ax.set_ylabel(r"Dimensionless moment of inertia $I^* = \rho_s h / (\rho_f L)$")
    ax.set_title(r"Falling regime map with trajectory cases $\mathbf{A\text{--}D}$")

    ax.grid(True, which="both", color="#e8e8e8", linestyle=":", lw=0.6, zorder=0)
    ax.legend(loc="lower right", fontsize=8.0, handletextpad=0.2, framealpha=0.9)

    plt.tight_layout()
    return save_fig(fig, "regime_map_labelled")


# ======================================================================================
# 14. trajectory_strips
# ======================================================================================
def fig14_trajectory_strips(cfg: SimulationConfig):
    L = 0.020
    num = dataclasses.replace(cfg.numerics, H_fall_factor=28.0, perturbation_rad=1e-3)

    cases = [
        ("A", 3303.73193, 1.377493e-3, 0.228, "fluttering"),
        ("B", 9000.0, 1.5e-3, 0.676, "fluttering"),
        ("C", 13068.560693, 2.061895e-3, 1.35, "tumbling"),
        ("D", 17249.920513, 2.314214e-3, 2.0, "mixed"),
    ]

    sims = []
    for name, rho, h, istar, reg in cases:
        plate = PlateParams(f"case_{name}", rho, L, h)
        res = simulate_drop(plate, cfg.fluid, cfg.coefficients, num, theta0=math.radians(20.0))
        x = res.X / L
        y = np.abs(res.Y) / L
        th = res.theta
        t = res.t

        idx = [int(np.argmin(np.abs(t - tg))) for tg in np.linspace(t[0], t[-1], 46)]
        h_eff = max(h / L, 0.13)
        x_min = min(x.min() - 0.55, -0.55)
        x_max = max(x.max() + 0.55, 0.55)
        dx = x_max - x_min
        sims.append(dict(name=name, istar=istar, reg=reg, x=x, y=y, th=th, t=t,
                         idx=idx, h_eff=h_eff, x_min=x_min, x_max=x_max, dx=dx))

    W_fig = 6.5
    H_fig = 3.6
    fig = plt.figure(figsize=(W_fig, H_fig))

    # Equal scale across all 4 panels: scale s = 0.065 in / data unit
    scale = 0.065
    H_ax = 30.0 * scale
    Y_bot = 0.55

    w_in = [s["dx"] * scale for s in sims]
    gaps = [0.65, 0.45, 0.40]
    lefts_in = [0.65]
    for j in range(3):
        lefts_in.append(lefts_in[-1] + w_in[j] + gaps[j])

    phi = np.linspace(0, 2 * np.pi, 40)

    for i, s in enumerate(sims):
        # Explicit normalized coordinates: exactly equal physical scale and generous title gaps
        ax = fig.add_axes([lefts_in[i] / W_fig, Y_bot / H_fig, w_in[i] / W_fig, H_ax / H_fig])
        ax.plot(s["x"], s["y"], color="#777777", lw=0.7, zorder=1)

        # 46 snapshots as rotated ellipses
        for k in s["idx"]:
            xk = s["x"][k]
            yk = s["y"][k]
            thk = s["th"][k]
            xb = 0.5 * np.cos(phi)
            yb = 0.5 * s["h_eff"] * np.sin(phi)
            xr = xk + (xb * np.cos(thk) - yb * np.sin(thk))
            yr = yk - (xb * np.sin(thk) + yb * np.cos(thk))
            poly = Polygon(np.column_stack([xr, yr]), facecolor="#ffffff",
                           edgecolor="#111111", lw=0.55, zorder=3)
            ax.add_patch(poly)

        ax.set_xlim(s["x_min"], s["x_max"])
        ax.set_ylim(30.0, 0.0)  # Shared depth 0 to 30
        ax.set_aspect("equal")
        ax.set_xlabel(r"$x/L$")
        s_name = s['name']
        s_reg = s['reg']
        s_ist = s['istar']
        ax.set_title(f"$\\mathbf{{({s_name})}}$ {s_reg}\n$I^* = {s_ist:.3f}$",
                     fontsize=8.0, pad=3)

        if i == 0:
            ax.set_ylabel(r"Depth $|y|/L$")
        else:
            ax.set_yticklabels([])

    return save_fig(fig, "trajectory_strips")


# ======================================================================================
# Main execution orchestrator
# ======================================================================================
def main():
    print("Regenerating all 14 publication-quality research paper figures...")
    cfg = SimulationConfig.from_yaml(get_default_config_path("base.yaml"))

    jobs = [
        ("energy_budget", fig01_energy_budget),
        ("threshold_vs_inertia", fig02_threshold_vs_inertia),
        ("speed_drift_sweep", fig03_speed_drift_sweep),
        ("flutter_spectrum", fig04_flutter_spectrum),
        ("regime_map", fig05_regime_map),
        ("release_angle_sensitivity", fig06_release_angle_sensitivity),
        ("landing_histograms", fig07_landing_histograms),
        ("nine_coins", lambda: fig08_nine_coins(cfg)),
        ("literature_comparison", fig09_literature_comparison),
        ("sph_vs_ode_tilt", lambda: fig10_sph_vs_ode_tilt(cfg)),
        ("sph_viscosity_sweep", fig11_sph_viscosity_sweep),
        ("sph_benchmarks", fig12_sph_benchmarks),
        ("regime_map_labelled", fig13_regime_map_labelled),
        ("trajectory_strips", lambda: fig14_trajectory_strips(cfg)),
    ]

    results_table = []
    for name, fn in jobs:
        print(f"\nRunning {name}...")
        try:
            w, h = fn()
            results_table.append((name, "PASS", f"{w}x{h} px"))
        except Exception as e:
            print(f"  FAILED {name}: {e}")
            results_table.append((name, f"FAIL: {e}", "N/A"))

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, status, dims in results_table:
        print(f"  {name:28s} {status:10s} {dims}")


if __name__ == "__main__":
    main()
