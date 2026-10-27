#!/usr/bin/env python
"""Paper-ready figures regenerated from the committed data (no invented curves).

Run from the repository root:

    PYTHONPATH=src python scripts/make_paper_figures.py

Output: results/paper_figures/F*.png and F*.pdf (300 dpi, white background, dark text).

Rules followed by every figure:
  * every curve or point comes from a CSV in results/ or results_sph/, or from a
    simulation run inside this script;
  * legends never cover data (they sit outside the axes or below them);
  * trajectories use equal aspect ratio;
  * values copied from the literature are labelled "as cited, not yet checked against the paper".
"""

from __future__ import annotations

import dataclasses
import math
import sys
import traceback
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from autumn.integrate import simulate_drop  # noqa: E402
from autumn.params import PlateParams, SimulationConfig, get_default_config_path  # noqa: E402

RES = ROOT / "results"
SPH = ROOT / "results_sph"
OUT = RES / "paper_figures"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#1a1a1a"
COL = {
    "steady": "#2ca02c",
    "fluttering": "#1f77b4",
    "tumbling": "#d62728",
    "mixed": "#ff7f0e",
    "undetermined": "#8c8c8c",
}
MK = {"steady": "o", "fluttering": "^", "tumbling": "D", "mixed": "s", "undetermined": "X"}
ORDER = ["steady", "fluttering", "tumbling", "mixed", "undetermined"]
FOOT = "2D quasi-steady model simulation"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.edgecolor": INK,
        "font.size": 11,
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 11.5,
        "legend.fontsize": 10,
        "lines.linewidth": 2.0,
        "grid.color": "#cfcfcf",
        "grid.linestyle": "--",
        "grid.alpha": 0.7,
    }
)


def save(fig: plt.Figure, name: str, footer: str | None = FOOT) -> None:
    if footer:
        fig.text(0.995, 0.005, footer, ha="right", va="bottom", fontsize=8, color="#555555")
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  saved", name)


def regime_legend_handles(present=None):
    names = present or ORDER
    return [
        Line2D([0], [0], marker=MK[r], color="none", markerfacecolor=COL[r], markeredgecolor="black",
               markersize=10, label=r.capitalize())
        for r in names
    ]


# --------------------------------------------------------------------------------------
# F01 regime vs I* strip + I*_c versus mu_1
# --------------------------------------------------------------------------------------
def f01_regime_strip():
    rm = pd.read_csv(RES / "regime_map.csv").groupby("I_star", as_index=False).first()
    sens = pd.read_csv(RES / "mu1_sensitivity.csv")
    sens = sens[sens.theta0_deg == sens.theta0_deg.min()].sort_values("mu_1")

    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 9.2), gridspec_kw={"height_ratios": [1.0, 1.0, 1.5], "hspace": 0.55})

    def strip(ax, lo, hi, size):
        for r in ORDER:
            s = rm[(rm.regime == r) & (rm.I_star >= lo) & (rm.I_star <= hi)]
            if len(s):
                ax.scatter(s.I_star, np.zeros(len(s)), s=size, marker=MK[r], c=COL[r], edgecolors="black", linewidths=0.8, zorder=3)
        ax.set_ylim(-0.6, 0.6)
        ax.set_yticks([])
        ax.grid(True, axis="x", which="both")

    strip(a1, 0.04, 4.0, 120)
    a1.set_xscale("log")
    a1.set_xlim(0.04, 4.5)
    a1.axvspan(1.14, 1.38, color="#bbbbbb", alpha=0.35, zorder=0)
    a1.set_title(r"(a) Regime versus $I^*$ at $\mu_1=0.20$, $\theta_0=20^\circ$ (one thickness path $h/L(I^*)$)")
    a1.set_xlabel(r"$I^*=\rho_s h/(\rho_f L)$")

    strip(a2, 0.95, 1.9, 190)
    a2.set_xlim(0.95, 1.9)
    a2.axvspan(1.14, 1.38, color="#bbbbbb", alpha=0.35, zorder=0)
    a2.text(1.26, 0.52, "experimental cards (as cited):\nflutter at 1.14, tumble at 1.38", ha="center", va="top", fontsize=9)
    a2.set_title(r"(b) Zoom on the transition region (linear axis)")
    a2.set_xlabel(r"$I^*$")

    ypos = np.arange(len(sens))
    for y, (_, row) in zip(ypos, sens.iterrows()):
        a3.errorbar([row.I_star_c], [y], xerr=[[row.I_star_c - row.I_star_lower], [row.I_star_upper - row.I_star_c]],
                    fmt="o", color="#333333", ms=9, capsize=3)
        a3.text(row.I_star_c + 0.012, y + 0.18, f"{row.I_star_c:.3f}", va="center", fontsize=10)
    a3.axvspan(1.14, 1.38, color="#bbbbbb", alpha=0.35, zorder=0)
    a3.set_xlim(0.95, 1.9)
    a3.set_yticks(ypos)
    a3.set_yticklabels([rf"$\mu_1={m:g}$" for m in sens.mu_1])
    a3.set_xlabel(r"$I^*_c$")
    a3.set_title(r"(c) Flutter-to-tumble onset $I^*_c$ (bisection bracket) for each $\mu_1$")
    a3.grid(True, axis="x")
    a3.set_ylim(-0.7, len(sens) - 0.3)
    present = [r for r in ORDER if r in set(rm.regime)]
    fig.legend(handles=regime_legend_handles(present), loc="lower center", ncol=len(present), frameon=False,
               bbox_to_anchor=(0.5, 0.0))
    save(fig, "F01_regime_vs_istar")


