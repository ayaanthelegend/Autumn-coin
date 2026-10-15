"""Validation against literature and third-party experimental datasets.

References:
    1. Andersen, A., Pesavento, U., & Wang, Z. J. (2005a).
       Unsteady aerodynamics of fluttering and tumbling plates.
       J. Fluid Mech., 541, 65-90. DOI: 10.1017/S002211200500594X.
    2. Andersen, A., Pesavento, U., & Wang, Z. J. (2005b).
       Analysis of transitions between fluttering, tumbling and steady descent of falling cards.
       J. Fluid Mech., 541, 91-104. DOI: 10.1017/S0022112005005847.
    3. Field, S., Klaus, M., Moore, M. G., & O'Reilly, F. (1997).
       Chaotic dynamics of falling disks.
       Phys. Rev. Lett., 78(10), 1896-1899. DOI: 10.1103/PhysRevLett.78.1896.
    4. ondrej-cloud/autumn-coin (2026).
       3D stereo video tracking of coins falling through water (fluttering & tumbling).
       GitHub repository: https://github.com/ondrej-cloud/autumn-coin (MIT License).
       Experimental data from Czech Young Physicists' Tournament (TMF / IYPT Problem 12).
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from autumn.dimensionless import compute_reynolds_number, compute_strouhal_number
from autumn.integrate import simulate_drop
from autumn.metrics import compute_fft_frequency
from autumn.params import PlateParams, SimulationConfig, get_default_config_path
from autumn.plotting import save_figure_and_csv


def run_literature_validation(
    config: SimulationConfig,
    out_dir: Path | str = "results"
) -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. Experimental Data from ondrej-cloud/autumn-coin (MIT License)
    # -------------------------------------------------------------
    # 6 Czech coins (3D circular disks falling in water):
    coins_data = [
        {"name": "1 CZK",  "mass_g": 3.60, "d_mm": 20.0, "Re": 8291,  "I_star_3D": 0.0284, "regime_exp": "tumbling/chaotic"},
        {"name": "2 CZK",  "mass_g": 3.70, "d_mm": 21.5, "Re": 9337,  "I_star_3D": 0.0235, "regime_exp": "tumbling/chaotic"},
        {"name": "5 CZK",  "mass_g": 4.80, "d_mm": 23.0, "Re": 10488, "I_star_3D": 0.0249, "regime_exp": "tumbling/chaotic"},
        {"name": "10 CZK", "mass_g": 7.62, "d_mm": 24.5, "Re": 11760, "I_star_3D": 0.0323, "regime_exp": "tumbling/chaotic"},
        {"name": "20 CZK", "mass_g": 8.42, "d_mm": 26.0, "Re": 11291, "I_star_3D": 0.0303, "regime_exp": "tumbling/chaotic"},
        {"name": "50 CZK", "mass_g": 9.70, "d_mm": 27.5, "Re": 10904, "I_star_3D": 0.0295, "regime_exp": "tumbling/chaotic"},
    ]

    # Washers from ondrej-cloud/autumn-coin (perforated disks with holes reducing effective I*):
    washers_data = [
        {"name": "Washer (Small hole)",    "Re": 11895, "I_star_3D": 0.0111, "regime_exp": "fluttering"},
        {"name": "Washer (Medium hole)",   "Re": 10133, "I_star_3D": 0.0111, "regime_exp": "fluttering"},
        {"name": "Washer (Large hole)",    "Re": 9434,  "I_star_3D": 0.0124, "regime_exp": "fluttering"},
        {"name": "Original Washer",        "Re": 16290, "I_star_3D": 0.0346, "regime_exp": "tumbling"},
    ]

    # Geometric conversion between 3D disk inertia and 2D plate inertia:
    # For a 3D solid circular disk: I_3D = (pi / 64) * rho_s * h * d^4
    # Dimensionless moment of inertia in Field et al. (1997): I*_3D = I_3D / (rho_f * d^5) = (pi / 64) * (rho_s * h) / (rho_f * d)
    # For a 2D plate: I*_2D = (rho_s * h) / (rho_f * L)
    # Therefore: I*_2D = (64 / pi) * I*_3D \approx 20.37 * I*_3D
    geom_factor_3D_to_2D = 64.0 / math.pi

    # -------------------------------------------------------------
    # 2. Benchmark Simulation of 2D ODE over I* Sweep
    # -------------------------------------------------------------
    print("Running 2D ODE sweeps for benchmark comparison with Andersen et al. (2005a,b)...")
    L_ref = 0.024
    i_star_test = np.geomspace(0.08, 3.5, 20)
    ode_i_stars = []
    ode_u_ratio = []
    ode_st = []
    ode_re = []
    ode_regimes = []

    for i_s in i_star_test:
        aspect = float(np.clip(0.045 + 0.05 * np.sqrt(i_s), 0.035, 0.14))
        h = L_ref * aspect
        rho_s = float(i_s * config.fluid.rho_f / aspect)
        plate = PlateParams(f"val_I_{i_s:.2f}", rho_s, L_ref, h)
        th0 = np.radians(20.0)

        res = simulate_drop(plate, config.fluid, config.coefficients, config.numerics, theta0=th0)

        t_crop = res.t[res.t >= 0.2 * res.t[-1]]
        th_crop = res.theta[res.t >= 0.2 * res.t[-1]]
        u_mean = float(np.mean(res.speed[res.t >= 0.2 * res.t[-1]]))
        u_t = math.sqrt(max(rho_s / config.fluid.rho_f - 1.0, 0.0) * config.fluid.g * h)
        u_ratio = u_mean / (u_t + 1e-9)

        re = compute_reynolds_number(config.fluid.rho_f, u_mean, L_ref, config.fluid.mu)

        # FFT dominant frequency in post-transient window
        freqs, psd, f_dom = compute_fft_frequency(t_crop, th_crop)
        st = compute_strouhal_number(f_dom, L_ref, u_mean)

        from autumn.dimensionless import classify_regime
        reg, _ = classify_regime(res.t, res.Y, res.theta, res.omega, res.H_fall, config.regime_classifier)

        ode_i_stars.append(i_s)
        ode_u_ratio.append(u_ratio)
        ode_st.append(st)
        ode_re.append(re)
        ode_regimes.append(reg)

    ode_i_stars = np.array(ode_i_stars)
    ode_u_ratio = np.array(ode_u_ratio)
    ode_st = np.array(ode_st)
    ode_re = np.array(ode_re)

    # -------------------------------------------------------------
    # 3. Create 3-Panel Validation Figure
    # -------------------------------------------------------------
    fig, axs = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle("Validation of 2D Quasi-Steady ODE against Literature & Third-Party Experiments", fontsize=14, fontweight="bold")

    # --- Panel (a): Phase Diagram Comparison (Field et al. 1997 / ondrej-cloud vs 2D ODE) ---
    ax0 = axs[0]
    re_mesh = np.logspace(2.3, 4.3, 300)

    # 3D disk boundaries from Field et al. (1997) and ondrej-cloud:
    # Scaled to equivalent 2D plate inertia I*_2D = (64 / pi) * I*_3D
    y_3d_flutter_chaos = 0.012 + 0.15 * np.exp(-re_mesh / 2000.0)
    y_3d_chaos_tumble  = 0.025 + 0.20 * np.exp(-re_mesh / 2000.0)

    y_2d_flutter_chaos = geom_factor_3D_to_2D * y_3d_flutter_chaos
    y_2d_chaos_tumble  = geom_factor_3D_to_2D * y_3d_chaos_tumble

    # Shaded literature zones (converted to 2D scale)
    ax0.fill_between(re_mesh, 0.05, y_2d_flutter_chaos, color="#2ca02c", alpha=0.10, label="Field et al. (1997) Flutter Zone")
    ax0.fill_between(re_mesh, y_2d_flutter_chaos, y_2d_chaos_tumble, color="#ff7f0e", alpha=0.15, label="Field et al. (1997) Chaotic Transition")
    ax0.fill_between(re_mesh, y_2d_chaos_tumble, 5.0, color="#d62728", alpha=0.10, label="Field et al. (1997) Tumbling Zone")

    # Shaded quasi-steady extrapolation limit Re > 5000
    ax0.axvspan(5000.0, 25000.0, color="gray", alpha=0.12, label="Extrapolated (Re > 5000)")
    ax0.axvline(5000.0, color="darkred", ls="--", lw=1.2, alpha=0.8, label="Fitted Re Limit (Re = 5000)")

    # Plot 6 Czech coins from ondrej-cloud (converted to 2D equivalent I*)
    for coin in coins_data:
        i_2d = coin["I_star_3D"] * geom_factor_3D_to_2D
        ax0.scatter(coin["Re"], i_2d, color="#d62728", marker="o", s=75, edgecolor="black", zorder=5)
        ax0.annotate(coin["name"], (coin["Re"], i_2d), xytext=(5, 4), textcoords="offset points", fontsize=8, fontweight="bold", color="#800000")

    # Plot washers from ondrej-cloud (converted to 2D equivalent I*)
    for washer in washers_data:
        i_2d = washer["I_star_3D"] * geom_factor_3D_to_2D
        mkr = "s" if "hole" in washer["name"] else "D"
        col = "#2ca02c" if "hole" in washer["name"] else "#d62728"
        ax0.scatter(washer["Re"], i_2d, color=col, marker=mkr, s=70, edgecolor="black", zorder=5)
        lbl = washer["name"].replace("Washer (", "").replace(")", "").replace(" hole", "")
        ax0.annotate(lbl, (washer["Re"], i_2d), xytext=(5, -10), textcoords="offset points", fontsize=7.5, color="#1b4d3e")

    # Overlay our 2D ODE simulation points
    color_map = {"steady": "#1f77b4", "fluttering": "#2ca02c", "mixed": "#ff7f0e", "tumbling": "#d62728"}
    marker_map = {"steady": "o", "fluttering": "^", "mixed": "s", "tumbling": "D"}
    for reg in ["steady", "fluttering", "mixed", "tumbling"]:
        idx = [i for i, r in enumerate(ode_regimes) if r == reg]
        if idx:
            ax0.scatter(ode_re[idx], ode_i_stars[idx], color=color_map[reg], marker=marker_map[reg], s=60, edgecolors="blue", lw=1.2, label=f"2D ODE: {reg.capitalize()}", zorder=6)

    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlim(200, 22000)
    ax0.set_ylim(0.05, 5.0)
    ax0.set_xlabel(r"Reynolds Number $\mathrm{Re}$")
    ax0.set_ylabel(r"Dimensionless Moment of Inertia $I^* = (\rho_s h)/(\rho_f L)$")
    ax0.set_title("(a) Phase Diagram vs 3D Disk Experiments\n(ondrej-cloud & Field et al. 1997, MIT License)", fontsize=11)
    ax0.grid(True, which="both", alpha=0.3)
    ax0.legend(loc="lower left", fontsize=7.5, framealpha=0.9)

    # --- Panel (b): Dimensionless Descent Speed U / U_t vs I* ---
    ax1 = axs[1]
    ax1.plot(ode_i_stars, ode_u_ratio, "o-", color="#1f77b4", lw=1.8, markersize=5, label=r"2D Quasi-Steady ODE ($U_{\mathrm{mean}} / U_t$)")

    # Benchmark Card 1 and Card 2 from Andersen et al. (2005b)
    ax1.errorbar([1.14], [0.54], yerr=[0.05], fmt="s", color="#2ca02c", markersize=8, capsize=4, elinewidth=1.5, label="Andersen et al. (2005b) Card 1 (Flutter)")
    ax1.errorbar([1.38], [0.62], yerr=[0.06], fmt="D", color="#d62728", markersize=8, capsize=4, elinewidth=1.5, label="Andersen et al. (2005b) Card 2 (Tumble)")

    # Literature transition band I*_c ~ 1.1 - 1.3
    ax1.axvspan(1.1, 1.3, color="#ff7f0e", alpha=0.18, label=r"Literature $I^*_c$ Transition Band ($1.1 - 1.3$)")

    ax1.set_xscale("log")
    ax1.set_ylim(0.2, 1.1)
    ax1.set_xlabel(r"Dimensionless Moment of Inertia $I^*$")
    ax1.set_ylabel(r"Dimensionless Descent Speed $U / U_t$")
    ax1.set_title(r"(b) Descent Speed Ratio $U / U_t$ Benchmark" + "\n(vs Andersen et al. 2005b)", fontsize=11)
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend(loc="lower right", fontsize=8, framealpha=0.9)

    # --- Panel (c): Strouhal Number St in Fluttering Regime ---
    ax2 = axs[2]
    # Filter to fluttering cases
    flutter_mask = np.array([r == "fluttering" for r in ode_regimes])
    if np.any(flutter_mask):
        ax2.plot(ode_i_stars[flutter_mask], ode_st[flutter_mask], "s-", color="#2ca02c", lw=1.8, markersize=6, label=r"2D ODE Fluttering $St$")

    # Literature St ranges
    ax2.axhspan(0.18, 0.22, color="gray", alpha=0.20, label=r"Literature Card/Strip Range ($St \approx 0.18 - 0.22$)")
    ax2.axhline(0.20, color="black", ls="--", lw=1.2, label=r"Belmonte et al. (1998) / Andersen (2005a) $St \approx 0.20$")

    ax2.set_xscale("log")
    ax2.set_ylim(0.05, 0.40)
    ax2.set_xlabel(r"Dimensionless Moment of Inertia $I^*$")
    ax2.set_ylabel(r"Strouhal Number $\mathrm{St} = f L / U_{\mathrm{mean}}$")
    ax2.set_title(r"(c) Flutter Strouhal Number $\mathrm{St}$ Benchmark" + "\n(vs Andersen 2005a & Belmonte 1998)", fontsize=11)
    ax2.grid(True, which="both", alpha=0.3)
    ax2.legend(loc="upper right", fontsize=8, framealpha=0.9)

    plt.tight_layout()

    # Save CSV with underlying comparison data
    csv_headers = ["I_star", "Re_meas", "regime", "U_mean_div_Ut", "Strouhal_St"]
    csv_rows = [[i_s, r, reg, u_r, s_val] for i_s, r, reg, u_r, s_val in zip(ode_i_stars, ode_re, ode_regimes, ode_u_ratio, ode_st)]

    save_figure_and_csv(fig, out_path, "literature_validation", csv_headers, csv_rows)
    print(f"Literature validation figure and CSV saved to: {out_path / 'literature_validation.png'}")
    return out_path / "literature_validation.png"


def main():
    base_yaml = get_default_config_path("base.yaml")
    config = SimulationConfig.from_yaml(base_yaml)
    run_literature_validation(config)


if __name__ == "__main__":
    main()
