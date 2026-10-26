"""Quantitative comparison between Step 1 2D ODE and Step 2 C++ SPH-FSI simulations."""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from autumn.params import PlateParams, FluidParams, Coefficients, NumericsParams
from autumn.integrate import simulate_drop

DROPS_DIR = ROOT_DIR / "results_sph" / "drops"
COMPARISON_DIR = ROOT_DIR / "results_sph" / "comparison"


def compute_spectral_frequency(t: np.ndarray, signal: np.ndarray) -> tuple[float | None, str]:
    """Compute dominant oscillation frequency via FFT after detrending.
    Requires at least 3 full cycles in the signal window (T_window >= 3.0 / f_peak);
    otherwise returns (None, 'not resolvable').
    """
    if len(t) < 30:
        return None, "not resolvable"
    dt = float(np.mean(np.diff(t)))
    sig_detrend = signal - np.mean(signal)
    fft_vals = np.abs(np.fft.rfft(sig_detrend))
    freqs = np.fft.rfftfreq(len(signal), d=dt)
    # Mask out DC and near-zero drift frequencies (< 0.5 Hz)
    valid_idx = freqs >= 0.5
    if not np.any(valid_idx):
        return None, "not resolvable"
    valid_freqs = freqs[valid_idx]
    valid_fft = fft_vals[valid_idx]
    peak_idx = np.argmax(valid_fft)
    f_peak = float(valid_freqs[peak_idx])

    # Duration of signal window
    t_win = float(t[-1] - t[0])
    # Minimum 3 cycles required: T_win >= 3.0 * (1 / f_peak)
    if f_peak <= 0.0 or t_win < (3.0 / f_peak):
        return None, "not resolvable"
    return f_peak, f"{f_peak:.2f}"


def run_ode_matched(case: dict) -> pd.DataFrame:
    """Run Step 1 DOP853 ODE simulation for exact matched plate geometry."""
    L = case["L"]
    h = case["h"]
    rho_f = 998.0
    rho_s = (case["I_star"] * rho_f * L) / h

    plate = PlateParams(
        name=case["name"],
        L=L,
        h=h,
        rho_s=rho_s
    )
    fluid = FluidParams(rho_f=rho_f, mu=0.001, g=9.81)
    coeffs = Coefficients(
        C_T=1.2,
        C_R=np.pi,
        C_D0=1.4,
        C_D1=1.0,
        mu_1=0.20,
        mu_2=0.20,
        C_tau=np.pi * 0.20 / 8.0
    )
    numerics = NumericsParams()
    theta0_rad = np.radians(case["theta0"])

    res = simulate_drop(
        plate=plate,
        fluid=fluid,
        coeffs=coeffs,
        numerics=numerics,
        theta0=theta0_rad,
        u0=0.0,
        v0=0.0,
        omega0=0.0,
        X0=0.0,
        Y0=-0.04,
        t_max_override=case["t_end"]
    )
    df = pd.DataFrame({
        "t": res.t,
        "x": res.X,
        "y": res.Y,
        "u": res.u,
        "v": res.v,
        "theta": res.theta,
        "omega": res.omega,
        "vy": res.v_Y
    })
    return df


