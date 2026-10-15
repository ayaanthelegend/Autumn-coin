# Autumn Coin: Step 1, Quasi-Steady ODE Model of a Falling Plate (2D)

> This file is the single source of truth for the agent. Read it once, then build.
> Do NOT re-read the whole file every step: use the section index below.

## 0. Section index

1. Goal and scope
2. Working rules for the agent
3. Repository layout (every file and what goes in it)
4. Physics spec (equations, coefficients, nondimensional numbers)
5. Numerics
6. Parameter sets
7. Experiments / parameter sweeps
8. Output and plot specs
9. Acceptance tests (must pass before moving on)
10. Task order (checklist)
11. Handoff for external review
12. Known uncertainties

---

## 1. Goal and scope

Build a Python implementation of a **2D quasi-steady model** of a thin plate (the cross-section of a coin) falling through water, after Andersen, Pesavento and Wang, *J. Fluid Mech.* 541 (2005) and Pesavento and Wang, *PRL* 93 (2004).

The model must reproduce, qualitatively:

- **steady descent**
- **fluttering** (side-to-side oscillation, no full rotation)
- **tumbling** (continuous rotation with drift)
- a **chaotic / mixed** regime between them

as the dimensionless moment of inertia `I*` and Reynolds number `Re` change.

This model is the reference for later steps (a 2D SPH + rigid-body FSI sim in Unity, and a comparison with literature data). **Out of scope for this step:** SPH, Unity, 3D, any experimental or fabricated data. All outputs are *simulation results*; label them as such everywhere.

## 2. Working rules for the agent

- Python 3.10+, `numpy`, `scipy`, `matplotlib`, `pytest`, `pyyaml`. No other dependencies without asking.
- Work in small steps following section 10. After each step: run tests, then commit.
- Keep all physical coefficients in `config/*.yaml`, never hardcoded in the solver.
- Every function that implements a formula gets a docstring with the equation and its source.
- Do not invent coefficients. If a value is marked `VERIFY` (section 12), implement it as a config default and print a one-line warning on first use.
- Fixed random seeds. Every run writes its config next to its output.
- Keep console output short. Write details to log files in `results/`.
- Do not modify files under `tests/` just to make tests pass. If a test fails, fix the model or report it.

## 3. Repository layout

```
autumn-coin-sim/
  README.md                      # this file
  requirements.txt
  config/
    base.yaml                    # fluid + numerics + coefficient defaults
    coin_sets.yaml               # plate/coin parameter sets (section 6)
    sweeps.yaml                  # sweep definitions (section 7)
  src/autumn/
    __init__.py
    params.py                    # dataclasses, config loading, derived quantities
    added_mass.py                # m11, m22, I_a for an ellipse
    forces.py                    # circulation, drag/lift coefficients, drag force, torque
    model.py                     # rhs(t, state, params) -> d(state)/dt
    integrate.py                 # solve_ivp wrapper, event for hitting the bottom
    dimensionless.py             # I*, Re, Fr, St, regime classifier
    metrics.py                   # post-processing: tilt stats, frequency, mean speed, energy
    sweeps.py                    # run sweeps over (I*, release angle, perturbation)
    plotting.py                  # all figures (section 8)
  scripts/
    run_single.py                # one drop: config name -> trajectory CSV + plots
    run_sweep.py                 # a sweep from sweeps.yaml
    make_regime_map.py           # I* vs Re regime diagram
    make_summary.py              # writes results/SUMMARY.md for external review
  tests/
    test_added_mass.py
    test_forces.py
    test_terminal_velocity.py
    test_energy.py
    test_regimes.py
  results/                       # generated, gitignored except SUMMARY.md
    single/<run_id>/{config.yaml,trajectory.csv,*.png}
    sweeps/<sweep_id>/{config.yaml,runs.csv,*.png}
    SUMMARY.md
```

## 4. Physics spec

### 4.1 Geometry and masses (per unit depth)

Plate cross-section = ellipse with semi-axes `a` (major, half-chord) and `b` (minor, half-thickness).