# --------------------------------------------------------------------------------------
# F02 regime map (I*, Re_meas)
# --------------------------------------------------------------------------------------
def f02_regime_map():
    d = pd.read_csv(RES / "regime_map.csv")
    fig, ax = plt.subplots(figsize=(9.6, 6.2))
    ax.axvspan(5000, d.Re_meas.max() * 1.6, color="#e6e6e6", alpha=0.8, zorder=0)
    ax.axvline(5000, color="#8b0000", ls="--", lw=1.4)
    ax.text(5200, 0.052, "Re > 5000: outside the\nfitted range of the force laws", fontsize=9, color="#8b0000", va="bottom")
    for r in ORDER:
        s = d[d.regime == r]
        if len(s):
            ax.scatter(s.Re_meas, s.I_star, s=70, marker=MK[r], c=COL[r], edgecolors="black", linewidths=0.6, alpha=0.95, label=r.capitalize(), zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\mathrm{Re}_{\mathrm{meas}}=\rho_f U_{\mathrm{mean}} L/\mu$ (computed after each run)")
    ax.set_ylabel(r"$I^*=\rho_s h/(\rho_f L)$")
    ax.set_title(r"Regime map in the $(\mathrm{Re}_{\mathrm{meas}},\,I^*)$ plane")
    ax.grid(True, which="both")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, title="Regime")
    fig.text(0.5, -0.02, "The ODE has no viscosity, so Re is an output: points at equal $I^*$ differ only through the chord length "
             "(four chords per $I^*$).", ha="center", fontsize=9, color="#444444")
    save(fig, "F02_regime_map_Re_istar")


# --------------------------------------------------------------------------------------
# F03 coin trajectories (first 60 time units, equal aspect, ghost chords)
# --------------------------------------------------------------------------------------
def _coins():
    cfg = yaml.safe_load(open(ROOT / "config" / "coins.yaml", encoding="utf-8"))
    out = []
    for c in cfg["coins"]:
        if not c.get("enabled", True):
            continue
        L = c["diameter_mm"] * 1e-3
        h = c["thickness_mm"] * 1e-3
        if c.get("rho_s_kgm3"):
            rho = float(c["rho_s_kgm3"])
        else:
            rho = c["mass_g"] * 1e-3 / (math.pi * (L / 2) ** 2 * h)
        out.append(dict(id=c["id"], label=c["label"], L=L, h=h, rho=rho))
    return out


