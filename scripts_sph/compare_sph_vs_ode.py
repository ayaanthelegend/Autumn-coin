"""Compare Step 1 ODE and Step 2 C++ SPH-FSI simulations."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DROPS_DIR = ROOT_DIR / "results_sph" / "drops"
COMPARISON_DIR = ROOT_DIR / "results_sph" / "comparison"
ODE_RESULTS = ROOT_DIR / "results"

def compare_sph_and_ode():
    print("[Comparison] Comparing Step 1 ODE vs Step 2 C++ SPH...")
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.patch.set_facecolor("#FFFFFF")

    # 1. Trajectory comparison for Fluttering (I* = 0.68)
    ax = axes[0, 0]
    ax.set_facecolor("#FFFFFF")
    sph_flutter_csv = DROPS_DIR / "sph_flutter_I068.csv"
    ode_flutter_csv = ODE_RESULTS / "single_drop" / "trajectory.csv"

    if ode_flutter_csv.exists():
        df_ode = pd.read_csv(ode_flutter_csv)
        ax.plot(df_ode["t"], np.degrees(df_ode["theta"]), "k--", lw=2, label="2D ODE (Quasi-Steady Added-Mass)")
    if sph_flutter_csv.exists():
        df_sph = pd.read_csv(sph_flutter_csv)
        ax.plot(df_sph["t"], np.degrees(df_sph["theta"]), color="#1E88E5", lw=2.2, label="2D SPH-FSI (Two-Way Coupled Navier-Stokes)")

    ax.set_xlabel("Time $t$ [s]")
    ax.set_ylabel("Tilt Angle $\\theta(t)$ [deg]")
    ax.set_title("Matched Case: Fluttering Dynamics ($I^* = 0.68$, $\\mathrm{Re}_{\\mathrm{in}} \\approx 850$)")
    ax.legend(frameon=True, facecolor="#FFFFFF")
    ax.grid(True, linestyle=":", alpha=0.6)

    # 2. Trajectory comparison for Tumbling (I* = 1.20)
    ax = axes[0, 1]
    ax.set_facecolor("#FFFFFF")
    sph_tumble_csv = DROPS_DIR / "sph_tumble_I120.csv"
    ode_tumble_csv = ODE_RESULTS / "tumbling_drop" / "trajectory.csv"

    if ode_tumble_csv.exists():
        df_ode = pd.read_csv(ode_tumble_csv)
        ax.plot(df_ode["t"], np.degrees(df_ode["theta"]), "k--", lw=2, label="2D ODE (Quasi-Steady Added-Mass)")
    if sph_tumble_csv.exists():
        df_sph = pd.read_csv(sph_tumble_csv)
        ax.plot(df_sph["t"], np.degrees(df_sph["theta"]), color="#E53935", lw=2.2, label="2D SPH-FSI (Two-Way Coupled Navier-Stokes)")

    ax.set_xlabel("Time $t$ [s]")
    ax.set_ylabel("Total Orientation Angle $\\theta(t)$ [deg]")
    ax.set_title("Matched Case: Tumbling Dynamics ($I^* = 1.20$)")
    ax.legend(frameon=True, facecolor="#FFFFFF")
    ax.grid(True, linestyle=":", alpha=0.6)

    # 3. Explicit Viscosity / Reynolds Sweep Comparison
    ax = axes[1, 0]
    ax.set_facecolor("#FFFFFF")
    visc_csv = COMPARISON_DIR / "viscosity_sweep_Re.csv"
    if visc_csv.exists():
        df_v = pd.read_csv(visc_csv)
        ax.plot(df_v["Re_in"], df_v["U_mean_m_s"], "o-", color="#FB8C00", lw=2.2, ms=8, label="2D SPH Measured $U_{\\mathrm{mean}}$")
        ax.set_xlabel("Input Reynolds Number $\\mathrm{Re}_{\\mathrm{in}} = \\rho_f U_t L / \\mu$")
        ax.set_ylabel("Mean Descent Speed $U_{\\mathrm{mean}}$ [m/s]")
        ax.set_title("Experiment 2: Explicit $\\mathrm{Re}$ Sweep via Physical Viscosity $\\mu$")
        ax.legend(frameon=True, facecolor="#FFFFFF")
        ax.grid(True, linestyle=":", alpha=0.6)

    # 4. Regime Summary Bar Comparison
    ax = axes[1, 1]
    ax.set_facecolor("#FFFFFF")
    matched_csv = COMPARISON_DIR / "matched_cases_sph_vs_ode.csv"
    if matched_csv.exists():
        df_m = pd.read_csv(matched_csv)
        cases = df_m["case"].str.replace("sph_", "")
        y_pos = np.arange(len(cases))
        ax.barh(y_pos - 0.2, df_m["U_mean_m_s"], height=0.35, color="#1E88E5", label="2D SPH-FSI Descent Speed")
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"{c}\n({ode})" for c, ode in zip(cases, df_m["ODE_regime"])])
        ax.set_xlabel("Descent Speed $U_{\\mathrm{mean}}$ [m/s]")
        ax.set_title("Descent Speed & Regime Alignment across $I^*$ Cases")
        ax.legend(frameon=True, facecolor="#FFFFFF")
        ax.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    out_plot = COMPARISON_DIR / "sph_vs_ode_comparison.png"
    plt.savefig(out_plot, dpi=300, facecolor="#FFFFFF")
    plt.close()
    print(f"[Comparison] Saved comparison figure to {out_plot}")

if __name__ == "__main__":
    compare_sph_and_ode()