- chord `L = 2a`, thickness `h = 2b`, area `A = pi*a*b`
- solid mass `m = rho_s * A`, displaced fluid mass `m_f = rho_f * A`
- solid moment of inertia `I = m*(a^2 + b^2)/4`

Coin mapping: coin diameter `D -> L`, coin thickness `h -> h`. This is a 2D cross-section approximation; state this in all captions.

### 4.2 Added mass (ellipse, potential flow)

```
m11 = rho_f * pi * b^2        # along the major axis
m22 = rho_f * pi * a^2        # along the minor axis
I_a = rho_f * pi * (a^2 - b^2)^2 / 8
```

### 4.3 State vector

`state = [X, Y, theta, u, v, omega]`

- `(X, Y)` lab-frame position, Y up, gravity `-Y`
- `theta` angle of the major axis from the +X axis
- `(u, v)` velocity components in the **body frame** (u along the major axis, v along the minor axis)
- `omega = d(theta)/dt`

Kinematics:

```
dX/dt = u*cos(theta) - v*sin(theta)
dY/dt = u*sin(theta) + v*cos(theta)
dtheta/dt = omega
```

### 4.4 Dynamics (Kirchhoff + quasi-steady forces)

```
(m + m11) du/dt = (m + m22) v*omega - rho_f*Gamma*v - F_u - (m - m_f) g sin(theta)
(m + m22) dv/dt = -(m + m11) u*omega + rho_f*Gamma*u - F_v - (m - m_f) g cos(theta)
(I + I_a) domega/dt = (m11 - m22) u*v - tau
```

Sign convention check is mandatory (section 9, tests 3 and 4). If a sign test fails, fix the signs, not the test.
*Note:* Circulation lift is dimensional: $\rho_f \Gamma V$ (in body components $\rho_f \Gamma v$ and $\rho_f \Gamma u$).

### 4.5 Circulation (Kutta-Joukowski, with rotational part)

```
alpha  = atan2(-v, u)                  # angle of attack (document your convention)
Gamma  = -C_T * L * (u*v / |V|)  + 0.5 * C_R * L^2 * omega
|V|    = sqrt(u^2 + v^2)               # guard: if |V| < eps, translational term = 0
```

Note: With $C_L(\alpha) = 2\Gamma / (|V| L)$, the convention $\Gamma_{\text{trans}} = -C_T L (u v / |V|)$ gives $C_L(\alpha) = C_T \sin(2\alpha)$, peaking at $C_{L,\max} = C_T = 1.2$ at $\alpha = 45^\circ$.
Defaults: `C_T = 1.2`, `C_R = pi` (verified against Andersen et al. 2005b).

### 4.6 Viscous drag and torque

```
C_D(alpha) = C_D0 - C_D1 * cos(2*alpha)        # defaults C_D0 = 1.4, C_D1 = 1.0 (VERIFY)
F_u = 0.5 * rho_f * L * C_D(alpha) * |V| * u
F_v = 0.5 * rho_f * L * C_D(alpha) * |V| * v
tau = 0.5 * C_tau * rho_f * L^4 * |omega| * omega   # default C_tau = 0.075 (strip theory C_D / 32; tunable)
```

Optionally add a small linear rotational damping `tau_lin = c_lin * omega` for numerical stability. Default `c_lin = 0`.

### 4.7 Nondimensional numbers (implement in `dimensionless.py`)

```
I_star = (rho_s * h) / (rho_f * L)             # 2D plate dimensionless moment of inertia
U_t    = sqrt((rho_s/rho_f - 1) * g * h)       # velocity scale (Froude-type)
Re     = rho_f * U * L / mu                    # use measured mean descent speed for U
St     = f * L / U                             # f = dominant oscillation frequency
```

Do NOT use `I/(m R^2)`: it is constant for a solid disk and carries no information.

### 4.8 Regime classifier

From each trajectory, after discarding the initial transient (first 10 percent of fall height):

