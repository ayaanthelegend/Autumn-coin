# Autumn Coin: Comprehensive Model, Numerics & Literature Validation Summary
**2D Quasi-Steady ODE Model & SPH Navier-Stokes Solver of a Falling Plate**

- **Date:** 2026-10-24
- **Branch:** `master`
- **Python Version:** `3.14.5` (Windows 11 AMD64)
- **Key Packages:** `numpy==2.5.4`, `scipy==1.18.1`, `matplotlib==3.11.2`, `pytest==9.1.1`, `pyyaml==6.0.3`
- **Primary Bibliography:** See [`references.md`](../references.md)

---

## 1. Hydrodynamic Parameters & Literature Verification

All physical coefficients are centralized in `config/base.yaml`, loaded dynamically, and documented against peer-reviewed literature.

| Parameter | Baseline Value | Literature Status | Mathematical Formulation & Role | Primary Literature Source |
|---|---|---|---|---|
| `C_T` | `1.2` | Primary Literature | Translational circulation: $\Gamma_{\text{trans}} = -C_T L (u v / \|V\|)$ | Andersen, Pesavento & Wang (2005b) Eq. (3.7); peak $C_L = 1.2$ at $\alpha = 45^\circ$ |
| `C_R` | `3.14159` ($\pi$) | Primary Literature | Rotational circulation: $\Gamma_{\text{rot}} = 0.5 C_R L^2 \omega$ | Andersen et al. (2005b) Eq. (3.7); rotational vortex shedding |
| `C_D0` | `1.4` | Primary Literature | Drag baseline: $C_D(\alpha) = C_{D0} - C_{D1} \cos(2\alpha)$ | Andersen et al. (2005b) Eq. (3.8); thin plate drag model |
| `C_D1` | `1.0` | Primary Literature | Drag angle variation ($C_D(0^\circ) = 0.4$, $C_D(90^\circ) = 2.4$) | Andersen et al. (2005b) Eq. (3.8); edge-on min, broadside max |
| `C_tau` | `0.075` | Derived / Literature | Quadratic rotational damping: $\tau_{\text{quad}} = 0.5 C_\tau \rho_f L^4 \|\omega\| \omega$ | Andersen et al. (2005b) Eq. (3.9) $\pi \mu_2 / 8 = 0.0785$ for $\mu_2 = 0.2$ (~4.5% diff) |
| `mu_1` | `0.20` | Primary Literature Baseline | Linear rotational damping: $c_{\text{lin}} = (\pi / 8) \rho_f L^3 U_0 \mu_1$ | Andersen et al. (2005b) Eq. (3.9). Note: $\mu_1 = 0.01$ was an empirically tuned alternative |
| `c_lin` | `0.0` | Config Default | Explicit optional linear damping [N*m*s/rad] | Numerical regularizer |
| `eps_V` | `1.0e-7` | Numerical Guard | Regularization threshold for velocity division | Numerical safeguard as $\|V\| \to 0$ |
| `tank_depth_m` | `0.38` | Experimental Config | Physical water tank depth [m] | Reconciles simulation with 38 cm laboratory tank drops |

### Clarification of Characteristic Velocity Scales
To eliminate notation ambiguity across the codebase and presentations:
1. **Froude Velocity Scale ($U_t$)**: Based on full plate thickness $h$:
   $$U_t = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g h}$$
2. **Andersen Characteristic Velocity ($U_0$)**: Based on semi-minor axis $b = h/2$ (Andersen et al. 2005b Eq. 2.3):
   $$U_0 = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g b} = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g \frac{h}{2}} = \frac{U_t}{\sqrt{2}}$$
Both definitions are implemented and tested in `src/autumn/dimensionless.py` (`compute_froude_velocity_scale` and `compute_andersen_velocity_scale`).

---

## 2. Critical Bifurcation $I^*_c$: Bisection Study & Literature Comparison

A high-precision bisection search was executed via `scripts/make_bisection_study.py` (tolerance $\Delta I^* < 0.005$) on a standard card cross-section ($L = 24\,\text{mm}$, $h = 1.8\,\text{mm}$, released at $\theta_0 = 20^\circ$) to locate the exact flutter-to-tumble transition threshold $I^*_c$:

| Model Configuration / Study | Damping $\mu_1$ | Critical $I^*_c$ | Bracket $[I^*_{\text{min}}, I^*_{\text{max}}]$ | Reference Literature | Discrepancy vs Lit. Midpoint |
|---|:---:|:---:|:---:|---|:---:|
| **Primary Literature Baseline** | **0.20** | **1.2063** | $[1.2047, 1.2080]$ | **Andersen et al. (2005b) Table 1** | **+0.5%** (midpoint 1.20, band $[1.10, 1.30]$) |
| Intermediate Damping | 0.10 | 1.0963 | $[1.0947, 1.0980]$ | Sensitivity Study | -8.6% |
| Moderate Damping | 0.05 | 1.0264 | $[1.0248, 1.0280]$ | Sensitivity Study | -14.5% |
| Tuned Alternative | 0.01 | 0.9573 | $[0.9547, 0.9600]$ | Former Commit Default | -20.2% |
| Zero Linear Damping ($\mu_1 = 0$) | 0.00 | 0.9363 | $[0.9347, 0.9380]$ | Pure Quadratic Damping | -22.0% |

**Key Finding:** Using the literature baseline $\mu_1 = 0.20$ directly from Andersen et al. (2005b) reproduces the experimental falling card transition midpoint ($I^* = 1.20$) within **+0.5%** without empirical tuning.

---

## 3. Acceptance Test Suite Results

All 16 unit and acceptance tests in `tests/` pass with zero failures (`python -m pytest`):

| Test Identifier | Category | Verified Property | Status |
|---|---|---|:---:|
| `test_added_mass_circular_limit` | Acceptance Test 1 | Circular limit $a=b \implies m_{11}=m_{22} = \rho_f \pi r^2$ and $I_a=0$ | **PASS** |
| `test_added_mass_thin_plate_limit` | Acceptance Test 1 | Thin plate limit $m_{22}/m_{11} = (a/b)^2$ and analytical $I_a$ formula | **PASS** |
| `test_invalid_inputs` | Acceptance Test 1 | Strict rejection of non-physical negative axes or fluid density | **PASS** |
| `test_no_forces_kirchhoff_conservation` | Acceptance Test 2 | Conservative motion: total kinetic energy $T$ and lab momentum constant ($< 10^{-8}$) | **PASS** |
| `test_no_forces_circular_plate_constant_velocity` | Acceptance Test 2 | Circular plate unforced: lab velocity vector, speed, and $\omega$ strictly invariant | **PASS** |
| `test_broadside_terminal_velocity` | Acceptance Test 3 | Terminal velocity matches analytical drag balance within **0.05%** (< 2% limit) | **PASS** |
| `test_sign_check_and_symmetry` | Acceptance Test 4 | Zero noise release: plate falls vertically without sideways drift ($|X| < 10^{-6} L$) | **PASS** |
| `test_energy_budget_closure_reference_card` | Acceptance Test 5 | Energy budget closes to **0.0000%** normalized by total potential energy drop | **PASS** |
| `test_energy_budget_closure_heavy_coin` | Acceptance Test 5 | Heavy coin energy budget closes to **0.0000%** residual | **PASS** |
| `test_all_four_regimes_detected` | Acceptance Test 6 | All 4 regimes (steady, fluttering, tumbling, mixed) cleanly detected | **PASS** |
| `test_regime_ordering_transition` | Acceptance Test 6 | Steady/fluttering at low $I^*$, clean tumbling at intermediate $I^*$, mixed at high $I^*$ | **PASS** |
| `test_regime_threshold_sensitivity` | Acceptance Test 6 | Classifications robust to $\pm 20\%$ variations in classifier thresholds across all 4 regimes | **PASS** |
| `test_numerical_convergence_tolerance_tightening` | Acceptance Test 7 | 10x tolerance tightening shifts landing $X$ by $< 10^{-6}\%$ of chord $L$ (< 0.1% limit) | **PASS** |
| `test_byte_identical_reproducibility` | Acceptance Test 8 | Fixed seed generates byte-identical trajectory CSV files | **PASS** |
| `test_lift_coefficient_peak` | Aerodynamics Audit | Implied lift coefficient $C_L(\alpha) = 2\Gamma / (\|V\| L)$ peaks at **1.2000** at $\alpha = 45^\circ$ | **PASS** |
| `test_equations_of_motion_dimensional_consistency` | Physics Audit | Dimensional consistency: linear ODE terms in $\text{N/m}$, angular ODE terms in $\text{N}$ | **PASS** |