def f03_coin_trajectories(cfg: SimulationConfig):
    labels = pd.read_csv(RES / "coin_regimes.csv")
    labels = labels[(np.isclose(labels.mu_1, 0.2)) & (np.isclose(labels.theta0_deg, 5.0))].set_index("coin")
    coins = _coins()
    fig, axs = plt.subplots(3, 3, figsize=(14, 14.5))
    for ax, c in zip(axs.ravel(), coins):
        a = c["L"] / 2
        U0 = math.sqrt(max(c["rho"] / cfg.fluid.rho_f - 1.0, 0.0) * cfg.fluid.g * c["h"] / 2)
        tau0 = a / U0
        num = dataclasses.replace(cfg.numerics, H_fall_factor=1e6, perturbation_rad=1e-3, dt_out=0.02 * tau0)
        r = simulate_drop(PlateParams(c["id"], c["rho"], c["L"], c["h"]), cfg.fluid, cfg.coefficients, num,
                          theta0=math.radians(5.0), t_max_override=60 * tau0)
        x, y, th, t = r.X / a, r.Y / a, r.theta, r.t / tau0
        ax.plot(x, y, color="#1f4e9c", lw=1.4)
        for tg in np.arange(0, 60.01, 2.0):
            i = int(np.argmin(np.abs(t - tg)))
            ax.plot([x[i] - np.cos(th[i]), x[i] + np.cos(th[i])], [y[i] - np.sin(th[i]), y[i] + np.sin(th[i])],
                    color="#777777", lw=1.0, alpha=0.9)
        ax.plot(x[0], y[0], "o", color="#2ca02c", ms=7, zorder=5)
        ax.plot(x[-1], y[-1], "o", color="#d62728", ms=6, zorder=5)
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True)
        ax.set_xlabel(r"$x/a$")
        ax.set_ylabel(r"$y/a$")
        reg = labels.loc[c["id"], "regime"] if c["id"] in labels.index else "?"
        ist = c["rho"] * c["h"] / (cfg.fluid.rho_f * c["L"])
        ax.set_title(f"{c['label']}\n$I^*={ist:.3f}$, classified {reg}", fontsize=11)
    fig.suptitle(r"Coin trajectories, first 60 time units ($a/U_0$), $\mu_1=0.20$, $\theta_0=5^\circ$ (+1e-3 rad)", y=0.995, fontsize=14,
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "F03_coin_trajectories")


# --------------------------------------------------------------------------------------
# F05 literature checks (no invented zones)
# --------------------------------------------------------------------------------------
CZK = [  # copied from scripts/make_literature_validation.py (values from the ondrej-cloud repository)
    ("1 CZK", 8291, 0.0284), ("2 CZK", 9337, 0.0235), ("5 CZK", 10488, 0.0249),
    ("10 CZK", 11760, 0.0323), ("20 CZK", 11291, 0.0303), ("50 CZK", 10904, 0.0295),
]
WASH = [("small hole", 11895, 0.0111), ("medium hole", 10133, 0.0111), ("large hole", 9434, 0.0124), ("original", 16290, 0.0346)]
G32 = 64.0 / math.pi


