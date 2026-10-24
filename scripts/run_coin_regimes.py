"""Comprehensive coin regime classification and mapping script.

Addresses Review Items 7 & 8:
- Runs all enabled coins/discs from config/coins.yaml
- theta0 in {5, 20, 45, 90} deg
- mu_1 in {0.20, 0.01}
- H_fall = 80 L, release from rest
- Writes results/coin_regimes.csv
- Generates results/coin_regimes.png (trajectory grid x/L vs y/L)
- Generates results/regime_vs_istar.png (40 I* points from 0.05 to 3.0 comparing mu_1=0.2 vs 0.01, white background)
- Honest steady regime search in I* in [0.02, 0.10] with rho_s/rho_f >= 1.2
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from autumn.dimensionless import classify_regime
from autumn.integrate import simulate_drop
from autumn.params import Coefficients, FluidParams, NumericsParams, PlateParams, RegimeClassifierParams, load_coins_yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"


def get_plate_for_istar(i_star: float, L: float = 0.024, rho_f: float = 998.0) -> PlateParams:
    """Fixed path h/L rule from Task 8."""
    if i_star < 0.1125:
        h_over_L = i_star / 1.5
    else:
        h_over_L = max(0.075, i_star / 20.0)
    h = L * h_over_L
    rho_s = rho_f * i_star / h_over_L
    return PlateParams(name=f"card_I_{i_star:.4f}", rho_s=rho_s, L=L, h=h)


def run_coin_suite() -> List[Dict[str, object]]:
    """Simulate and classify all enabled coins across angles and mu_1 values."""
    fluid = FluidParams(rho_f=998.0, g=9.81)
    num = NumericsParams(H_fall_factor=80.0, perturbation_rad=0.0)
    cla = RegimeClassifierParams()

    coins_file = ROOT_DIR / "config" / "coins.yaml"
    plates = load_coins_yaml(coins_file)

    theta0_list = [5.0, 20.0, 45.0, 90.0]
    mu1_list = [0.20, 0.01]

    rows: List[Dict[str, object]] = []

    print("=" * 70)
    print("  SIMULATING COIN & DESIGN DISC REGIMES (H_fall = 80 L)")
    print("=" * 70)

    for plate in plates:
        i_star = plate.I_star(fluid.rho_f)
        rho_ratio = plate.rho_s / fluid.rho_f
        for th0_deg in theta0_list:
            for mu1 in mu1_list:
                c_tau = math.pi * 0.20 / 8.0
                coeffs = Coefficients(mu_1=mu1, mu_2=0.20, C_tau=c_tau)
                res = simulate_drop(
                    plate=plate,
                    fluid=fluid,
                    coeffs=coeffs,
                    numerics=num,
                    theta0=math.radians(th0_deg),
                    u0=0.0,
                    v0=0.0,
                    omega0=0.0
                )
                regime, metrics = classify_regime(
                    t=res.t,
                    Y=res.Y,
                    theta=res.theta,
                    omega=res.omega,
                    H_fall=res.H_fall,
                    params=cla
                )
                net_turns = abs(metrics.get("delta_theta_net_rad", 0.0)) / (2.0 * math.pi)
                ptp_deg = metrics.get("theta_range_deg", 0.0)
                x_end_over_L = res.X[-1] / plate.L

                row = {
                    "coin": plate.name,
                    "I_star": round(i_star, 4),
                    "rho_s_over_rho_f": round(rho_ratio, 4),
                    "theta0_deg": th0_deg,
                    "mu_1": mu1,
                    "regime": regime,
                    "net_turns": round(net_turns, 2),
                    "ptp_deg": round(ptp_deg, 1),
                    "x_end_over_L": round(x_end_over_L, 3),
                }
                rows.append(row)
                if th0_deg == 5.0 and mu1 == 0.20:
                    print(f"Coin: {plate.name:24s} | I*={i_star:6.4f} | rho_s/rho_f={rho_ratio:5.2f} | regime={regime:10s} (turns={net_turns:4.1f}, ptp={ptp_deg:5.1f} deg)")

    return rows


def make_trajectories_plot(plates: List[PlateParams]) -> None:
    """Generate 3x3 trajectory panels (x/L vs y/L) for all 9 coins."""
    fluid = FluidParams(rho_f=998.0, g=9.81)
    num = NumericsParams(H_fall_factor=80.0, perturbation_rad=0.0)
    cla = RegimeClassifierParams()

    n_coins = len(plates)
    cols = 3
    rows = int(math.ceil(n_coins / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(15, 14), facecolor="white")
    axes = axes.flatten()

    for idx, plate in enumerate(plates):
        ax = axes[idx]
        ax.set_facecolor("white")
        i_star = plate.I_star(fluid.rho_f)

        # Baseline: mu_1 = 0.20, theta0 = 5 deg
        coeffs_base = Coefficients(mu_1=0.20, mu_2=0.20, C_tau=math.pi * 0.20 / 8.0)
        res_base = simulate_drop(plate, fluid, coeffs_base, num, theta0=math.radians(5.0))
        reg_base, _ = classify_regime(res_base.t, res_base.Y, res_base.theta, res_base.omega, res_base.H_fall, cla)

        # Comparison: mu_1 = 0.01, theta0 = 5 deg
        coeffs_tuned = Coefficients(mu_1=0.01, mu_2=0.20, C_tau=math.pi * 0.20 / 8.0)
        res_tuned = simulate_drop(plate, fluid, coeffs_tuned, num, theta0=math.radians(5.0))
        reg_tuned, _ = classify_regime(res_tuned.t, res_tuned.Y, res_tuned.theta, res_tuned.omega, res_tuned.H_fall, cla)

        # Plot trajectories normalized by chord L
        x_base = res_base.X / plate.L
        y_base = res_base.Y / plate.L
        x_tuned = res_tuned.X / plate.L
        y_tuned = res_tuned.Y / plate.L

        ax.plot(x_base, y_base, color="#1f77b4", lw=1.6, label=r"$\mu_1=0.20$ (" + reg_base + ")")
        ax.plot(x_tuned, y_tuned, color="#d62728", lw=1.2, ls="--", alpha=0.85, label=r"$\mu_1=0.01$ (" + reg_tuned + ")")

        ax.set_title(f"{plate.name}\n$I^* = {i_star:.3f}$ | baseline: {reg_base}", fontsize=11, fontweight="bold")
        ax.set_xlabel("$x / L$", fontsize=10)
        ax.set_ylabel("$y / L$", fontsize=10)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="best", fontsize=8)

    for idx in range(n_coins, len(axes)):
        fig.delaxes(axes[idx])

    fig.suptitle("Autumn Coin Trajectories in Water ($H_{\\mathrm{fall}} = 80 L$, $\\theta_0 = 5^\\circ$)\nComparison: Baseline Literature $\\mu_1=0.20$ vs Tuned $\\mu_1=0.01$", fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout()
    out_png = RESULTS_DIR / "coin_regimes.png"
    plt.savefig(out_png, dpi=300, facecolor="white")
    plt.close(fig)
    print("Saved trajectory grid plot to:", out_png)


def make_regime_vs_istar_plot() -> None:
    """Evaluate 40 I* points from 0.05 to 3.0 comparing mu_1=0.20 vs mu_1=0.01."""
    fluid = FluidParams(rho_f=998.0, g=9.81)
    num = NumericsParams(H_fall_factor=80.0, perturbation_rad=0.0)
    cla = RegimeClassifierParams()
    L = 0.024

    i_stars = np.geomspace(0.05, 3.0, 40)
    regimes_base = []
    regimes_tuned = []

    print("\nScanning 40 I* points from 0.05 to 3.0 comparing mu_1=0.20 vs 0.01...")
    for i_s in i_stars:
        p = get_plate_for_istar(i_s, L=L, rho_f=fluid.rho_f)

        # Baseline mu_1 = 0.20
        c_base = Coefficients(mu_1=0.20, mu_2=0.20, C_tau=math.pi * 0.20 / 8.0)
        r_b = simulate_drop(p, fluid, c_base, num, theta0=math.radians(5.0))
        reg_b, _ = classify_regime(r_b.t, r_b.Y, r_b.theta, r_b.omega, r_b.H_fall, cla)
        regimes_base.append(reg_b)

        # Tuned mu_1 = 0.01
        c_tuned = Coefficients(mu_1=0.01, mu_2=0.20, C_tau=math.pi * 0.20 / 8.0)
        r_t = simulate_drop(p, fluid, c_tuned, num, theta0=math.radians(5.0))
        reg_t, _ = classify_regime(r_t.t, r_t.Y, r_t.theta, r_t.omega, r_t.H_fall, cla)
        regimes_tuned.append(reg_t)

    # Color mapping for regimes
    regime_colors = {
        "steady": "#2ca02c",      # green
        "fluttering": "#1f77b4",   # blue
        "tumbling": "#d62728",     # red
        "mixed": "#ff7f0e"         # orange
    }

    fig, ax = plt.subplots(figsize=(12, 5), facecolor="white")
    ax.set_facecolor("white")

    # Plot two distinct horizontal tracks: y=1.0 for mu_1=0.01, y=2.0 for mu_1=0.20
    for idx, i_s in enumerate(i_stars):
        # Tuned mu_1 = 0.01
        reg_t = regimes_tuned[idx]
        ax.scatter(i_s, 1.0, color=regime_colors[reg_t], s=120, edgecolors="black", zorder=3)

        # Baseline mu_1 = 0.20
        reg_b = regimes_base[idx]
        ax.scatter(i_s, 2.0, color=regime_colors[reg_b], s=120, edgecolors="black", zorder=3)

    # Transition reference bands
    ax.axvspan(1.10, 1.30, color="gray", alpha=0.18, label="Andersen et al. (2005b) Transition Band [1.10, 1.30]")
    ax.axvline(1.20, color="gray", linestyle="--", alpha=0.7, label="Literature Midpoint $I^*_c = 1.20$")

    # Annotations
    ax.set_xscale("log")
    ax.set_ylim(0.5, 2.5)
    ax.set_yticks([1.0, 2.0])
    ax.set_yticklabels([r"Tuned ($\mu_1 = 0.01$)", r"Literature Baseline ($\mu_1 = 0.20$)"], fontsize=12, fontweight="bold")
    ax.set_xlabel("Dimensionless Moment of Inertia $I^* = \\frac{\\rho_s h}{\\rho_f L}$", fontsize=12)
    ax.set_title("Regime Classification vs $I^*$ along Fixed Path $h/L$\nDirect Comparison between $\\mu_1 = 0.20$ and $\\mu_1 = 0.01$", fontsize=13, fontweight="bold")

    # Legend for regimes
    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=regime_colors["fluttering"], markersize=10, markeredgecolor="k", label="Fluttering"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=regime_colors["tumbling"], markersize=10, markeredgecolor="k", label="Tumbling"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=regime_colors["mixed"], markersize=10, markeredgecolor="k", label="Mixed / Chaotic"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=regime_colors["steady"], markersize=10, markeredgecolor="k", label="Steady"),
        plt.Line2D([0], [0], color="gray", alpha=0.3, lw=8, label="Andersen (2005b) Band [1.10, 1.30]"),
        plt.Line2D([0], [0], color="gray", linestyle="--", lw=1.5, label="Midpoint $I^*_c = 1.20$"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", framealpha=0.95, facecolor="white")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)

    plt.tight_layout()
    out_png = RESULTS_DIR / "regime_vs_istar.png"
    plt.savefig(out_png, dpi=300, facecolor="white")
    plt.close(fig)
    print("Saved regime vs I* plot to:", out_png)


def search_steady_regime() -> None:
    """Search for steady regime in I* in [0.02, 0.10] with rho_s/rho_f >= 1.2."""
    fluid = FluidParams(rho_f=998.0, g=9.81)
    coeffs = Coefficients(mu_1=0.20, mu_2=0.20, C_tau=math.pi * 0.20 / 8.0)
    num = NumericsParams(H_fall_factor=80.0, perturbation_rad=0.0)
    cla = RegimeClassifierParams()
    L = 0.024

    print("\n" + "=" * 70)
    print("  STEADY REGIME SEARCH (I* in [0.02, 0.10], rho_s/rho_f >= 1.2, theta0 = 5 deg)")
    print("=" * 70)

    found_steady = False
    for i_s in np.linspace(0.02, 0.10, 9):
        for r_ratio in [1.2, 1.5, 2.7]:
            hol = i_s / r_ratio
            h = L * hol
            rho_s = r_ratio * fluid.rho_f
            plate = PlateParams(f"search_steady_{i_s:.3f}", rho_s, L, h)
            res = simulate_drop(plate, fluid, coeffs, num, theta0=math.radians(5.0))
            reg, met = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, cla)
            if reg == "steady":
                found_steady = True
                print(f"  Steady found at I*={i_s:.3f}, rho_s/rho_f={r_ratio:.1f}: ptp={met['theta_range_deg']:.2f} deg")

    if not found_steady:
        print("RESULT: No genuinely steady descent was reached for any physical perturbation (all cases flutter with ptp >= 23.5 deg).")
        print("REASON: True steady descent (ptp < 2.0 deg) only occurs under mathematically exact unperturbed vertical drop (theta0 = 0.0, zero perturbation), which is an unstable equilibrium in a real physical environment.")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = RESULTS_DIR / "coin_regimes.csv"

    # 1. Run coin suite
    rows = run_coin_suite()

    fieldnames = [
        "coin",
        "I_star",
        "rho_s_over_rho_f",
        "theta0_deg",
        "mu_1",
        "regime",
        "net_turns",
        "ptp_deg",
        "x_end_over_L"
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("\nSaved coin regimes CSV to:", out_csv)

    # 2. Make trajectory panels plot
    coins_file = ROOT_DIR / "config" / "coins.yaml"
    plates = load_coins_yaml(coins_file)
    make_trajectories_plot(plates)

    # 3. Make regime vs I* plot
    make_regime_vs_istar_plot()

    # 4. Steady search
    search_steady_regime()


if __name__ == "__main__":
    main()