- `theta_range = max(theta) - min(theta)`; `n_flips` = count of full 2*pi rotations of `theta`
- **steady**: `theta_range < 0.2 rad` and tilt variance below a threshold (`var_theta_steady`)
- **fluttering**: `theta` oscillates, `n_flips == 0`
- **tumbling**: `n_flips >= 2` with a consistent rotation direction
- **mixed / chaotic**: anything else (e.g. flutter with occasional flips)

All thresholds are config values in `base.yaml`. Print the classification counts per sweep.

## 5. Numerics

- Integrator: `scipy.integrate.solve_ivp`, method `DOP853`, `rtol=1e-9`, `atol=1e-11`.
- Dense output sampled at a fixed `dt_out` (default 1e-3 s) for post-processing.
- Terminal event: fall depth reaches `H_fall` (default 40 L). Adaptive $t_{\max} \approx 3 \text{--} 5 \times H_{\text{fall}} / U_{\text{terminal}}$ with timeout flagging.
- Use SI units everywhere. Fluid: water at 20 C, `rho_f = 998`, `mu = 1.0e-3`, `g = 9.81`.
- Verify convergence: tightening tolerances by 10x must change landing x by < 0.1 percent of chord $L$ for a non-chaotic fluttering case.

## 6. Parameter sets (`config/coin_sets.yaml`)

Define each set by `rho_s`, `L`, `h`, `a/b = L/h`. Include at least:

| name               | role                                | rho_s [kg/m3] | L [mm] | h [mm] |
| ------------------ | ----------------------------------- | ------------- | ------ | ------ |
| `reference_card` | baseline for flutter/tumble physics | 1200          | 20     | 2      |
| `heavy_coin`     | metal coin, high I*                 | 7800          | 24     | 1.8    |
| `light_coin`     | low I*                              | 2700          | 24     | 1.8    |
| `washer_proxy`   | lower effective density (hole)      | 4000          | 24     | 1.8    |

These values are illustrative inputs for simulation, **not measurements**. Include a `notes` field per set stating that.

## 7. Experiments / sweeps (`config/sweeps.yaml`)

1. **I\* sweep** (main result): `I*` from 0.05 to 5 (log spaced, 25 values). Scaled physically with aspect ratio $h/L \in [0.04, 0.25]$ such that $\rho_s/\rho_f \le 20$. Release angle 5 deg off horizontal plus small noise.
2. **Release angle sweep**: 0 to 90 deg, 19 values, at three `I*` values (low $0.2$, transition $0.8$, tumble $3.5$).
3. **Ensemble for chaos statistics**: for each of 3 selected `I*`, 50 drops with `theta0 ~ N(mu, 0.5 deg)` and `u0, v0 ~ N(0, 1e-4 m/s)`; seed fixed. Outputs: mean trajectory, 1-sigma band, landing scatter.
4. **Viscosity dependence & regime map**: The quasi-steady formulation carries no explicit viscosity dependence in its force terms (fixed coefficients). The Reynolds number Re is evaluated a posteriori from the measured mean descent speed U via Re = rho_f * U * L / mu. Viscosity is probed through physical scaling of rho_s, L, and h, while true viscous Re dependence is reserved for the 2D SPH step.
5. **Regime map**: grid over I* and Re (evaluated a posteriori across physical variations of rho_s, L, h), classifying each cell.

## 8. Output and plot specs

Matplotlib, white background, dark text and axes (no theme-dependent light text), 300 dpi PNG plus PDF.
Every plot title or caption must say "2D quasi-steady model simulation".

1. Single drop: trajectory in the X-Y plane (orientation arrows every N frames), `theta(t)`, speed vs time.
2. Ensemble: mean trajectory with 1-sigma band, landing scatter (rose / scatter), histogram of landing x.
3. I\* sweep: regime vs `I*`, mean descent speed vs `I*`, lateral drift vs `I*`.
4. Phase diagram: `I*` vs `Re` with regime colours, one legend, no overlapping labels.
5. Energy budget: potential, kinetic (translational + rotational), cumulative dissipated energy; total must reconcile to within 1 percent.
6. Frequency analysis: FFT of `theta(t)` in the fluttering regime; report `St`.
   CSV for every figure's underlying data in the same folder.

