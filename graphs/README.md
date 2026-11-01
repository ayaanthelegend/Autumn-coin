# Autumn Coin: Publication Figures (`graphs/`)

All figures have been regenerated from committed repository datasets and exact simulation pipelines to publication-quality standards. Figures are rendered at their final print scale (width exactly 6.5 inches to span the full text width of a US Letter document) at 300 DPI in raster PNG and vector PDF formats.

---

## 1. Figure Inventory and Specifications

| File Base Name | Paper Figure | Source Data Files / Pipeline | Exact Parameters | Pixel Size (300 DPI) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `energy_budget` | Fig. 8 / Energy Budget | `results/sweeps/i_star_sweep/energy_budget_reconciliation.csv` | $\rho_f = 998\,\mathrm{kg/m^3}$, $\mu_1 = 0.20$, baseline ODE | $1894 \times 819$ px | **PASS** |
| `threshold_vs_inertia` | Fig. 1 / Bifurcation Threshold | `results/regime_map.csv`, `results/mu1_sensitivity.csv` | $\mu_1 \in [0.0, 0.20]$, $\theta_0 = 20^\circ + 10^{-3}\,\mathrm{rad}$, $I^* \in [0.05, 3.50]$ | $1901 \times 1688$ px | **PASS** |
| `speed_drift_sweep` | Fig. 6 / Inertia Sweep | `results/sweeps/i_star_sweep/i_star_sweep.csv` | 25-point log sweep, $I^* \in [0.05, 3.50]$, $\mu_1 = 0.20$ | $1896 \times 886$ px | **PASS** |
| `flutter_spectrum` | Fig. 7 / Flutter Spectrum | `results/sweeps/i_star_sweep/flutter_frequency_analysis.csv` | $I^* = 0.80$, Welch PSD of $\theta(t)$, $f \in [0, 6]\,\mathrm{Hz}$ | $1894 \times 849$ px | **PASS** |
| `regime_map` | Fig. 5 / Falling Regime Map | `results/regime_map.csv` | $N = 136$ runs, $L \in \{8, 12, 16, 20\}\,\mathrm{mm}$, $I^* \in [0.05, 3.50]$, $\mu_1 = 0.20$ | $1864 \times 1267$ px | **PASS** |
| `release_angle_sensitivity` | Fig. 9 / Release Angle Sweep | `results/sweeps/release_angle_sweep/release_angle_sweep.csv` | $\theta_0 \in [0^\circ, 90^\circ]$ ($5^\circ$ step), $I^* \in \{0.20, 0.80, 3.50\}$ | $1891 \times 1809$ px | **PASS** |
| `landing_histograms` | Fig. 10 / Landing Dispersion | `results/sweeps/chaos_ensemble/chaos_ensemble_*.csv` | $N = 50$ drops/case, $\sigma_\theta = 0.5^\circ$, $\sigma_v = 10^{-4}\,\mathrm{m/s}$, $I^* \in \{0.20, 0.80, 3.50\}$ | $1920 \times 1689$ px | **PASS** |
| `nine_coins` | Fig. 3 / Coin Trajectories | `config/coins.yaml`, `results/coin_regimes.csv`, live ODE | 9 physical coin designs, first 60 time units $a/U_0$, $\theta_0 = 5^\circ + 10^{-3}\,\mathrm{rad}$ | $1914 \times 2197$ px | **PASS** |
| `literature_comparison` | Fig. 4 / Literature Benchmark | `results/regime_map.csv`, `results/literature_validation.csv` | Andersen (2005b) cards, Belmonte (1998) band, Ondřejov 3D discs | $1920 \times 1831$ px | **PASS** |
| `sph_vs_ode_tilt` | Fig. 11 / SPH vs ODE Dynamics | `results_sph/drops/sph_flutter_I068.csv`, `sph_tumble_I135.csv` | $I^* = 0.68$ (flutter), $I^* = 1.35$ (tumble), first $0.50\,\mathrm{s}$ | $1894 \times 817$ px | **PASS** |
| `sph_viscosity_sweep` | Fig. 12 / Viscosity Variation | `results_sph/drops/sph_visc_Re*.csv`, `viscosity_sweep_Re.csv` | $I^* = 0.65$, $\mathrm{Re}_{\mathrm{in}} \in \{25, 100, 300, 800\}$, $t = 0.35\,\mathrm{s}$ | $1894 \times 877$ px | **PASS** |
| `sph_benchmarks` | Fig. 13 / SPH Verification Ladder| `results_sph/validation/test4_dam_break.csv`, `test5_*.csv`, `test7_*.csv` | Test 4 dam-break front, Test 5 cylinder drag ($\mathrm{Re}=20, 40$), Test 7 grid study | $1907 \times 1621$ px | **PASS** |
| `regime_map_labelled` | New Fig. 13 / Regime Map + Cases | `results/regime_map.csv` | Regime map with highlighted Heisinger trajectory cases $\mathbf{A\text{--}D}$ | $1864 \times 1269$ px | **PASS** |
| `trajectory_strips` | New Fig. 14 / Trajectory Strips | Live ODE pipeline (`simulate_drop`) | $L = 20\,\mathrm{mm}$, fall depth $28L$, $\theta_0 = 20^\circ + 10^{-3}\,\mathrm{rad}$, 46 rotated coin ellipses | $1887 \times 837$ px | **PASS** |

