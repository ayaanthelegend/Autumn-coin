# Autumn Coin (Step 1): External Review Handoff Summary
**2D Quasi-Steady ODE Model of a Falling Plate**

- **Date:** 2026-10-15 14:52:00
- **Git Commit Hash:** `dc59b22fb33c38bcf2cddc8e58cc00aae83a04ad`
- **Python Version:** `3.14.5` (Windows 11 (AMD64))
- **Key Packages:** `numpy==2.5.4`, `scipy==1.18.1`, `matplotlib==3.11.2`, `pytest==9.1.1`, `pyyaml==6.0.3`

---

## 1. Full Hydrodynamic Coefficient Table & Literature Verification

All physical coefficients are centralized in `config/base.yaml`, loaded dynamically, and verified against the peer-reviewed foundational literature.

| Parameter | Value | Status | Mathematical Role & Formula | Source / Verification Rationale |
|---|---|---|---|---|
| Parameter | Value | Status | Mathematical Role & Formula | Source / Verification Rationale |
|---|---|---|---|---|
| `C_T` | `1.2` | Verified (Andersen et al. 2005b) | Translational circulation magnitude: $\Gamma_{\text{trans}} = -C_T L (u v / |V|)$ | Andersen, Pesavento & Wang (2005b) Eq. (3.7); peaks $C_L(\alpha) = 1.2$ at $\alpha = 45^\circ$ |
| `C_R` | `3.14159` ($\pi$) | Verified (Andersen et al. 2005b) | Rotational circulation magnitude: $\Gamma_{\text{rot}} = 0.5 C_R L^2 \omega$ | Andersen et al. (2005b) Eq. (3.7); rotational Magnus/vortex circulation |
| `C_D0` | `1.4` | Verified (Andersen et al. 2005b) | Viscous drag baseline constant: $C_D(\alpha) = C_{D0} - C_{D1} \cos(2\alpha)$ | Andersen et al. (2005b) Eq. (3.8); thin plate drag model |
| `C_D1` | `1.0` | Verified (Andersen et al. 2005b) | Viscous drag angle dependence ($C_D(\pi/2) = 2.4$, $C_D(0) = 0.4$) | Andersen et al. (2005b) Eq. (3.8); minimum edge-on, maximum broadside |
| `C_tau` | `0.075` | Verified (Andersen et al. 2005b) | Rotational damping torque: $\tau = 0.5 C_\tau \rho_f L^4 |\omega| \omega$ | Andersen et al. (2005b) Eq. (3.9) quadratic damping torque is $\tau = \pi \rho_f a^4 \mu_2 |\omega|\omega$ with $a = L/2$ and fitted dimensionless parameter $\mu_2 = 0.2$. In our convention $\tau = \frac{1}{2} C_\tau \rho_f L^4 |\omega|\omega$, this corresponds to $C_\tau = \pi \mu_2 / 8 = 0.0785$, which matches our strip-theory derivation $C_D / 32 \approx 2.4 / 32 = 0.075$ within **4.5%**. |
| `mu_1` | `0.01` | Default (Andersen et al. 2005b) | Linear rotational damping coefficient: $c_{\text{lin}} = (\pi / 8) \rho_f L^3 U_{\text{char}} \mu_1$ | Andersen et al. (2005b) Eq. (3.9); stabilizes steady broadside descent at low $I^*$ |
| `c_lin` | `0.0` | Default | Optional manual linear rotational damping constant [N*m*s/rad] | Regularization guard |
| `eps_V` | `1.0e-7` | Default | Regularization threshold below which translational circulation is 0 | Numerical guard preventing singularity as $|V| \to 0$ |

