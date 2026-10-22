"""Run SPH-FSI numerical experiments: matched cases, explicit Re sweep, and Seb Lague frame renders."""

import subprocess
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
SPH_RUNNER = ROOT_DIR / "cpp_sph" / "bin" / ("sph_runner.exe" if sys.platform == "win32" else "sph_runner")
DROPS_DIR = ROOT_DIR / "results_sph" / "drops"
FRAMES_DIR = DROPS_DIR / "frames"
COMPARISON_DIR = ROOT_DIR / "results_sph" / "comparison"

def run_experiment_1():
    print("\n=======================================================")
    print("  EXPERIMENT 1: Matched Cases vs Step 1 ODE Drops      ")
    print("=======================================================")
    DROPS_DIR.mkdir(parents=True, exist_ok=True)
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # 4 Representative cases across dynamic regimes from Step 1 ODE
    cases = [
        {"name": "steady_I006",    "I_star": 0.06, "L": 0.024, "h": 0.0018, "mu": 0.001, "theta0": 5.0,  "t_end": 0.35, "ode_regime": "Steady"},
        {"name": "flutter_I068",   "I_star": 0.68, "L": 0.024, "h": 0.0018, "mu": 0.001, "theta0": 5.0,  "t_end": 0.40, "ode_regime": "Fluttering"},
        {"name": "tumble_I120",    "I_star": 1.20, "L": 0.024, "h": 0.0018, "mu": 0.001, "theta0": 20.0, "t_end": 0.40, "ode_regime": "Tumbling"},
        {"name": "mixed_I235",     "I_star": 2.35, "L": 0.024, "h": 0.0018, "mu": 0.001, "theta0": 15.0, "t_end": 0.40, "ode_regime": "Mixed"}
    ]

    results = []

    for c in cases:
        csv_out = DROPS_DIR / f"sph_{c['name']}.csv"
        print(f"\n[Exp 1] Running SPH drop: {c['name']} (I* = {c['I_star']}, {c['ode_regime']})...")
        cmd = [
            str(SPH_RUNNER), "--fsi-drop",
            "--Istar", str(c["I_star"]),
            "--L", str(c["L"]),
            "--h", str(c["h"]),
            "--mu", str(c["mu"]),
            "--theta0", str(c["theta0"]),
            "--t_end", str(c["t_end"]),
            "--dt", "5e-5",
            "--dx", "0.0015", # N_h = 1.2
            "--out-csv", str(csv_out)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print(f"[Error in {c['name']}]: {res.stderr}")

        # Post-process trajectory
        if csv_out.exists():
            df = pd.read_csv(csv_out)
            if len(df) > 20:
                t = df["t"].values
                vy = df["V"].values
                th = df["theta"].values
                # Discard transient (first 20%)
                idx_post = int(0.20 * len(df))
                u_mean = np.mean(np.abs(vy[idx_post:]))
                re_in = np.sqrt(max((c["I_star"] * 998.0 * c["L"] / c["h"] / 998.0) - 1.0, 0.0) * 9.81 * c["h"]) * c["L"] / (c["mu"] / 998.0)
                re_meas = (998.0 * u_mean * c["L"]) / c["mu"]
                th_std = np.std(np.degrees(th[idx_post:]))
                th_net = np.abs(th[-1] - th[0])

                # Regime classification
                if th_std < 1.0 and th_net < 0.2:
                    sph_regime = "Steady"
                elif th_net >= 2.0 * np.pi:
                    sph_regime = "Tumbling"
                elif th_net >= 1.0 * np.pi:
                    sph_regime = "Mixed"
                else:
                    sph_regime = "Fluttering"

                results.append({
                    "case": c["name"],
                    "I_star": c["I_star"],
                    "ODE_regime": c["ode_regime"],
                    "SPH_regime": sph_regime,
                    "Re_in": round(re_in, 1),
                    "Re_meas": round(re_meas, 1),
                    "U_mean_m_s": round(u_mean, 4),
                    "theta_std_deg": round(th_std, 2),
                    "N_h": round(c["h"] / 0.0015, 1)
                })

    df_res = pd.DataFrame(results)
    df_res.to_csv(COMPARISON_DIR / "matched_cases_sph_vs_ode.csv", index=False)
    print("\n[Exp 1] Matched cases summary:")
    print(df_res.to_string())
    return df_res

def run_experiment_2():
    print("\n=======================================================")
    print("  EXPERIMENT 2: Explicit Viscosity / Re_in Sweep        ")
    print("=======================================================")
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # Fixed geometry and I* = 0.65; vary physical viscosity mu
    I_star = 0.65
    L = 0.024
    h = 0.0018
    rho_f = 998.0
    g = 9.81
    rho_s = (I_star * rho_f * L) / h
    u_t = np.sqrt(((rho_s / rho_f) - 1.0) * g * h)

    re_targets = [25.0, 100.0, 300.0, 800.0]
    sweep_results = []

    for Re_in in re_targets:
        mu = (rho_f * u_t * L) / Re_in
        csv_out = DROPS_DIR / f"sph_visc_Re{int(Re_in)}.csv"
        print(f"\n[Exp 2] Running viscosity case: Re_in = {Re_in} (mu = {mu:.6f} Pa*s)...")
        cmd = [
            str(SPH_RUNNER), "--fsi-drop",
            "--Istar", str(I_star),
            "--L", str(L),
            "--h", str(h),
            "--mu", str(mu),
            "--theta0", "5.0",
            "--t_end", "0.35",
            "--dt", "5e-5",
            "--dx", "0.0015",
            "--out-csv", str(csv_out)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if csv_out.exists():
            df = pd.read_csv(csv_out)
            if len(df) > 20:
                idx_post = int(0.20 * len(df))
                u_mean = np.mean(np.abs(df["V"].values[idx_post:]))
                re_meas = (rho_f * u_mean * L) / mu
                th_std = np.std(np.degrees(df["theta"].values[idx_post:]))
                sweep_results.append({
                    "Re_in": Re_in,
                    "mu_Pa_s": round(mu, 6),
                    "Re_meas": round(re_meas, 1),
                    "U_mean_m_s": round(u_mean, 4),
                    "theta_std_deg": round(th_std, 2),
                    "regime": "Fluttering" if th_std >= 1.0 else "Steady"
                })

    df_sw = pd.DataFrame(sweep_results)
    df_sw.to_csv(COMPARISON_DIR / "viscosity_sweep_Re.csv", index=False)
    print("\n[Exp 2] Viscosity sweep summary:")
    print(df_sw.to_string())
    return df_sw

def run_experiment_3():
    print("\n=======================================================")
    print("  EXPERIMENT 3: Sebastian Lague-Style PNG Frame Renders ")
    print("=======================================================")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Render Mode B (SPH Fluttering Drop with Speed Colormap)
    print("[Exp 3] Rendering Mode B SPH Fluttering Drop (Speed Ramp)...")
    cmd_sph_speed = [
        str(SPH_RUNNER), "--fsi-drop",
        "--Istar", "0.68",
        "--theta0", "8.0",
        "--t_end", "0.20",
        "--dt", "5e-5",
        "--dx", "0.0015",
        "--render",
        "--render-mode", "speed",
        "--render-stride", "40",
        "--render-dir", str(FRAMES_DIR / "flutter_speed")
    ]
    subprocess.run(cmd_sph_speed, capture_output=True, text=True)

    # 2. Render Mode B (SPH Tumbling Drop with Vorticity Colormap)
    print("[Exp 3] Rendering Mode B SPH Tumbling Drop (Vorticity Ramp)...")
    cmd_sph_vort = [
        str(SPH_RUNNER), "--fsi-drop",
        "--Istar", "1.20",
        "--theta0", "20.0",
        "--t_end", "0.20",
        "--dt", "5e-5",
        "--dx", "0.0015",
        "--render",
        "--render-mode", "vorticity",
        "--render-stride", "40",
        "--render-dir", str(FRAMES_DIR / "tumble_vorticity")
    ]
    subprocess.run(cmd_sph_vort, capture_output=True, text=True)

    # 3. Render Mode A (ODE Replay)
    ode_csv = ROOT_DIR / "results" / "single_drop" / "trajectory.csv"
    if ode_csv.exists():
        print(f"[Exp 3] Rendering Mode A ODE Replay from {ode_csv}...")
        cmd_ode = [
            str(SPH_RUNNER), "--ode-replay",
            str(ode_csv),
            str(FRAMES_DIR / "ode_replay")
        ]
        subprocess.run(cmd_ode, capture_output=True, text=True)

    print(f"[Exp 3] Frame renders complete. Output frames in {FRAMES_DIR}")

if __name__ == "__main__":
    run_experiment_1()
    run_experiment_2()
    run_experiment_3()
