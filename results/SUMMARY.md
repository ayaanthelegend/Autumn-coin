# Autumn Coin: Comprehensive Model, Numerics & Literature Validation Summary
**2D Quasi-Steady ODE Model & SPH Navier-Stokes Solver of a Falling Plate**

- **Date:** 2026-10-25
- **Branch:** `master`
- **Tested Operating System:** Windows 11 AMD64 (build environment: Python 3.14.5, MSVC 2026 / C++17, Ninja 1.13, Node v22+)
- **Key Packages:** `numpy==2.5.4`, `scipy==1.18.1`, `matplotlib==3.11.2`, `pytest==9.1.1`, `pyyaml==6.0.3`
- **Test Status:** **23/23 Python unit and acceptance tests pass**, **10/10 C++ unit test cases (641 assertions) pass**, **Node JS core tests pass with 100% parity**

---

## 1. Hydrodynamic Parameters & Literature Baseline

All physical coefficients are centralized in `config/base.yaml`, loaded dynamically via `NumericsParams.from_config()`, and cited against peer-reviewed literature.

| Parameter | Baseline Value | Literature Status | Mathematical Formulation & Role | Primary Literature Source |
|---|---|---|---|---|
| `C_T` | `1.2` | Primary Literature | Translational circulation: $\Gamma_{\text{trans}} = -C_T L (u v / \|V\|)$ | Andersen, Pesavento & Wang (2005b) as used in ondrej-cloud implementation |
| `C_R` | `3.14159` ($\pi$) | Primary Literature | Rotational circulation: $\Gamma_{\text{rot}} = 0.5 C_R L^2 \omega$ | Andersen et al. (2005b) as used in ondrej-cloud implementation |
| `C_D0` | `1.4` | Primary Literature | Drag baseline: $C_D(\alpha) = C_{D0} - C_{D1} \cos(2\alpha)$ | Andersen et al. (2005b) thin plate drag model |
| `C_D1` | `1.0` | Primary Literature | Drag angle variation ($C_D(0^\circ) = 0.4$, $C_D(90^\circ) = 2.4$) | Andersen et al. (2005b) edge-on min, broadside max |
| `mu_1` | `0.20` | **Literature Baseline** | Linear rotational damping: $c_{\text{lin}} = (\pi / 8) \rho_f L^3 U_0 \mu_1$ | Andersen et al. (2005b); $\mu_1 = 0.01$ was an empirically tuned value |
| `mu_2` | `0.20` | Primary Literature | Quadratic damping parameter | Andersen et al. (2005b) |
| `C_tau` | `0.07854` ($\pi \mu_2 / 8$) | Derived Baseline | Quadratic rotational damping: $\tau_{\text{quad}} = 0.5 C_\tau \rho_f L^4 \|\omega\| \omega$ | Derived directly from $\pi \mu_2 / 8$ with $\mu_2 = 0.20$ |
| `eps_V` | `1.0e-7` | Numerical Guard | Regularization threshold for velocity division | Numerical safeguard as $\|V\| \to 0$ |
| `min_horizon_time_units` | `80.0` | Numerics Policy | Minimum dimensionless integration horizon $N \tau_0$ | Prevents truncation artifacts |
| `transient_time_units` | `20.0` | Classifier Policy | Minimum dimensionless transient discard $20 \tau_0$ | Discards initial transient before regime analysis |
| `min_window_time_units` | `30.0` | Classifier Policy | Minimum post-transient window $M \tau_0$ | Returns `"undetermined"` if duration insufficient |
| `stationarity_tolerance` | `0.15` (15%) | Classifier Policy | Stationarity check across post-transient window thirds | Returns `"undetermined"` if amplitude drifts $> 15\%$ |
| `min_cycles` | `2.0` | Classifier Policy | Minimum oscillation cycles $N_\text{cycles} \ge 2.0$ | Ensures attractor periodicity is established |

---

## 2. Universal Perturbation Policy & Instability of Symmetric Starts