def f05_literature():
    rm = pd.read_csv(RES / "regime_map.csv")
    lit = pd.read_csv(RES / "literature_validation.csv")
    fig, axs = plt.subplots(1, 3, figsize=(20, 6.4))
    ax = axs[0]
    ax.axvspan(5000, 30000, color="#e6e6e6", alpha=0.8, zorder=0)
    ax.axvline(5000, color="#8b0000", ls="--", lw=1.3)
    for r in ORDER:
        s = rm[rm.regime == r]
        if len(s):
            ax.scatter(s.Re_meas, s.I_star, s=38, marker=MK[r], c=COL[r], edgecolors="black", linewidths=0.4, alpha=0.8, zorder=3)
    ys = [0.80, 0.70, 0.62, 0.55, 0.48, 0.42]
    pts = sorted([(n, re, i * G32) for n, re, i in CZK], key=lambda p: -p[2])
    for (n, re, i2), yt in zip(pts, ys):
        ax.scatter(re, i2, marker="o", s=70, c="white", edgecolors="black", linewidths=1.6, zorder=6)
        ax.annotate(n, (re, i2), xytext=(19500, yt), textcoords="data", fontsize=9, va="center",
                    arrowprops=dict(arrowstyle="-", color="#666666", lw=0.8))
    wy = {"small hole": 0.17, "medium hole": 0.14, "large hole": 0.115, "original": 1.05}
    for n, re, i3 in WASH:
        ax.scatter(re, i3 * G32, marker="P", s=80, c="white", edgecolors="black", linewidths=1.6, zorder=6)
        ax.annotate("washer: " + n, (re, i3 * G32), xytext=(19500, wy[n]), textcoords="data", fontsize=9, va="center",
                    arrowprops=dict(arrowstyle="-", color="#666666", lw=0.8))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(200, 60000)
    ax.set_ylim(0.05, 5)
    ax.set_xlabel("Re")
    ax.set_ylabel(r"$I^*_{2D}=(64/\pi)\,I^*_{3D}$ for the experiments")
    ax.set_title("(a) ODE regimes and the ondrej-cloud\ncoins and washers (open symbols)", fontsize=12)
    ax.grid(True, which="both")
    h = regime_legend_handles([r for r in ORDER if r in set(rm.regime)])
    h += [Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor="black", markersize=9, label="experiment (coin)"),
          Line2D([0], [0], marker="P", color="none", markerfacecolor="white", markeredgecolor="black", markersize=9, label="experiment (washer)")]
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False, fontsize=9)

    ax = axs[1]
    ax.plot(lit.I_star, lit.U_mean_div_Ut, "o-", color="#1f4e9c", label=r"2D ODE")
    ax.errorbar([1.14], [0.54], yerr=[0.05], fmt="s", color="#2ca02c", ms=9, capsize=4, label="card 1, flutter (as cited)")
    ax.errorbar([1.38], [0.62], yerr=[0.06], fmt="D", color="#d62728", ms=9, capsize=4, label="card 2, tumble (as cited)")
    ax.set_xscale("log")
    ax.set_xlabel(r"$I^*$")
    ax.set_ylabel(r"$U_{\mathrm{mean}}/U_t$")
    ax.set_xticks([0.1, 0.2, 0.5, 1, 2])
    ax.set_xticklabels(["0.1", "0.2", "0.5", "1", "2"])
    ax.minorticks_off()
    ax.set_title(r"(b) Descent speed ratio", fontsize=12)
    ax.grid(True, which="both")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=1, frameon=False, fontsize=9)

    ax = axs[2]
    fl = lit[lit.regime == "fluttering"]
    ax.plot(fl.I_star, fl.Strouhal_St, "s-", color="#1f4e9c", label=r"2D ODE, fluttering runs")
    ax.axhspan(0.18, 0.22, color="#999999", alpha=0.3, label=r"$\mathrm{St}\approx0.18$-$0.22$ (as cited)")
    ax.set_xscale("log")
    ax.set_ylim(0, max(0.55, float(fl.Strouhal_St.max()) * 1.1))
    ax.set_xlabel(r"$I^*$")
    ax.set_ylabel(r"$\mathrm{St}=fL/U_{\mathrm{mean}}$")
    ax.set_xticks([0.1, 0.2, 0.5, 1])
    ax.set_xticklabels(["0.1", "0.2", "0.5", "1"])
    ax.minorticks_off()
    ax.set_title(r"(c) Flutter Strouhal number", fontsize=12)
    ax.grid(True, which="both")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=1, frameon=False, fontsize=9)
    fig.suptitle("Comparison with published data (cited values are not yet checked against the papers)", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save(fig, "F05_literature_comparison")


# --------------------------------------------------------------------------------------
# F06 - F10 sweeps
# --------------------------------------------------------------------------------------
def f06_istar_sweep():
    d = pd.read_csv(RES / "sweeps" / "i_star_sweep" / "i_star_sweep.csv")
    fig, axs = plt.subplots(1, 3, figsize=(17, 5.2))
    for r in ORDER:
        s = d[d.regime == r]
        if len(s):
            for ax, col in zip(axs[1:], ["mean_speed_ms", "lateral_drift_m"]):
                ax.scatter(s.I_star, s[col], s=70, marker=MK[r], c=COL[r], edgecolors="black", linewidths=0.6, zorder=3)
            axs[0].scatter(s.I_star, [ORDER.index(r)] * len(s), s=70, marker=MK[r], c=COL[r], edgecolors="black", linewidths=0.6, zorder=3)
    axs[1].plot(d.I_star, d.mean_speed_ms, color="#999999", lw=1, zorder=1)
    axs[2].plot(d.I_star, d.lateral_drift_m, color="#999999", lw=1, zorder=1)
    present = [r for r in ORDER if r in set(d.regime)]
    axs[0].set_yticks([ORDER.index(r) for r in present])
    axs[0].set_yticklabels([r.capitalize() for r in present])
    axs[0].set_ylabel("Regime")
    axs[1].set_ylabel("Mean descent speed [m/s]")
    axs[2].set_ylabel("Net lateral drift $|X_{final}|$ [m]")
    for ax, t in zip(axs, ["(a) Regime", "(b) Descent speed", "(c) Lateral drift"]):
        ax.set_xscale("log")
        ax.set_xlabel(r"$I^*$")
        ax.set_title(t)
        ax.grid(True, which="both")
    fig.tight_layout()
    save(fig, "F06_istar_sweep")


def f07_spectrum():
    d = pd.read_csv(RES / "sweeps" / "i_star_sweep" / "flutter_frequency_analysis.csv")
    m = d.freq_Hz <= 6
    f, p = d.freq_Hz[m].values, d.psd[m].values
    i = int(np.argmax(p[1:]) + 1)
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(f, p, color="#1f4e9c")
    ax.axvline(f[i], color="#d62728", ls="--")
    ax.annotate(f"peak {f[i]:.2f} Hz", (f[i], p[i]), xytext=(f[i] + 0.6, p[i] * 0.9), arrowprops=dict(arrowstyle="->"), fontsize=11)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel(r"PSD of $\theta(t)$ [rad$^2$/Hz]")
    ax.set_title("Flutter spectrum (0-6 Hz)")
    ax.grid(True)
    save(fig, "F07_flutter_spectrum")


def f08_energy():
    d = pd.read_csv(RES / "sweeps" / "i_star_sweep" / "energy_budget_reconciliation.csv")
    k = max(1, len(d) // 2500)
    d = d.iloc[::k]
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 5.2))
    a.plot(d.t_s, d.E_kin_Jm, label="kinetic")
    a.plot(d.t_s, d.E_pot_Jm, label="potential")
    a.plot(d.t_s, d.W_diss_Jm, label="dissipated")
    a.plot(d.t_s, d.E_total_Jm, "k--", label="total (should stay at 0)")
    a.set_xlim(0, d.t_s.max())
    a.set_xlabel("Time [s]")
    a.set_ylabel("Energy per unit depth [J/m]")
    a.set_title("(a) Energy budget")
    a.grid(True)
    a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False, fontsize=9.5)
    b.plot(d.t_s, d.residual_pct.abs(), color="#d62728")
    b.axhline(1.0, color="#555555", ls=":", label="1 % acceptance limit")
    b.set_xlim(0, d.t_s.max())
    b.set_ylim(0, 1.1)
    b.set_xlabel("Time [s]")
    b.set_ylabel("|energy residual| [%]")
    b.set_title(f"(b) Closure residual (max {d.residual_pct.abs().max():.1e} %)")
    b.grid(True)
    b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), frameon=False, fontsize=9.5)
    fig.tight_layout()
    save(fig, "F08_energy_budget")