## 9. Acceptance tests (pytest, all must pass)

1. **Added mass**: for `a == b` (circle), `m11 == m22` and `I_a == 0`.
2. **No forces (Kirchhoff conservation)**: zero drag, zero circulation, zero torque, zero gravity: total kinetic energy $T$ is constant (to 1e-8) and lab-frame linear momentum rotated from $((m+m_{11})u, (m+m_{22})v)$ is constant (to 1e-8). For a circular plate ($a = b$), lab velocity and angular momentum are strictly constant.
3. **Broadside terminal velocity**: start with the plate horizontal (`theta = 0`) and tiny noise suppressed. Terminal speed must match the drag balance `0.5*rho_f*C_D*L*U^2 = (rho_s - rho_f)*g*A` within 2 percent (use the `C_D` at the correct `alpha`).
4. **Sign check**: a plate released with `theta = 0` and zero velocity falls straight down in the absence of perturbations, never drifting sideways by more than `1e-6 L` when noise is off.
5. **Energy**: with drag, torque, and circulation work all included, the energy budget closes to within 1 percent over a full drop, normalized by the potential energy drop $(m - m_f) g H_{\text{fall}}$.
6. **Regime ordering**: at fixed `Re`-range, the classifier gives fluttering or steady for the smallest `I*` in the sweep and tumbling for the largest. Do not hardcode the critical value: report where the transition occurs.
7. **Convergence**: tolerance tightened 10x changes a non-chaotic fluttering landing position by less than 0.1 percent of chord $L$.
8. **Reproducibility**: same seed, same CSV (byte-identical).

## 10. Task order (tick off in order; commit after each)

- [X] 1. Scaffold repo, `requirements.txt`, configs, `params.py`
- [X] 2. `added_mass.py` + test 1
- [X] 3. `forces.py`, `model.py` + tests 2, 3, 4
- [X] 4. `integrate.py`, `run_single.py`, first single-drop plots
- [X] 5. `dimensionless.py`, `metrics.py`, regime classifier + test 6
- [X] 6. Energy budget + test 5
- [X] 7. Convergence and reproducibility tests (7, 8)
- [X] 8. Sweeps (section 7) and sweep plots
- [X] 9. Regime map
- [X] 10. `make_summary.py` (section 11)

## 11. Handoff for external review

Generate `results/SUMMARY.md` containing:

- git commit hash, Python and package versions
- the full coefficient table actually used (every `VERIFY` item, its value, its source)
- test results (pass/fail list)
- for each sweep: number of runs, regime counts, the estimated transition `I*`
- the 10 most important figures (file paths)
- any test that was relaxed, any coefficient tuned, and why
- a short "Observed disagreements with literature" section (even if empty)

To review the model, share: `README.md`, `results/SUMMARY.md`, `src/autumn/forces.py`, `src/autumn/model.py`, and the regime map and a single-drop figure.

## 12. Known uncertainties (flag these, do not silently fix)

| item                                          | default                                   | status                                     |
| --------------------------------------------- | ----------------------------------------- | ------------------------------------------ |
| `C_T`, `C_R`                              | 1.2, pi                                   | VERIFY against Andersen et al. 2005        |
| `C_D(alpha)` form and constants             | 1.4 - 1.0 cos(2 alpha)                    | VERIFY                                     |
| rotational torque form and `C_tau`          | 0.5 C_tau rho_f L^4 abs(omega) omega, 0.2 | tunable, must be documented                |
| angle-of-attack sign convention               | `alpha = atan2(-v, u)`                  | check with tests 3 and 4                   |
| 2D approximation of a 3D coin                 | n/a                                       | limitation: state in paper                 |
| critical `I*` for flutter-tumble transition | none                                      | must emerge from the model, not be assumed |

Rules: if the model output disagrees with the literature, report it in `SUMMARY.md` and do not tune coefficients to hide it without documenting what was tuned.