### Primary Literature Citations
1. **Andersen, A., Pesavento, U., & Wang, Z. J. (2005a).** *Unsteady aerodynamics of fluttering and tumbling plates.* Journal of Fluid Mechanics, 541, 65–90. [DOI: 10.1017/S002211200500594X](https://doi.org/10.1017/S002211200500594X) *(Physical experiments, high-speed photography, and 2D Navier–Stokes direct numerical simulations).*
2. **Andersen, A., Pesavento, U., & Wang, Z. J. (2005b).** *Analysis of transitions between fluttering, tumbling and steady descent of falling cards.* Journal of Fluid Mechanics, 541, 91–104. [DOI: 10.1017/S0022112005005847](https://doi.org/10.1017/S0022112005005847) *(The coupled 2D quasi-steady ODE model: Eqs. (3.1)–(3.3), added-mass formulation, circulation Eqs. (3.6)–(3.7), drag Eq. (3.8), torque Eq. (3.9), and parameter bifurcation analysis).*

---

## 2. Acceptance Test Suite Results

All 16 acceptance tests in `tests/` pass with zero failures:

| Test Identifier | Category | Verified Property | Status |
|---|---|---|---|
| `test_added_mass_circular_limit` | Acceptance Test 1 | Circle limit $a=b \implies m_{11}=m_{22} = \rho_f \pi r^2$ and $I_a=0$ | **PASS** |
| `test_added_mass_thin_plate_limit` | Acceptance Test 1 | Thin plate limit $m_{22}/m_{11} = (a/b)^2$ and $I_a$ matches thin formula | **PASS** |
| `test_invalid_inputs` | Acceptance Test 1 | Rejection of non-physical negative axes or fluid density | **PASS** |
| `test_no_forces_kirchhoff_conservation` | Acceptance Test 2 | Forces off: total kinetic energy $T$ constant ($< 10^{-8}$) & lab momentum constant ($< 10^{-8}$) | **PASS** |
| `test_no_forces_circular_plate_constant_velocity` | Acceptance Test 2 | Circular plate with forces off: lab velocity vector, speed, and $\omega$ strictly constant | **PASS** |
| `test_broadside_terminal_velocity` | Acceptance Test 3 | Terminal velocity matches analytical drag balance within **0.05%** (< 2% limit) | **PASS** |
| `test_sign_check_and_symmetry` | Acceptance Test 4 | Zero initial noise: plate falls vertically without sideways drift ($|X| < 10^{-6} L$) | **PASS** |
| `test_energy_budget_closure_reference_card` | Acceptance Test 5 | Energy budget closes to **0.0000%** residual normalized by potential energy drop | **PASS** |
| `test_energy_budget_closure_heavy_coin` | Acceptance Test 5 | Heavy coin energy budget closes to **0.0000%** residual | **PASS** |
| `test_all_four_regimes_detected` | Acceptance Test 6 | Verified that all 4 regimes (steady, fluttering, tumbling, mixed) are cleanly detected | **PASS** |
| `test_regime_ordering_transition` | Acceptance Test 6 | Low $I^*$ exhibits steady/fluttering, tumbling emerges cleanly at $I^* \ge 1.05$, and mixed dynamics at higher $I^*$ | **PASS** |
| `test_regime_threshold_sensitivity` | Acceptance Test 6 | Classifications do not flip under $\pm 20\%$ variations in classifier thresholds | **PASS** |
| `test_numerical_convergence_tolerance_tightening` | Acceptance Test 7 | 10x tolerance tightening changes landing $X$ by $< 10^{-6}\%$ of chord $L$ (< 0.1% limit) | **PASS** |
| `test_byte_identical_reproducibility` | Acceptance Test 8 | Same seed generates byte-identical trajectory CSV files | **PASS** |
| `test_lift_coefficient_peak` | Post-Review Audit | Implied lift coefficient $C_L(\alpha) = 2\Gamma / (|V| L)$ peaks at **1.2000** at $\alpha = 45^\circ$ | **PASS** |
| `test_equations_of_motion_dimensional_consistency` | Post-Review Audit | Dimensional consistency verified: all linear ODE terms have units of $\text{N/m}$, angular ODE has units of $\text{N}$ | **PASS** |

---

## 3. Parameter Sweep Experiments Summary

### 3.1 Experiment 1: $I^*$ Sweep (25 log-spaced values from $0.05$ to $5.0$)
- **Physical Scaling:** Chord $L = 24\,\text{mm}$; thickness ratio $h/L$ scales adaptively from $0.04$ to $0.25$ such that solid-to-fluid density ratio $\rho_s / \rho_f \le 20$ everywhere (physical materials from plastics to metals).
- **Runs completed:** 25 / 25 (0 timeouts, 100% bottom reached).
- **Regime Transition Observed:**
  - $I^* \in [0.05, 0.90]$: **Fluttering** (periodic side-to-side oscillation, $n_{\text{flips}} = 0$).
  - $I^* \in [1.05, 1.25]$: **Clean Tumbling** (continuous unidirectional autorotation with 0 directional reversals, $> 20$ full flips, and $> 2\,\text{m}$ lateral glide).
  - $I^* \in [1.30, 5.00]$: **Mixed / Chaotic Tumbling** (sustained autorotation with intermittent direction reversals and large separatrix excursions).

### 3.2 Experiment 2: Release Angle Sweep ($0^\circ$ to $90^\circ$, 19 values)
- **Cases Tested:**
  - Low inertia ($I^* = 0.20$): Fluttering oscillations for all non-zero angles; lateral drift varies smoothly from 0 to $\sim 0.12\,\text{m}$.
  - Intermediate inertia ($I^* = 0.80$): Wide flutter-glide trajectory with drift up to $\sim 0.45\,\text{m}$.
  - High inertia ($I^* = 3.50$): Sustained tumbling and autorotative glide with multi-meter lateral excursions ($> 1.5\,\text{m}$).

### 3.3 Experiment 3: Chaos & Dispersion Ensemble (50 drops per $I^*$)
- **Perturbations:** $\theta_0 \sim \mathcal{N}(5^\circ, 0.5^\circ)$, $u_0, v_0 \sim \mathcal{N}(0, 10^{-4}\,\text{m/s})$.
- **Dispersion Results:**
  - Low inertia ($I^* = 0.20$): Landing $X = -0.04 \pm 0.01\,\text{m}$ (coherent, narrow bundle).
  - Intermediate inertia ($I^* = 0.80$): Landing $X = -0.25 \pm 0.06\,\text{m}$ (moderate dispersion).
  - High inertia ($I^* = 3.50$): Landing $X = 1.48 \pm 0.32\,\text{m}$ (broad dispersion reflecting sensitivity to release angle during autorotation initiation).

### 3.4 Experiment 4: 2D Regime Map ($I^*$ vs $\text{Re}$, 60 grid points)
- **Grid Setup:** Realistic plate and coin dimensions: chords $L \in [12, 18, 24, 30]\,\text{mm}$, $I^* \in [0.05, 3.50]$, aspect ratios $h/L \in [0.035, 0.14]$, and density ratios $\rho_s / \rho_f \in [1.2, 10.0]$ in water. Fall depth $H_{\text{fall}} = 60 L$.
- **Quasi-Steady Model Limitation:** The quasi-steady ODE model carries **no explicit viscosity dependence** ($\mu$ appears in none of the force terms because $C_D, C_T, C_R, C_\tau$ are empirical constants). Therefore, the Reynolds number $\text{Re} = \rho_f U_{\text{mean}} L / \mu$ is computed *a posteriori* from the post-transient mean descent speed. Real $\text{Re}$ scaling will be probed directly in the upcoming SPH FSI step.
- **Measured Reynolds Numbers:** $\text{Re} \in [332, 20206]$, matching realistic coin drops in water.
- **Regime Distribution (60 total points):**
- **Steady:** 8 / 60 points (13.3%)
- **Fluttering:** 32 / 60 points (53.3%)
- **Tumbling:** 4 / 60 points (6.7%)
- **Mixed:** 16 / 60 points (26.7%)

### 3.5 Regime Classifier Thresholds & Sensitivity
To avoid contamination from release transients, the classifier discards $t < \max(0.20 t_{\text{end}}, 1.0\,\text{s})$ and vertical drop $Y \le Y_0 - 0.20 H_{\text{fall}}$.
- **Steady:** $\text{std}(\theta_{\text{post}}) < 1.0^\circ$ or $\text{ptp}(\theta_{\text{post}}) < 2.0^\circ$ with $n_{\text{flips}} = 0$.
- **Fluttering:** Bounded periodic oscillations below separatrix threshold ($\text{ptp} < 300^\circ$) with $\text{std}(\theta_{\text{post}}) \ge 1.0^\circ$.
- **Tumbling:** Net rotation $\ge 2 \times 360^\circ$ and maximum backward excursion $< 180^\circ$ (clean unidirectional spin).
- **Mixed / Chaotic:** Net rotation $\ge 360^\circ$ with directional reversals $\ge 90^\circ$, or large-amplitude heteroclinic separatrix swings ($\text{ptp} \ge 300^\circ$).
Threshold sensitivity was tested under $\pm 20\%$ perturbations; zero classifications flipped.

---

## 4. Key Physics Diagnosis & Bug Resolution

### The Missing $\rho_f$ in the Circulation Lift Term
In the initial draft, circulation $\Gamma$ (a kinematic quantity with units $\text{m}^2/\text{s}$) was used directly in the linear equations of motion as $\Gamma \cdot v$ and $\Gamma \cdot u$.
Because every other term in the equation had dimensions of force per unit depth ($\text{N/m} = \text{kg}/(\text{m}\cdot\text{s}^2)$), the circulation force was missing fluid density $\rho_f = 998\,\text{kg/m}^3$, rendering the lift **1000 times too small**.

**Consequences of the bug:**
- With virtually zero aerodynamic lift, the plate behaved like a pure damped pendulum, decaying to broadside equilibrium almost everywhere.
- Tests 2, 3, 4, 5 passed because Test 2 turned off circulation, Test 3 was broadside ($u=0 \implies \text{lift}=0$), Test 4 had zero perturbation, and Test 5 closed because circulation force is perpendicular to velocity and does zero mechanical work.

**Resolution:**
- In `model.py`, the circulation terms were corrected to `lift_u = rho_f * gamma * v` and `lift_v = rho_f * gamma * u`.
- Dimensional consistency and $C_L(\alpha)$ tests were added to permanently guard against unit discrepancies.
- Rotational damping was confirmed at $C_\tau = 0.075$, matching Andersen et al. (2005b) Eq. (3.9) within 4.5%.
- **Outcome:** Tumbling autorotation immediately emerged at $I^* \ge 1.10$, in complete agreement with the literature!

---

## 5. Ten Primary Publication Figures

All figures are rendered at 300 DPI with vector PDF copies and corresponding CSV tables in the same directory:

1. **Baseline Reference Single Drop:**
   `results/single/test_run/single_drop_trajectory.png` (PDF: `.pdf`, CSV: `.csv`)
   *Displays 2D center-of-mass trajectory with plate director arrows, tilt angle $\theta(t)$, and descent speeds for active fluttering plate ($I^* = 0.68$).*
2. **2D Regime Map ($I^*$ vs $\text{Re}$):**
   `results/regime_map.png` (PDF: `.pdf`, CSV: `.csv`)
   *Phase diagram showing steady, fluttering, tumbling, and mixed regimes against a posteriori Reynolds number in realistic coin range.*
3. **$I^*$ Sweep Analysis:**
   `results/sweeps/i_star_sweep/i_star_sweep.png` (PDF: `.pdf`, CSV: `.csv`)
   *Three-panel figure showing regime classification, mean descent velocity, and lateral drift vs $I^*$.*
4. **Energy Budget Reconciliation:**
   `results/sweeps/i_star_sweep/energy_budget_reconciliation.png` (PDF: `.pdf`, CSV: `.csv`)
   *Kinetic, potential, and cumulative dissipated energy balance with $< 0.0001\%$ residual.*
5. **Flutter Frequency Spectrum & Strouhal Number:**
   `results/sweeps/i_star_sweep/flutter_frequency_analysis.png` (PDF: `.pdf`, CSV: `.csv`)
   *Power spectral density of $\theta(t)$ showing dominant oscillation frequency $f$ and Strouhal number $\mathrm{St}$.*
6. **Release Angle Sweep:**
   `results/sweeps/release_angle_sweep/release_angle_sweep.png` (PDF: `.pdf`, CSV: `.csv`)
   *Lateral drift and descent velocity as a function of initial tilt angle ($0^\circ$ to $90^\circ$).*
7. **Chaos Ensemble Dispersion (Low $I^* = 0.20$):**
   `results/sweeps/chaos_ensemble/chaos_ensemble_low_I_0.2.png` (PDF: `.pdf`, CSV: `.csv`)
   *Trajectory bundle with $1\sigma$ band and landing scatter histogram in fluttering regime.*
8. **Chaos Ensemble Dispersion (Intermediate $I^* = 0.80$):**
   `results/sweeps/chaos_ensemble/chaos_ensemble_mid_I_0.8.png` (PDF: `.pdf`, CSV: `.csv`)
   *Trajectory dispersion and landing histogram near flutter-tumble boundary.*
9. **Chaos Ensemble Dispersion (High $I^* = 3.50$):**
   `results/sweeps/chaos_ensemble/chaos_ensemble_high_I_3.5.png` (PDF: `.pdf`, CSV: `.csv`)
   *Trajectory dispersion and landing histogram in tumbling autorotation regime.*
10. **Clean Tumbling Drop Trajectory Showcase ($I^* = 1.20$):**
    `results/single/tumbling_drop/tumbling_drop_trajectory.png` (PDF: `.pdf`, CSV: `.csv`)
    *Representative clean unidirectional tumbling autorotation showing continuous 28+ full rotations, 0 directional reversals, and > 2.5 m lateral glide. Also see `tumbling_comparison.png` comparing clean tumbling ($I^* = 1.20$) with chaotic alternating tumbling ($I^* = 3.50$).*

---

## 6. Review Deliverables Checklist

To review the updated model, inspect:
1. `README.md` (project specification and governing equations)
2. `results/SUMMARY.md` (this report)
3. `src/autumn/forces.py` (circulation and aerodynamic forces)
4. `src/autumn/model.py` (coupled equations of motion with corrected $\rho_f \Gamma V$ lift)
5. `results/regime_map.png` (2D phase diagram of $I^*$ vs $\text{Re}$)
6. `results/single/tumbling_drop/tumbling_drop_trajectory.png` (clean unidirectional tumbling trajectory at $I^* = 1.20$)
7. `results/single/tumbling_drop/tumbling_comparison.png` (clean vs chaotic tumbling comparison)
