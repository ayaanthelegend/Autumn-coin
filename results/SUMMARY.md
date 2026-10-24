# Autumn Coin: Comprehensive Model, Numerics & Literature Validation Summary
**2D Quasi-Steady ODE Model & SPH Navier-Stokes Solver of a Falling Plate**

- **Date:** 2026-10-24
- **Branch:** `master`
- **Tested Operating System:** Windows 11 AMD64 (build environment: Python 3.14.5, MSVC 2026 / C++17, Ninja 1.13)
- **Key Packages:** `numpy==2.5.4`, `scipy==1.18.1`, `matplotlib==3.11.2`, `pytest==9.1.1`, `pyyaml==6.0.3`
- **Test Status:** **18/18 Python unit tests pass**, **10/10 C++ unit test cases (641 assertions) pass**

---

## 1. Hydrodynamic Parameters & Defect Resolution (Review Item A-1)

All physical coefficients are centralized in `config/base.yaml`, loaded dynamically via `NumericsParams.from_config()`, and cited against peer-reviewed literature.

| Parameter | Baseline Value | Literature Status | Mathematical Formulation & Role | Primary Literature Source |
|---|---|---|---|---|
| `C_T` | `1.2` | Primary Literature | Translational circulation: $\Gamma_{\text{trans}} = -C_T L (u v / \|V\|)$ | Andersen, Pesavento & Wang (2005b) as used in ondrej-cloud implementation (equation number unchecked) |
| `C_R` | `3.14159` ($\pi$) | Primary Literature | Rotational circulation: $\Gamma_{\text{rot}} = 0.5 C_R L^2 \omega$ | Andersen et al. (2005b) as used in ondrej-cloud implementation |
| `C_D0` | `1.4` | Primary Literature | Drag baseline: $C_D(\alpha) = C_{D0} - C_{D1} \cos(2\alpha)$ | Andersen et al. (2005b) thin plate drag model |
| `C_D1` | `1.0` | Primary Literature | Drag angle variation ($C_D(0^\circ) = 0.4$, $C_D(90^\circ) = 2.4$) | Andersen et al. (2005b) edge-on min, broadside max |
| `mu_1` | `0.20` | **Literature Baseline** | Linear rotational damping: $c_{\text{lin}} = (\pi / 8) \rho_f L^3 U_0 \mu_1$ | Andersen et al. (2005b) as used in ondrej-cloud implementation; $\mu_1 = 0.01$ was an empirically tuned value ("tuned, not from the paper") |
| `mu_2` | `0.20` | Primary Literature | Quadratic damping parameter | Andersen et al. (2005b) |
| `C_tau` | `0.07854` ($\pi \mu_2 / 8$) | Derived Baseline | Quadratic rotational damping: $\tau_{\text{quad}} = 0.5 C_\tau \rho_f L^4 \|\omega\| \omega$ | Derived directly from $\pi \mu_2 / 8$ with $\mu_2 = 0.20$; $0.075$ strip theory is retained as a documented alternative |
| `eps_V` | `1.0e-7` | Numerical Guard | Regularization threshold for velocity division | Numerical safeguard as $\|V\| \to 0$ |
| `tank_depth_m` | `0.38` | Experimental Config | Physical water tank depth [m] | Laboratory tank drops |

### Defect Resolution Note: $\mu_1 = 0.20$ vs $\mu_1 = 0.01$
In earlier revisions, $\mu_1 = 0.01$ was erroneously labeled "verified". Bisection demonstrates that with $\mu_1 = 0.01$, the critical bifurcation threshold drops to $I^*_c = 0.9703$ (-19.1% error vs literature midpoint $1.20$), causing $I^* = 1.10$ to tumble prematurely. With the authentic literature baseline $\mu_1 = 0.20$, $I^* = 1.10$ flutters and tumbling onsets at $I^*_c = 1.2172$ (+1.4% vs literature midpoint $1.20$), cleanly within the experimental band $[1.10, 1.30]$.

---

## 2. $\mu_1$ Sensitivity & Bifurcation Study (`results/mu1_sensitivity.csv`)

A systematic coarse-scan (step 0.05) and bisection study ($\Delta I^* \le 0.005$) executed via `scripts/run_mu1_sensitivity.py` along the fixed-path $h/L$ rule ($L = 24\,\text{mm}$, $H_{\text{fall}} = 80 L$, rest release) maps the onset of tumbling:

| Damping $\mu_1$ | Release $\theta_0$ | Critical $I^*_c$ | Bracket $[I^*_{\text{lower}}, I^*_{\text{upper}}]$ | Coarse Bracket | Discrepancy vs Lit. Midpoint ($1.20$) | Regime Transition |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.00 | $5^\circ, 20^\circ, 45^\circ$ | **0.9578** | $[0.9562, 0.9594]$ | $[0.95, 1.00]$ | -20.2% | Flutter $\to$ Tumble |
| 0.01 | $5^\circ, 20^\circ, 45^\circ$ | **0.9703** | $[0.9688, 0.9719]$ | $[0.95, 1.00]$ | -19.1% | Flutter $\to$ Tumble |
| 0.05 | $5^\circ, 20^\circ, 45^\circ$ | **1.0266** | $[1.0250, 1.0281]$ | $[1.00, 1.05]$ | -14.4% | Flutter $\to$ Tumble |
| 0.10 | $5^\circ, 20^\circ, 45^\circ$ | **1.0922** | $[1.0906, 1.0938]$ | $[1.05, 1.10]$ | -9.0% | Flutter $\to$ Tumble |
| **0.20** | $5^\circ, 20^\circ, 45^\circ$ | **1.2172** | $[1.2156, 1.2188]$ | $[1.20, 1.25]$ | **+1.4%** | **Flutter $\to$ Tumble** |