### 2.1 Policy & Implementation
- **Library Default:** `NumericsParams.perturbation_rad = 0.0` in library defaults, configuration files, and exact reference benchmarks (`tests/test_reference_repro.py`, C++ parity tests, and `scripts/export_cpp_references.py`).
- **Labelling Scripts:** Systematic parameter sweeps (`scripts/run_coin_regimes.py`, `scripts/make_regime_map.py`, `scripts/make_bisection_study.py`, `scripts/run_mu1_sensitivity.py`) explicitly pass a physical release perturbation $\delta\theta = 10^{-3}\text{ rad}$ ($0.057^\circ$) via the centralized helper `get_labelling_numerics(base_numerics, perturbation_rad=1e-3)`.
- **Perturbation Invariance:** In `src/autumn/integrate.py` and `autumn-coin-cpp/src/sweep.cpp`, `perturbation_rad` is applied to $\theta_0$ at **any angle**:
  $$\theta(0) = \theta_0 + \delta\theta$$
- **Symmetry-Breaking Warning:** When $(|\sin\theta_0| < 10^{-9} \lor |\cos\theta_0| < 10^{-9})$ with $\delta\theta = 0.0$ and zero initial velocity, a warning is emitted noting that the trajectory direction is determined purely by floating-point roundoff, and `symmetric_start = True` is recorded.

### 2.2 Findings on Steady Descent
- **Broadside ($\theta_0 = 0^\circ, 180^\circ$) & Edge-On ($\theta_0 = 90^\circ, 270^\circ$):** In the 2D Kirchhoff potential flow + quasi-steady drag equations, both broadside and edge-on descent are exact unstable saddle points.
- **Experimental Reality:** Under physical perturbation ($\delta\theta = 10^{-3}\text{ rad}$), **zero steady descent states survive across the entire tested catalog and parameter space** ($I^* \in [0.02, 3.50]$):
  - Edge-on releases ($\theta_0 = 90^\circ$) at low $I^*$ rapidly destabilize and transition into periodic fluttering with angular excursions exceeding $30^\circ$ to $170^\circ$.
  - High $I^*$ edge-on releases transition to tumbling or chaotic mixed modes.
  - In `results/coin_regimes.csv` (72 simulated runs across 9 coins and 4 release angles), 0 steady labels exist.

---

## 3. Dimensionless Classifier Horizon & Stationarity Validation

### 3.1 Timescale & Post-Transient Formulation
The characteristic dynamical timescale of a falling plate is governed by the half-chord $a = L/2$ and the terminal descent scale $U_0 = \sqrt{(\rho_s/\rho_f - 1) g h / 2}$:
$$\tau_0 = \frac{a}{U_0}$$
- **Transient Discard:** $t_\text{transient} = \max(20.0 \tau_0, 0.20 \times t_\text{end})$.
- **Dual Stopping Event:** Integration terminates only when both $Y(t) \le -H_\text{fall}$ and $t \ge 80.0 \tau_0$.
- **Window Length:** The post-transient window must satisfy $W_\tau = (t_\text{post, end} - t_\text{post, start}) / \tau_0 \ge 30.0$.
- **Stationarity Criterion:** Dividing the post-transient window into equal thirds ($T_1, T_2, T_3$), the relative amplitude deviation between the final third $T_3$ and middle third $T_2$ must satisfy:
  $$\frac{|\text{amp}_{T_3} - \text{amp}_{T_2}|}{\max(\text{amp}_{T_2}, 10^{-6})} \le 0.15$$
  and the trajectory must complete at least $N_\text{cycles} \ge 2.0$. If either check fails, the classifier honestly assigns `"undetermined"`.

### 3.2 Horizon-Doubling Convergence Study ($N=80$ vs $160$)
Validated in `tests/test_regimes.py::test_horizon_doubling_extended_points` across boundary points, intermediate points, tungsten, and high-$I^*$ cases at both $\delta\theta = 10^{-3}$ and $\delta\theta = 10^{-2}$:
- $I^* = 1.20 \implies$ **fluttering** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 1.25 \implies$ **tumbling** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 1.30 \implies$ **tumbling** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 1.50 \implies$ **mixed** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 2.00 \implies$ **mixed** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 2.41$ (Tungsten) $\implies$ **mixed** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 3.00 \implies$ **fluttering** ($N=80$ and $N=160$, 100% agreement)
- $I^* = 3.50 \implies$ **fluttering** ($N=80$ and $N=160$, 100% agreement)

**High $I^*$ Attractor:** For $I^* \ge 3.0$ with physical plate thickness, plates settle into a stable periodic limit-cycle flutter (over 15 completed oscillation cycles, stationarity variation $< 0.3\%$).

---

## 4. Refined Regime Map & Physical Thickness Rule (`results/regime_map.csv`)