def compare_sph_and_ode():
    print("[Comparison] Running quantitative Step 1 ODE vs Step 2 C++ SPH-FSI comparison...")
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # Retained physical cases (1.2 <= rho_s/rho_f <= 20)
    cases = [
        {"name": "flutter_I068", "I_star": 0.68, "L": 0.024, "h": 0.0018, "theta0": 5.0,  "t_end": 1.00, "ode_regime": "Fluttering"},
        {"name": "tumble_I135",  "I_star": 1.35, "L": 0.024, "h": 0.0018, "theta0": 20.0, "t_end": 1.00, "ode_regime": "Tumbling"},
        {"name": "mixed_I145",   "I_star": 1.45, "L": 0.024, "h": 0.0018, "theta0": 15.0, "t_end": 1.00, "ode_regime": "Mixed"}
    ]

    metrics = []
    dfs_ode = {}
    dfs_sph = {}

    for c in cases:
        print(f"  Processing case: {c['name']} (I* = {c['I_star']})...")
        df_ode = run_ode_matched(c)
        dfs_ode[c["name"]] = df_ode

        sph_csv = DROPS_DIR / f"sph_{c['name']}.csv"
        if not sph_csv.exists():
            print(f"  [Notice] SPH file {sph_csv.name} not found yet. Skipping SPH load.")
            continue

        df_sph = pd.read_csv(sph_csv)
        dfs_sph[c["name"]] = df_sph

        # Developed regime: discard transient (first 25%), compare over matched window [0.25 * t_end, t_end]
        post_ode = (df_ode["t"] >= 0.25 * c["t_end"]) & (df_ode["t"] <= c["t_end"])
        post_sph = (df_sph["t"] >= 0.25 * c["t_end"]) & (df_sph["t"] <= c["t_end"])

        # Descent speeds
        u_mean_ode = float(np.mean(np.abs(df_ode.loc[post_ode, "vy"])))
        u_mean_sph = float(np.mean(np.abs(df_sph.loc[post_sph, "V"])))
        diff_u_pct = abs(u_mean_sph - u_mean_ode) / u_mean_ode * 100.0

        # Frequency & amplitude
        th_ode_deg = np.degrees(df_ode.loc[post_ode, "theta"].values)
        th_sph_deg = np.degrees(df_sph.loc[post_sph, "theta"].values)

        f_val_ode, f_str_ode = compute_spectral_frequency(df_ode.loc[post_ode, "t"].values, th_ode_deg)
        f_val_sph, f_str_sph = compute_spectral_frequency(df_sph.loc[post_sph, "t"].values, th_sph_deg)
        if f_val_ode is not None and f_val_sph is not None and f_val_ode > 0.1:
            diff_f_pct = f"{abs(f_val_sph - f_val_ode) / f_val_ode * 100.0:.2f}"
        else:
            diff_f_pct = "—"

        th_amp_ode = float(0.5 * (np.max(th_ode_deg) - np.min(th_ode_deg)))
        th_amp_sph = float(0.5 * (np.max(th_sph_deg) - np.min(th_sph_deg)))
        diff_th_pct = (abs(th_amp_sph - th_amp_ode) / th_amp_ode * 100.0) if th_amp_ode > 1.0 else 0.0

        # SPH regime classification
        th_std_sph = float(np.std(th_sph_deg))
        th_net_sph = float(abs(th_sph_deg[-1] - th_sph_deg[0]))
        if th_std_sph < 1.5 and th_net_sph < 15.0:
            sph_regime = "Steady"
        elif th_net_sph >= 360.0:
            sph_regime = "Tumbling"
        elif th_net_sph >= 180.0:
            sph_regime = "Mixed"
        else:
            sph_regime = "Fluttering"

        metrics.append({
            "case": c["name"],
            "I_star": c["I_star"],
            "ODE_regime": c["ode_regime"],
            "SPH_regime": sph_regime,
            "U_mean_ODE_m_s": round(u_mean_ode, 4),
            "U_mean_SPH_m_s": round(u_mean_sph, 4),
            "diff_U_pct": round(diff_u_pct, 2),
            "freq_ODE_Hz": f_str_ode,
            "freq_SPH_Hz": f_str_sph,
            "diff_freq_pct": diff_f_pct,
            "theta_amp_ODE_deg": round(th_amp_ode, 1),
            "theta_amp_SPH_deg": round(th_amp_sph, 1),
            "diff_theta_amp_pct": round(diff_th_pct, 2)
        })

    df_metrics = pd.DataFrame(metrics)
    csv_out = COMPARISON_DIR / "quantitative_sph_vs_ode_comparison.csv"
    df_metrics.to_csv(csv_out, index=False)
    print(f"\n[Comparison] Quantitative Metrics Table saved to {csv_out}:")
    print(df_metrics.to_string())

    # Generate 4-panel visual comparison
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.patch.set_facecolor("#FFFFFF")

    # 1. Pitch angle trajectory overlay for Fluttering (I* = 0.68)
    ax1 = axes[0, 0]
    ax1.set_facecolor("#FFFFFF")
    if "flutter_I068" in dfs_ode:
        df_o = dfs_ode["flutter_I068"]
        ax1.plot(df_o["t"], np.degrees(df_o["theta"]), "k--", lw=2.0, label="2D ODE (Quasi-Steady Potential Flow)")
    if "flutter_I068" in dfs_sph:
        df_s = dfs_sph["flutter_I068"]
        ax1.plot(df_s["t"], np.degrees(df_s["theta"]), color="#1E88E5", lw=2.2, label="2D SPH-FSI (Two-Way Coupled Navier-Stokes)")
    ax1.set_xlabel("Time $t$ [s]")
    ax1.set_ylabel("Tilt Angle $\\theta(t)$ [deg]")
    ax1.set_title("Matched Case: Fluttering Dynamics ($I^* = 0.68$, $\\mathrm{Re} \\approx 3200$)")
    ax1.legend(frameon=True, facecolor="#FFFFFF")
    ax1.grid(True, linestyle=":", alpha=0.6)

    # 2. Orientation / autorotation trajectory overlay for Tumbling (I* = 1.35)
    ax2 = axes[0, 1]
    ax2.set_facecolor("#FFFFFF")
    if "tumble_I135" in dfs_ode:
        df_o = dfs_ode["tumble_I135"]
        ax2.plot(df_o["t"], np.degrees(df_o["theta"]), "k--", lw=2.0, label="2D ODE (Quasi-Steady)")
    if "tumble_I135" in dfs_sph:
        df_s = dfs_sph["tumble_I135"]
        ax2.plot(df_s["t"], np.degrees(df_s["theta"]), color="#E53935", lw=2.2, label="2D SPH-FSI (Navier-Stokes)")
    ax2.set_xlabel("Time $t$ [s]")
    ax2.set_ylabel("Total Orientation Angle $\\theta(t)$ [deg]")
    ax2.set_title("Matched Case: Tumbling Dynamics ($I^* = 1.35$)")
    ax2.legend(frameon=True, facecolor="#FFFFFF")
    ax2.grid(True, linestyle=":", alpha=0.6)

    # 3. Explicit Viscosity / Reynolds Sweep Comparison
    ax3 = axes[1, 0]
    ax3.set_facecolor("#FFFFFF")
    visc_csv = COMPARISON_DIR / "viscosity_sweep_Re.csv"
    if visc_csv.exists():
        df_v = pd.read_csv(visc_csv)
        ax3.plot(df_v["Re_in"], df_v["U_mean_m_s"], "o-", color="#FB8C00", lw=2.2, ms=8, label="2D SPH Measured $U_{\\mathrm{mean}}$")
        ax3.set_xlabel("Input Reynolds Number $\\mathrm{Re}_{\\mathrm{in}} = \\rho_f U_t L / \\mu$")
        ax3.set_ylabel("Mean Descent Speed $U_{\\mathrm{mean}}$ [m/s]")
        ax3.set_title("Viscosity Sweep: Wake Damping at Low $\\mathrm{Re}$")
        ax3.legend(frameon=True, facecolor="#FFFFFF")
        ax3.grid(True, linestyle=":", alpha=0.6)

    # 4. Descent Speed & Frequency Quantitative Bar Chart
    ax4 = axes[1, 1]
    ax4.set_facecolor("#FFFFFF")
    if len(metrics) > 0:
        x_pos = np.arange(len(metrics))
        width = 0.35
        ax4.bar(x_pos - width/2, [m["U_mean_ODE_m_s"] for m in metrics], width, label="2D ODE Speed [m/s]", color="#90CAF9")
        ax4.bar(x_pos + width/2, [m["U_mean_SPH_m_s"] for m in metrics], width, label="2D SPH Speed [m/s]", color="#1E88E5")
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels([f"{m['case']}\n(I*={m['I_star']})" for m in metrics])
        ax4.set_ylabel("Mean Descent Speed [m/s]")
        ax4.set_title("Quantitative Descent Velocity Agreement")
        for i, m in enumerate(metrics):
            ax4.text(i, max(m["U_mean_ODE_m_s"], m["U_mean_SPH_m_s"]) + 0.015,
                     f"diff: {m['diff_U_pct']}%", ha="center", fontsize=9, fontweight="bold", color="#D32F2F")
        ax4.legend(frameon=True, facecolor="#FFFFFF")
        ax4.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    out_plot = COMPARISON_DIR / "sph_vs_ode_comparison.png"
    plt.savefig(out_plot, dpi=300, facecolor="#FFFFFF")
    plt.close()
    print(f"[Comparison] Saved 4-panel figure to {out_plot}")
    return df_metrics


if __name__ == "__main__":
    compare_sph_and_ode()