---

## 2. Suggested Figure Captions and Notes

### Figure 5 & 13: Regime Map Suggested Caption
> **Suggested Caption:** Falling regime phase diagram in the $(\mathrm{Re}_{\mathrm{meas}}, I^*)$ plane across 136 simulation drops ($L \in \{8, 12, 16, 20\}\,\mathrm{mm}$, $I^* \in [0.05, 3.50]$, $\mu_1 = 0.20$, $\theta_0 = 20^\circ + 10^{-3}\,\mathrm{rad}$). The quasi-steady Kirchhoff ODE model has no explicit fluid viscosity, so the Reynolds number $\mathrm{Re}_{\mathrm{meas}} = \rho_f U_{\mathrm{mean}} L / \mu$ is an output quantity evaluated a posteriori from post-transient descent velocity; points at identical $I^*$ differ in Reynolds number only through the physical plate chord length $L$ (four chord lengths evaluated per $I^*$). The shaded region ($\mathrm{Re} > 5000$) denotes operating conditions extrapolated beyond the experimental calibration window of the quasi-steady force coefficients.

### Figure 14: Heisinger Trajectory Strips Description
> **Suggested Caption:** Heisinger-style trajectory strips for four representative falling coin cases at $L = 20\,\mathrm{mm}$, initial release angle $\theta_0 = 20^\circ + 10^{-3}\,\mathrm{rad}$, and total fall depth $28L$:
> - **Case A** ($I^* = 0.228$): Periodic fluttering with narrow lateral oscillation ($\Delta x \approx 1.15 L$).
> - **Case B** ($I^* = 0.676$): Fluttering with moderate lateral oscillation ($\Delta x \approx 2.37 L$, $\rho_s = 9000\,\mathrm{kg/m^3}$, $h = 1.5\,\mathrm{mm}$).
> - **Case C** ($I^* = 1.350$): Unidirectional autorotative tumbling with steady diagonal glide slope ($\Delta x \approx 51.86 L$).
> - **Case D** ($I^* = 2.000$): Mixed chaotic autorotation with reversals ($\Delta x \approx 6.26 L$).
> Each strip depicts the centroid path (thin grey line) overlaid with 46 equally spaced temporal snapshots of the coin cross-section rendered as an ellipse of major chord $L$ and thickness $\max(h/L, 0.13)$, oriented at instantaneous tilt $\theta(t)$. Subplot widths are strictly proportional to the horizontal extent of each trajectory, and vertical depth $|y|/L \in [0, 30]$ is displayed at 1:1 equal physical aspect ratio across all panels.

---

## 3. Could Not Regenerate

**None.** All 14 figures regenerated successfully from committed data and simulation models without omissions or errors.

---

## 4. How to Regenerate

To re-run all 14 figures in a single automated step:

```bash
python scripts/make_paper_graphs.py
```

The script reads plotting configuration from `scripts/plot_style.py` and saves both 300 DPI PNG and vector PDF copies to `graphs/`.