### 4.1 Physical Thickness Rule $h/L(I^*)$
In natural and engineering materials, the solid density is constrained by physical elements ($\rho_s/\rho_f \le 20.0$, bounded by tungsten $\approx 19.3$). Because $I^* \approx \frac{1}{\pi} (\rho_s/\rho_f) (h/L)$, holding aspect ratio $h/L$ constant while scaling $I^*$ to 3.5 would require unphysical densities ($\rho_s/\rho_f > 40$). To preserve physical realism:
$$\frac{h}{L} = \max\left(\frac{I^*}{20.0}, \min\left(\frac{I^*}{1.2}, \text{aspect}\right)\right)$$
This guarantees:
1. $\rho_s / \rho_f \le 20.0$ for all high $I^*$.
2. $\rho_s / \rho_f \ge 1.20$ for all low $I^*$ (avoiding buoyant or neutrally buoyant plates).

### 4.2 Grid Structure & Distribution
- **Grid Density:** 34 $I^*$ grid points (combining low-$I^*$ logarithmic geomspace, $0.05$ fine steps in $[1.00, 1.80]$, and $0.25$ steps up to $3.50$) evaluated across 4 chord lengths ($L = 8, 12, 16, 24\text{ mm}$), yielding 136 total simulation points.
- **Regime Distribution:**
  - **Fluttering:** 72 points ($I^* \le 1.20$ and $I^* \ge 3.00$)
  - **Tumbling:** 20 points ($I^* \in [1.25, 1.45]$)
  - **Mixed:** 44 points ($I^* \in [1.50, 2.75]$)
  - **Steady:** 0 points (0.0%)
- **Scale Invariance:** Validated across all 4 chord lengths ($L = 8, 12, 16, 24\text{ mm}$); all 34 grid points yield identical regime labels regardless of absolute chord scale.

---

## 5. $\mu_1$ Sensitivity & Critical Onset Bisection (`results/mu1_sensitivity.csv` & `bisection_istar_c.csv`)

Bisection study along the physical path rules:

| Damping $\mu_1$ | Release $\theta_0$ | Critical $I^*_c$ | Bracket $[I^*_{\text{lower}}, I^*_{\text{upper}}]$ | Coarse Bracket | Discrepancy vs Lit. Midpoint ($1.20$) | Transition |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.00 | $5^\circ, 20^\circ, 45^\circ$ | **0.9578** | $[0.9562, 0.9594]$ | $[0.95, 1.00]$ | -20.2% | Flutter $\to$ Tumble |
| 0.01 | $5^\circ, 20^\circ, 45^\circ$ | **0.9703** | $[0.9688, 0.9719]$ | $[0.95, 1.00]$ | -19.1% | Flutter $\to$ Tumble |
| 0.05 | $5^\circ, 20^\circ, 45^\circ$ | **1.0266** | $[1.0250, 1.0281]$ | $[1.00, 1.05]$ | -14.4% | Flutter $\to$ Tumble |
| 0.10 | $5^\circ, 20^\circ, 45^\circ$ | **1.0922** | $[1.0906, 1.0938]$ | $[1.05, 1.10]$ | -9.0% | Flutter $\to$ Tumble |
| **0.20** | $5^\circ, 20^\circ, 45^\circ$ | **1.2172** | $[1.2156, 1.2188]$ | $[1.20, 1.25]$ | **+1.4%** | **Flutter $\to$ Tumble** |

At $\mu_1 = 0.20$ with variable aspect ratios ($h/L = 0.05, 0.075, 0.10$), the critical threshold sits at $I^*_c = 1.213$ (bracket $[1.2113, 1.2146]$), within **$1.1\%$** of Andersen et al. (2005b) experimental midpoint $1.20$.

---

## 6. Catalog Coins Summary (`results/coin_regimes.csv`)

Evaluated at $\delta\theta = 10^{-3}\text{ rad}$ ($0.057^\circ$), $H_\text{fall} = 80 L$, $\theta_0 = 5^\circ$:

| Coin / Disc ID | Geometry ($D \times h$) | $\rho_s$ [$\text{kg/m}^3$] | $\rho_s / \rho_f$ | $I^*$ | Regime ($\mu_1 = 0.20$) | Turns / PTP | Regime at $\mu_1 = 0.01$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `pk_rs10` | $25.5 \times 1.5\,\text{mm}$ | 7179.6 | 7.19 | 0.4232 | **Fluttering** | 0.04 turns / $75.9^\circ$ | Fluttering |
| `pk_rs5_2002` | $24.0 \times 2.1\,\text{mm}$ | 6842.0 | 6.86 | 0.5999 | **Fluttering** | 0.03 turns / $97.6^\circ$ | Fluttering |
| `design_acrylic_24x1.2` | $24.0 \times 1.2\,\text{mm}$ | 1180.0 | 1.18 | 0.0591 | **Fluttering** | 0.01 turns / $31.3^\circ$ | Undetermined (stationarity) |
| `design_aluminium_24x1.5` | $24.0 \times 1.5\,\text{mm}$ | 2700.0 | 2.71 | 0.1691 | **Fluttering** | 0.05 turns / $44.9^\circ$ | Fluttering |
| `design_brass_24x3.0` | $24.0 \times 3.0\,\text{mm}$ | 8500.0 | 8.52 | 1.0646 | **Fluttering** | 0.02 turns / $170.4^\circ$ | Tumbling (16.5 turns) |
| `design_brass_24x3.5` | $24.0 \times 3.5\,\text{mm}$ | 8500.0 | 8.52 | 1.2421 | **Tumbling** | 7.04 turns / $2533.2^\circ$ | Tumbling |
| `design_steel_24x4.5` | $24.0 \times 4.5\,\text{mm}$ | 7850.0 | 7.87 | 1.4748 | **Mixed** | 0.01 turns / $389.3^\circ$ | Mixed |
| `design_lead_24x3.5` | $24.0 \times 3.5\,\text{mm}$ | 11340.0 | 11.36 | 1.6571 | **Mixed** | 1.48 turns / $929.1^\circ$ | Mixed |
| `design_tungsten_24x3.0` | $24.0 \times 3.0\,\text{mm}$ | 19250.0 | 19.29 | 2.4111 | **Mixed** | 0.67 turns / $1131.4^\circ$ | Mixed |

---

## 7. Canonical Benchmark Reference Reproduction

Using the reference ODE solver matching the Andersen-Pesavento-Wang formulation at $t^* = 50$ ($[0, -1, 0.1, 0]$ with $\delta\theta = 0.0$):
- **$I^* = 1.1$ (Fluttering):** Reaches $(7.32, -32.99) a$, matching reference $(7.3, -33.0) a$ within **$0.02 a$**.
- **$I^* = 1.4$ (Tumbling):** Reaches $(-26.11, -24.28) a$, matching reference $(-26.1, -24.3) a$ within **$0.02 a$**.
- **$I^* = 1.6$ (Mixed):** Reaches $(6.09, -29.31) a$, matching reference $(6.1, -29.3) a$ within **$0.01 a$**.

All cases are within the strict $0.3 a$ acceptance tolerance.

---

## 8. Verified Test Suite Status

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Autumn coin
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 23 items

tests\test_added_mass.py ...                                             [ 13%]
tests\test_dimensions_and_lift.py ..                                     [ 21%]
tests\test_energy.py ..                                                  [ 30%]
tests\test_forces.py ...                                                 [ 43%]
tests\test_numerics.py ..                                                [ 52%]
tests\test_reference_repro.py ..                                         [ 60%]
tests\test_regimes.py ........                                           [ 95%]
tests\test_terminal_velocity.py .                                        [100%]

============================= 23 passed in 21.67s =============================
```

```
[doctest] doctest version is "2.4.11"
[doctest] run with "--help" for options
===============================================================================
[doctest] test cases:  10 |  10 passed | 0 failed | 0 skipped
[doctest] assertions: 641 | 641 passed | 0 failed |
[doctest] Status: SUCCESS!
```

```
======================================================================
  AUTUMN COIN: JS CORE PHYSICS & REGIME CLASSIFIER TEST SUITE
======================================================================
✓ Extracted and evaluated // <CORE> block in pure Node VM context.
✓ Classifier thresholds verified against config/base.yaml.
✓ All 3 canonical reference cases reproduced within strict 0.3 a tolerance.
✓ All 9 catalog coins match results/coin_regimes.csv exactly.
✓ Presets [2]-[4] correctly map to verified catalog coins, Preset [1] disabled.
======================================================================
  ALL JS TESTS PASSED SUCCESSFULLY (100% PARITY)
======================================================================
```