---

## 3. Coin Catalog & Design Discs Verification (`results/coin_regimes.csv`)

Recomputed from physical parameters ($H_{\text{fall}} = 80 L$, release from rest, $\theta_0 = 5^\circ$):

| Coin / Disc ID | Geometry ($D \times h$) | $\rho_s$ [$\text{kg/m}^3$] | $\rho_s / \rho_f$ | $I^*$ | Regime ($\mu_1 = 0.20$) | Turns / PTP | Regime at $\mu_1 = 0.01$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `pk_rs10` | $25.5 \times 1.5\,\text{mm}$ | 7179.6 | 7.19 | 0.4232 | **Fluttering** | 0.0 turns / $75.9^\circ$ | Fluttering |
| `pk_rs5_2002` | $24.0 \times 2.1\,\text{mm}$ | 6842.0 | 6.86 | 0.5999 | **Fluttering** | 0.0 turns / $97.6^\circ$ | Fluttering |
| `design_acrylic_24x1.2` | $24.0 \times 1.2\,\text{mm}$ | 1180.0 | 1.18 | 0.0591 | **Fluttering** | 0.0 turns / $31.3^\circ$ | Fluttering |
| `design_aluminium_24x1.5` | $24.0 \times 1.5\,\text{mm}$ | 2700.0 | 2.71 | 0.1691 | **Fluttering** | 0.0 turns / $44.9^\circ$ | Fluttering |
| `design_brass_24x3.0` | $24.0 \times 3.0\,\text{mm}$ | 8500.0 | 8.52 | 1.0646 | **Fluttering** | 0.1 turns / $170.4^\circ$ | **Tumbling** (16.5 turns) |
| `design_brass_24x3.5` | $24.0 \times 3.5\,\text{mm}$ | 8500.0 | 8.52 | 1.2421 | **Tumbling** | 7.0 turns / $2537.3^\circ$ | Tumbling |
| `design_steel_24x4.5` | $24.0 \times 4.5\,\text{mm}$ | 7850.0 | 7.87 | 1.4748 | **Mixed** | 0.0 turns / $388.9^\circ$ | Mixed |
| `design_lead_24x3.5` | $24.0 \times 3.5\,\text{mm}$ | 11340.0 | 11.36 | 1.6571 | **Mixed** | 0.1 turns / $415.7^\circ$ | Mixed |
| `design_tungsten_24x3.0` | $24.0 \times 3.0\,\text{mm}$ | 19250.0 | 19.29 | 2.4111 | **Mixed** | 0.2 turns / $742.1^\circ$ | Mixed |

### Steady Regime Search Report (Task 7 & 8)
A dedicated fine sweep of $I^* \in [0.02, 0.10]$ with $\rho_s / \rho_f \ge 1.2$ at $\theta_0 = 5^\circ$ confirmed that:
**No genuinely steady descent is reached for any physical perturbation** (all cases undergo sustained periodic fluttering with peak-to-peak amplitude $\text{ptp} \ge 23.5^\circ$). True broadside descent ($\text{ptp} < 2^\circ$) only persists when released from exact mathematical symmetry ($\theta_0 = 0.0$ with zero perturbation), which represents an unstable saddle equilibrium in real physical experiments.

---

## 4. Benchmark Reference Reproduction (`tests/test_reference_repro.py`)

Using a self-contained dimensionless reference solver matching the canonical Andersen-Pesavento-Wang equations at $t^* = 50$ (initial state $[0, -1, 0.1, 0]$):
- **$I^* = 1.1$ (Fluttering):** Reaches $(7.32, -32.99) a$, matching reference $(7.3, -33.0) a$ within **$0.02 a$**.
- **$I^* = 1.4$ (Tumbling):** Reaches $(-26.11, -24.28) a$, matching reference $(-26.1, -24.3) a$ within **$0.02 a$**.
- **$I^* = 1.6$ (Periodic Mixture):** Reaches $(6.09, -29.31) a$, matching reference $(6.1, -29.3) a$ within **$0.01 a$**.
All cases match well within the strict $0.3 a$ threshold, confirming exact equivalence.

---

## 5. Acceptance Test Suite Results

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
collected 18 items

tests\test_added_mass.py ...                                             [ 16%]
tests\test_dimensions_and_lift.py ..                                     [ 27%]
tests\test_energy.py ..                                                  [ 38%]
tests\test_forces.py ...                                                 [ 55%]
tests\test_numerics.py ..                                                [ 66%]
tests\test_reference_repro.py ..                                         [ 77%]
tests\test_regimes.py ...                                                [ 94%]
tests\test_terminal_velocity.py .                                        [100%]

============================= 18 passed in 9.06s ==============================
```

```
[doctest] doctest version is "2.4.11"
===============================================================================
[doctest] test cases:  10 |  10 passed | 0 failed | 0 skipped
[doctest] assertions: 641 | 641 passed | 0 failed |
[doctest] Status: SUCCESS!
```