---

## 4. Parameter Sweep & 2D Phase Map Summary

### 4.1 2D Phase Map in $(I^*, \text{Re})$ Space (60 Grid Points)
- **Physics Clarification**: The 2D quasi-steady ODE depends solely on $I^*$ and dimensionless coefficients ($C_T, C_R, C_D, C_\tau, \mu_1$); Reynolds number $\text{Re}$ is evaluated *a posteriori* from descent speed. Viscosity-dependent transitions are evaluated separately via the Navier-Stokes SPH solver.
- **Grid Setup**: Chords $L \in [8, 12, 16, 20]\,\text{mm}$, thickness ratios $h/L \in [0.035, 0.14]$, and density ratios $\rho_s / \rho_f \in [1.2, 20.0]$.
- **Measured Reynolds Numbers**: $\text{Re}_{\text{meas}} \in [180.9, 13541.2]$.
- **Regime Distribution (Baseline $\mu_1 = 0.20$):**
  - **Steady Descent**: 8 / 60 points (13.3%) — broadside drops at low initial angles / low $I^*$.
  - **Periodic Fluttering**: 40 / 60 points (66.7%) — stable periodic oscillations.
  - **Autorotation Tumbling**: 4 / 60 points (6.7%) — sustained unidirectional spin with high lateral glide.
  - **Mixed / Chaotic Tumbling**: 8 / 60 points (13.3%) — large-amplitude separatrix swings with reversals.

---

## 5. Navier-Stokes SPH Fluid-Structure Interaction Highlights

1. **Resolution of Numerical Start-up Shock**:
   - Initial shock previously produced artificial $190\,\text{m/s}^2$ acceleration at $t = 1\,\text{ms}$.
   - **Root Cause**: In `cpp_sph/src/main_cli.cpp`, fluid particles were generated before rigid boundaries were established, placing fluid particles inside the solid ellipse.
   - **Fix**: Plate boundary is instantiated first to cleanly carve out fluid geometry, followed by 60 fixed equilibration steps. Initial speed at $t = 1\,\text{ms}$ dropped to $0.0055\,\text{m/s}$ (smooth gravitational acceleration).
2. **Physical Plate Density Ratios**:
   - Replaced buoyant case ($I^* = 0.06$, $\rho_s = 798\,\text{kg/m}^3 < \rho_f$, which floated upward) with sinking plate ($I^* = 0.15$, $\rho_s = 2395\,\text{kg/m}^3$, $\rho_s/\rho_f = 2.40$, $\text{Re}_{\text{in}} = 3438 > 0$).
   - All SPH cases strictly bounded within $1.2 \le \rho_s/\rho_f \le 20.0$.
3. **Spatial Resolution Convergence (Test 7)**:
   - Genuine resolution convergence test over grid refinements ($L/\Delta x = 12 \to 16 \to 20$) evaluating hydrodynamic force convergence ($\Delta_{23} = 25.4\% < 30\%$).
   - All 7 SPH validation tests pass cleanly (`sph_runner.exe --all-tests`).

---

## 6. Primary References
All citations are documented in [`references.md`](../references.md):
- **Andersen, A., Pesavento, U., & Wang, Z. J. (2005a).** J. Fluid Mech., 541, 65–90.
- **Andersen, A., Pesavento, U., & Wang, Z. J. (2005b).** J. Fluid Mech., 541, 91–104.
- **Field, S., Klaus, M., Moore, M. G., & O'Reilly, F. (1997).** Phys. Rev. Lett., 78(10), 1896–1899.
- **Pesavento, U., & Wang, Z. J. (2004).** Phys. Rev. Lett., 93(14), 144501.
- **Akinci, G., et al. (2012).** ACM Trans. Graph. (TOG), 31(4), 62.
- **Novotný, O., Přibyl, V., & Ambros, M. (2026).** ondrej-cloud/autumn-coin (MIT License).