def f09_release_angle():
    d = pd.read_csv(RES / "sweeps" / "release_angle_sweep" / "release_angle_sweep.csv")
    cases = [("low_I_0.2", r"$I^*=0.2$"), ("mid_I_0.8", r"$I^*=0.8$"), ("high_I_3.5", r"$I^*=3.5$")]
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 5.2))
    for (k, lab), c in zip(cases, ["#1f77b4", "#2ca02c", "#d62728"]):
        a.plot(d.angle_deg, d[f"{k}_drift_mm"].abs(), "o-", color=c, label=lab, ms=5)
        b.plot(d.angle_deg, d[f"{k}_speed_ms"], "o-", color=c, label=lab, ms=5)
    a.set_yscale("symlog", linthresh=10)
    a.set_xlabel(r"Release angle $\theta_0$ [deg]")
    a.set_ylabel("Net lateral drift $|X_{final}|$ [mm]")
    a.set_title("(a) Lateral drift")
    b.set_xlabel(r"Release angle $\theta_0$ [deg]")
    b.set_ylabel("Mean descent speed [m/s]")
    b.set_title("(b) Descent speed")
    for ax in (a, b):
        ax.grid(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    fig.tight_layout()
    save(fig, "F09_release_angle_sweep")


def f10_landing():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    for ax, (k, lab) in zip(axs, [("low_I_0.2", r"$I^*=0.2$"), ("mid_I_0.8", r"$I^*=0.8$"), ("high_I_3.5", r"$I^*=3.5$")]):
        d = pd.read_csv(RES / "sweeps" / "chaos_ensemble" / f"chaos_ensemble_{k}.csv")
        x = d.landing_X_mm.values
        ax.hist(x, bins=12, color="#f2a65a", edgecolor="black")
        ax.axvline(x.mean(), color="black", ls="--", label=f"mean {x.mean():.0f} mm")
        ax.axvspan(x.mean() - x.std(), x.mean() + x.std(), color="#999999", alpha=0.25, label=f"std {x.std():.0f} mm")
        ax.set_xlabel("Landing position X at 1 m depth [mm]")
        ax.set_title(f"{lab}, {len(x)} perturbed drops")
        ax.grid(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=9.5)
    axs[0].set_ylabel("Number of drops")
    fig.tight_layout()
    save(fig, "F10_landing_scatter")


# --------------------------------------------------------------------------------------
# F11 - F13 SPH (real data only)
# --------------------------------------------------------------------------------------
def f11_sph_vs_ode(cfg: SimulationConfig):
    cases = [("flutter_I068", 0.68, "Fluttering case"), ("tumble_I135", 1.35, "Tumbling case")]
    L, h = 0.024, 0.0018
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.4))
    for ax, (name, ist, ttl) in zip(axs, cases):
        s = pd.read_csv(SPH / "drops" / f"sph_{name}.csv")
        rho = ist * cfg.fluid.rho_f * L / h
        th0 = float(s.theta.iloc[0])
        num = dataclasses.replace(cfg.numerics, H_fall_factor=1e6, perturbation_rad=0.0, dt_out=0.002)
        r = simulate_drop(PlateParams(name, rho, L, h), cfg.fluid, cfg.coefficients, num, theta0=th0, t_max_override=2.5)
        ax.plot(r.t, np.degrees(r.theta), "--", color="#444444", lw=1.8, label="2D ODE")
        ax.plot(s.t, np.degrees(s.theta), color="#d62728", lw=2.6, label=f"2D SPH (run length {s.t.iloc[-1]:.2f} s)")
        ax.axvline(s.t.iloc[-1], color="#d62728", ls=":", lw=1)
        ax.set_xlabel("Time [s]")
        ax.set_ylabel(r"Tilt angle $\theta$ [deg]")
        ax.set_title(f"{ttl}, $I^*={ist}$")
        ax.grid(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
    fig.suptitle("SPH versus ODE tilt angle, same plate and release angle (SPH covers only the part before the dotted line)",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    save(fig, "F11_sph_vs_ode_tilt", footer="2D SPH-FSI and 2D quasi-steady ODE, measured data")


def f12_sph_viscosity():
    v = pd.read_csv(SPH / "comparison" / "viscosity_sweep_Re.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 5.2))
    for (_, row), c in zip(v.iterrows(), ["#d62728", "#9467bd", "#ff7f0e", "#2ca02c"]):
        s = pd.read_csv(SPH / "drops" / f"sph_visc_Re{int(row.Re_in)}.csv")
        a.plot(s.t, np.degrees(s.theta), color=c, label=rf"$\mathrm{{Re}}_{{in}}={int(row.Re_in)}$")
    a.set_xlabel("Time [s]")
    a.set_ylabel(r"Tilt angle $\theta$ [deg]")
    a.set_title(r"(a) SPH tilt angle, $I^*=0.65$ (0.35 s runs)")
    a.grid(True)
    a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False, fontsize=9.5)
    b.plot(v.Re_in, v.U_mean_m_s, "o", color="#1f4e9c", ms=9)
    b.set_xscale("log")
    b.set_xlabel(r"Input Reynolds number $\mathrm{Re}_{in}$")
    b.set_ylabel("Mean descent speed [m/s]")
    b.set_title("(b) Mean speed (four runs, no trend claimed)")
    b.grid(True, which="both")
    fig.tight_layout()
    save(fig, "F12_sph_viscosity_sweep", footer="2D SPH-FSI, measured data")


def f13_sph_problem_tests():
    t4 = pd.read_csv(SPH / "validation" / "test4_dam_break.csv")
    t5 = pd.read_csv(SPH / "validation" / "test5_cylinder_drag.csv")
    t7 = pd.read_csv(SPH / "validation" / "test7_resolution_study.csv")
    fig, axs = plt.subplots(1, 3, figsize=(18, 5.4))
    a = axs[0]
    a.plot(t4.tau_dimensionless, t4.x_front_over_w0, color="#1f4e9c", lw=2, label="SPH front")
    a.text(0.05, 0.90, "Qualitative demonstration only\n(Martin & Moyce 1952 table\nunverified in references.md)",
           transform=a.transAxes, fontsize=9.5, verticalalignment="top",
           bbox=dict(boxstyle="round,pad=0.4", facecolor="#f0f0f0", edgecolor="#888888", alpha=0.85))
    a.set_xlabel(r"$\tau=t\sqrt{g/W_0}$")
    a.set_ylabel(r"$X_{front}/W_0$")
    a.set_title("(a) Test 4, dam break (QUALITATIVE)")
    a.grid(True)
    a.legend(loc="lower right", frameon=False, fontsize=9.5)
    b = axs[1]
    bench = {}
    for _, row in t5.iterrows():
        parts = str(row["steady_benchmark"]).split("-")
        bench[int(row["Re"])] = (float(parts[0]), float(parts[1]))
    xs = np.arange(len(t5))
    cd_col = "CD_measured_t002s" if "CD_measured_t002s" in t5.columns else ("CD_measured" if "CD_measured" in t5.columns else t5.columns[1])
    b.bar(xs - 0.2, t5[cd_col], 0.38, color="#3b4cc0", label="SPH measured (t = 0.02 s)")
    for x, re in zip(xs, t5.Re):
        lo, hi = bench[int(re)]
        b.bar(x + 0.2, (lo + hi) / 2, 0.38, color="#f2a65a", yerr=(hi - lo) / 2, capsize=4, label="literature range (CSV)" if x == 0 else None)
    for x, (_, row) in zip(xs, t5.iterrows()):
        lo, hi = bench[int(row.Re)]
        meas_val = float(row[cd_col])
        b.text(x - 0.2, meas_val * 1.08, f"x{meas_val / ((lo + hi) / 2):.1f}", ha="center", fontsize=10)
    b.set_yscale("log")
    b.set_xticks(xs)
    b.set_xticklabels([f"Re = {int(r)}" for r in t5.Re])
    b.set_ylabel(r"Drag coefficient $C_D$")
    b.set_title("(b) Test 5, cylinder drag (FAIL: ~5x benchmark)")
    b.grid(True, axis="y", which="both")
    b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9.5)
    c = axs[2]
    c.plot(t7.N_h, t7.U_mean_m_s, "o-", color="#1f4e9c", ms=9)
    for _, r in t7.iterrows():
        c.annotate(str(r.grid_label), (r.N_h, r.U_mean_m_s), xytext=(6, 8), textcoords="offset points", fontsize=9)
    c.set_xlabel(r"Particles across the thickness $N_h$")
    c.set_ylabel(r"$U_{mean}$ [m/s]")
    c.set_title("(c) Test 7, resolution study (FAIL)")
    c.grid(True)
    fig.tight_layout()
    save(fig, "F13_sph_validation_problem_tests", footer="2D SPH-FSI, measured data")


def main():
    cfg = SimulationConfig.from_yaml(get_default_config_path("base.yaml"))
    jobs = [
        ("F01", f01_regime_strip), ("F02", f02_regime_map), ("F03", lambda: f03_coin_trajectories(cfg)),
        ("F05", f05_literature), ("F06", f06_istar_sweep), ("F07", f07_spectrum), ("F08", f08_energy),
        ("F09", f09_release_angle), ("F10", f10_landing), ("F11", lambda: f11_sph_vs_ode(cfg)),
        ("F12", f12_sph_viscosity), ("F13", f13_sph_problem_tests),
    ]
    only = set(sys.argv[1:])
    for name, fn in jobs:
        if only and name not in only:
            continue
        try:
            print(name)
            fn()
        except Exception:
            print("  FAILED", name)
            traceback.print_exc()


if __name__ == "__main__":
    main()
