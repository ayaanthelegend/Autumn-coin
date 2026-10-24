# Autumn Coin: Fluid Dynamics of Falling Disks & Plates

[![Python Tests](https://img.shields.io/badge/pytest-23%20passed-brightgreen.svg)]()
[![C++ Core Tests](https://img.shields.io/badge/catch2-10%20passed-brightgreen.svg)]()
[![SPH Validation](https://img.shields.io/badge/sph_tests-7%2F7%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An end-to-end computational and theoretical investigation of **IYPT 2026 Problem 12: Autumn Coin**, investigating the complex trajectory bifurcation (steady descent, periodic fluttering, chaotic tumble-glide, and autorotation) of coins and planar plates falling through viscous fluids.

The project combines four synchronized computational tools:
1. **2D Quasi-Steady Kirchhoff ODE Model (Python)**: High-precision adaptive Runge-Kutta integrator (`DOP853`) capturing translational/rotational added mass, Kutta-Joukowski circulation, angle-of-attack dependent drag, and nonlinear damping.
2. **High-Performance C++ Desktop Visualizer (`autumn-coin-cpp/`)**: Real-time simulation and visualization using Raylib, Dear ImGui, and ImPlot with interactive parameter tuning and headless CI support.
3. **2D Weakly Compressible Smoothed Particle Hydrodynamics Solver (`cpp_sph/`)**: Direct Navier-Stokes fluid-structure interaction (FSI) solver coupling weakly compressible SPH (Wendland $C_2$ kernel) with moving rigid body boundaries.
4. **Single-File Modern Web Visualizer (`visualizer.html`)**: Interactive browser simulator featuring dual-mode physics (Mode A: 2D ODE, Mode B: 2D SPH-FSI numerical illustration), responsive layout, and real-time trajectory analytics.

---

## Repository Structure

```
Autumn-coin/
├── config/                      # Simulation configurations & coin geometry sets
│   ├── base.yaml                # Hydrodynamic parameters, classifier thresholds, numerics
│   └── coin_sets.yaml           # Physical coin & plate geometries (CZK, EUR, cards)
├── src/autumn/                  # Core Python quasi-steady ODE package
│   ├── added_mass.py            # Analytical potential flow added mass & inertia
│   ├── forces.py                # Circulation, viscous drag, and damping torque
│   ├── model.py                 # Kirchhoff equations of motion (RHS)
│   ├── integrate.py             # DOP853 numerical time integration & event detection
│   ├── metrics.py               # Energy accounting, FFT analysis, trajectory summary
│   ├── dimensionless.py         # Nondimensional scaling (I*, Re, St) & regime classifier
│   └── params.py                # Dataclasses and YAML configuration loader
├── tests/                       # Complete pytest suite (16 unit and acceptance tests)
├── scripts/                     # Production scripts for scientific studies & presentation
│   ├── make_bisection_study.py  # High-precision bisection for critical I*_c vs literature
│   ├── make_regime_map.py       # 60-point (I*, Re) phase space regime map
│   ├── make_presentation.py     # Generates the complete 24-slide IYPT deck
│   └── check_slide_numbers.py   # Automated consistency audit for presentation slides (9/9 audits passed)
├── autumn-coin-cpp/             # Native C++ port & interactive visualizer
│   ├── src/                     # C++ model, integrator, and Raylib/ImGui visualizer
│   ├── include/autumn/          # C++ header definitions
│   └── tests/                   # Native C++ Catch2 unit test suite
├── cpp_sph/                     # 2D SPH FSI solver
│   ├── src/                     # SPH solver, Wendland C2 kernel, rigid body coupling
│   └── include/                 # SPH header files
├── scripts_sph/                 # Automated runners for SPH drops and post-processing
├── results/                     # ODE outputs, phase diagrams, and SUMMARY.md
├── results_sph/                 # SPH drop CSVs, validation logs, and SUMMARY_SPH.md
├── docs/                        # Technical documentation & developer notes
├── tools/                       # Development maintenance and verification utilities
└── references.md                # Complete bibliography of peer-reviewed literature
```

---

## Physics & Hydrodynamic Formulation

The 2D equations of motion for a plate falling under gravity through an incompressible fluid are formulated in the body-fixed coordinate frame $(u, v, \omega)$ following Kirchhoff's equations with quasi-steady hydrodynamic forces (Andersen, Pesavento & Wang, *J. Fluid Mech.* 2005):

$$\begin{aligned}
(m + m_{11})\dot{u} &= (m + m_{22})v\omega - F_L \sin\alpha - F_{D,u} - (m - m_f)g\sin\theta \\
(m + m_{22})\dot{v} &= -(m + m_{11})u\omega + F_L \cos\alpha - F_{D,v} - (m - m_f)g\cos\theta \\
(I + I_a)\dot{\omega} &= (m_{11} - m_{22})uv - \tau_{\text{diss}}
\end{aligned}$$

Where:
- **Added Mass**: $m_{11} = \rho_f \pi b^2$, $m_{22} = \rho_f \pi a^2$, and $I_a = \frac{1}{8}\rho_f \pi (a^2 - b^2)^2$.
- **Circulation & Lift**: $\Gamma = -C_T L \frac{uv}{|V|} + \frac{1}{2} C_R L^2 \omega$, with peak $C_{L,\max} = C_T = 1.2$ at $\alpha = 45^\circ$.
- **Viscous Drag**: $C_D(\alpha) = C_{D0} - C_{D1}\cos(2\alpha)$, with $C_D(0^\circ) = 0.4$ (edge-on) and $C_D(90^\circ) = 2.4$ (broadside).
- **Damping Torque**: $\tau_{\text{diss}} = \frac{1}{2}C_\tau \rho_f L^4 |\omega|\omega + c_{\text{lin}}\omega$, with literature baseline $\mu_1 = 0.20$ yielding $c_{\text{lin}} = \frac{\pi}{8}\rho_f L^3 U_0 \mu_1$.

---

## Installation & Setup

### Python Environment
Requires Python 3.10+ (tested on Python 3.14).

```bash
# Clone the repository
git clone https://github.com/ayaanthelegend/Autumn-coin.git
cd Autumn-coin

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Building C++ Core & Visualizer (`autumn-coin-cpp`)
Prerequisites: CMake 3.20+ and a C++20 compiler (MSVC 2022, GCC 11+, or Clang 13+).

```bash
cd autumn-coin-cpp
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release

# To build headless tests only (e.g. on Linux servers without X11):
cmake -B build -S . -DAUTUMN_BUILD_VIZ=OFF
cmake --build build --target autumn_tests
```

### Building SPH Solver (`cpp_sph`)
Using the provided MSVC build utility or standard C++20 compiler:

```bash
python cpp_sph/build.py
```

---

## Verification & Testing

### 1. Python Acceptance Test Suite
Runs the 23 full unit and acceptance tests covering added-mass limits, Kirchhoff momentum conservation, broadside terminal velocity, energy budget closure to $< 10^{-4}\%$, universal perturbation at all angles, symmetry-breaking warnings, edge-on instability, 180° parity, chord scale invariance, and extended horizon-doubling convergence ($N=80$ vs $160$ across $I^*=1.2, 1.25, 1.3, 1.5, 2.0, 2.41, 3.0, 3.5$):

```bash
python -m pytest
```

### 2. C++ Parity & Unit Tests
Executes 10 Catch2/doctest test cases (641 assertions) compiled with `/we4062` / `-Wswitch -Werror`, validating C++ ODE rhs evaluation, cross-compiler compatibility, coordinate symmetries, `Regime::Undetermined` handling, and exact numeric parity against Python DOP853 outputs:

```bash
./autumn-coin-cpp/build/autumn_tests
```

### 3. SPH FSI Solver Verification & Validation Suite
Runs the formal 7-test suite split into Verification (analytical Navier-Stokes solutions: partition of unity, hydrostatic buoyancy, viscous Couette / Taylor-Green decay) and Validation (2D dam-break benchmark, cylinder drag scaling, added-mass stability, and multi-grid developed descent convergence with $\epsilon_{23} \le 5\%$ threshold):

```bash
./cpp_sph/bin/sph_runner.exe --all-tests
```

### 4. Browser Visualizer Core Parity Tests
Validates the pure-JS ODE solver, RK4 substep integrator, and regime classifier in `visualizer.html` against Python reference outputs:

```bash
node --test tests_js/test_core.mjs
```

---

## Reproducing Key Results

### 1. Critical $I^*_c$ Bisection Study
Determines the flutter-to-tumble bifurcation boundary across damping values $\mu_1 \in \{0, 0.01, 0.05, 0.1, 0.2\}$ and release angles $\theta_0 \in \{5^\circ, 20^\circ, 45^\circ\}$:

```bash
python scripts/make_bisection_study.py
```
*Results*: Baseline $\mu_1 = 0.20$ gives $I^*_c = 1.213$ ($[1.2113, 1.2146]$), within **+1.1%** of Andersen et al. (2005b) experimental card transition midpoint ($1.20$, band $[1.10, 1.30]$).

### 2. 2D Regime Map in $(I^*, \text{Re})$ Space
Generates the 136-point phase diagram with physical thickness rule $h/L(I^*)$ capping $\rho_s/\rho_f \le 20.0$, dimensionless transient discard $t_\text{transient} = \max(20\tau_0, 0.2 t_\text{end})$, post-transient stationarity checks, and dual stopping criteria ($N \ge 80\tau_0$ and $Y \le -H_\text{fall}$):

```bash
python scripts/make_regime_map.py
```

### 3. IYPT 22-Slide Deck Generation
Builds the full 22-slide PowerPoint presentation with live tables and figures:

```bash
python scripts/make_presentation.py
python scripts/check_slide_numbers.py  # Runs automated audit across all 22 slides
```

---

## Key Findings & Highlights

1. **Literature Baseline Alignment**: Using the literature damping parameter $\mu_1 = 0.20$ from Andersen et al. (2005b) yields $I^*_c = 1.213$, achieving $+1.1\%$ agreement with empirical falling card transitions without artificial tuning.
2. **Instability of Symmetric Starts**: Both broadside ($\theta_0 = 0^\circ, 180^\circ$) and edge-on ($\theta_0 = 90^\circ, 270^\circ$) releases represent exact mathematical saddle points. Under physical perturbation ($\delta\theta = 10^{-3}\text{ rad}$), zero steady descent states survive across the tested catalog ($I^* \in [0.02, 3.50]$); all low-$I^*$ drops develop periodic limit-cycle flutter ($> 30^\circ$ amplitude).
3. **Refined Tumbling & Flutter Attractors**: Tumbling occurs within $I^* \in [1.25, 1.45]$ for $\mu_1 = 0.20$. For $I^* \ge 3.0$ with physical thickness $h/L = I^*/20.0$ ($\rho_s/\rho_f \le 20.0$), plates settle into a stable periodic limit-cycle flutter (15+ cycles, stationarity variation $< 0.3\%$).
4. **Dimensionless Horizon & Stationarity**: Integrating for $N \ge 80\tau_0$ with transient discard $\max(20\tau_0, 0.2 t_\text{end})$ and stationarity tolerance ($15\%$) eliminates truncation artifacts and guarantees scale invariance across chord lengths.
5. **Energy Conservation**: Numerical energy accounting tracks kinetic, potential, and cumulative viscous dissipation, demonstrating energy closure within $< 0.001\%$ across entire drops.
6. **SPH Shock Mitigation**: Eliminating impulsive particle initialization shocks via geometric solid pre-carving and initial relaxation enables smooth gravitational start-up from rest ($|V|(1\,\text{ms}) \le 0.006\,\text{m/s}$).

---

## References & Bibliography
See [`references.md`](references.md) for complete citations of foundational literature (Field et al. 1997, Andersen et al. 2005a, 2005b, Pesavento & Wang 2004, Akinci et al. 2012, ondrej-cloud 2026).

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
