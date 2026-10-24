Here is the complete **`README_STEP2_CPP_SPH.md`** file, formatted and ready to be saved directly into your repository for Antigravity CLI:

```markdown
# Autumn Coin: Step 2, 2D SPH Fluid-Structure Interaction (FSI) & Visual Renderer in C++

> This file is the single source of truth for the agent building the Step 2 C++20 2D WCSPH-FSI solver, Sebastian Lague-style real-time visual renderer, and Python post-processing suite. Read it once, then build step-by-step in section 9 order.

## 0. Section Index
1. Goal and Scope
2. Working Rules, C++ Architecture & Honesty Constraints
3. Repository & Directory Layout
4. Physics & Mathematical Specification (2D WCSPH + Akinci Rigid-Fluid Coupling)
5. Nondimensional Parameter Matching, Resolution Limits & Tank Sizing
6. Dual-Mode Visual Renderer (Mode A: ODE Trajectory Replay, Mode B: Live SPH-FSI)
7. Verification, Validation & Convergence Ladder (Tests 1–7)
8. Numerical Experiments & Output Specs
9. Task Order (Checklist)
10. Handoff Summary (`results_sph/SUMMARY_SPH.md`)

---

## 1. Goal and Scope

Build a high-performance **C++20 2D Weakly Compressible Smoothed Particle Hydrodynamics (WCSPH)** solver with two-way rigid-body Fluid-Structure Interaction (FSI) after Akinci et al. (2012), paired with a **Sebastian Lague-inspired 2D visual renderer** (supporting both live interactive OpenGL/Raylib window rendering and headless high-resolution PNG frame export).

### Scope & Honest Limitations:
1. **Single C++20 Codebase (`cpp_sph/`):** One deterministic C++ physics engine (parallelized with OpenMP and compiled with `-O3`) powers the automated validation tests, the batch parameter sweeps, and the visual renderer—eliminating any code divergence between solver and visualizer.
2. **Qualitative Nature of 2D SPH at Moderate $\text{Re}$:** For a thin plate with $h/L \approx 0.08$ at particle spacing $\Delta x = L/24$, the plate thickness spans only $\sim 2$ particles, and the laminar boundary layer ($\delta \sim L/\sqrt{\text{Re}}$) is under-resolved above $\text{Re} \sim 200$. State explicitly in `SUMMARY_SPH.md` and all figure captions that the 2D SPH-FSI results at coin Reynolds numbers are **qualitative / coarse-grained numerical experiments**, and always report the exact number of particles across plate thickness $N_h = h/\Delta x$.
3. **No Pre-Assumed Outcomes:** Measure and report what the solver produces—including any discrepancies, numerical damping, or added-mass instabilities—without tuning parameters to force agreement.

---

## 2. Working Rules & Honesty Constraints

- **Build System & Dependencies:** Standard C++20 with `CMake` (or direct `g++`/`clang++`/`cl` build script), OpenMP for multi-core CPU parallelization, `stb_image_write.h` (single-header, included in `third_party/`) for deterministic headless PNG frame rendering, and optional `raylib` / `GLFW+OpenGL` for the live interactive window. Python (`numpy`, `pandas`, `matplotlib`, `pytest`) is used to orchestrate batch runs, verify test tolerances, and plot publication figures.
- **Strict Labeling:** Every plot, CSV, and rendered frame must be explicitly labeled `"2D SPH-FSI numerical simulation"` (Mode B) or `"2D ODE simulation replay — visualization only"` (Mode A). Never present simulation outputs as experimental data.
- **Visual Style:** All exported plots and C++ rendered frames must use a **white background** (`#FFFFFF`) with dark, high-contrast text, borders, and coin outlines (`#111111`), plus smooth scientific colormaps for particle speed/vorticity.

---

## 3. Repository & Directory Layout

```text
autumn-coin-sim/
├── README.md                        # Step 1 ODE spec
├── README_STEP2_CPP_SPH.md          # Step 2 C++ SPH-FSI spec (this file)
└── cpp_sph/
    ├── CMakeLists.txt               # Builds sph_runner (CLI + headless renderer) and sph_viewer (live GUI)
    ├── third_party/
    │   └── stb_image_write.h        # Single-header PNG writer for guaranteed headless frame export
    ├── include/
    │   ├── config.hpp               # Config structs & simple key-value / JSON / YAML parser
    │   ├── kernels.hpp              # 2D Wendland C2 kernel and verified gradient
    │   ├── spatial_hash.hpp         # O(N) uniform grid spatial hash
    │   ├── fluid_state.hpp          # SoA/AoS fluid particle arrays: x, y, vx, vy, rho, p, ax, ay, vort
    │   ├── rigid_ellipse.hpp        # Elliptical rigid body (a = L/2, b = h/2) + boundary particles
    │   ├── sph_solver.hpp           # Density summation, Tait EOS, Morris viscosity, Akinci FSI
    │   ├── integrator_kdk.hpp       # Synchronous Kick-Drift-Kick integrator for fluid + rigid body
    │   ├── ode_replay.hpp           # Loads Step 1 trajectory.csv for Mode A visualization
    │   └── software_renderer.hpp    # Anti-aliased 2D software/OpenGL particle & wake renderer (Seb Lague style)
    ├── src/
    │   ├── kernels.cpp
    │   ├── spatial_hash.cpp
    │   ├── rigid_ellipse.cpp
    │   ├── sph_solver.cpp
    │   ├── software_renderer.cpp
    │   ├── main_cli.cpp             # CLI entry point: runs validation tests 1-7, drops, CSV & PNG export
    │   └── main_viewer.cpp          # Optional live interactive Raylib/OpenGL window (60 FPS)
    ├── config/
    │   ├── sph_base.cfg
    │   ├── validation_cases.cfg
    │   └── fsi_cases.cfg            # Generated from saved Step 1 ODE runs
    ├── scripts_sph/
    │   ├── run_validation_ladder.py # Compiles C++ solver, runs Tests 1-7, generates benchmark plots
    │   ├── run_fsi_experiments.py   # Runs matched SPH drops, explicit Re sweep, and renders wake PNGs
    │   ├── compare_sph_vs_ode.py    # Compares theta(t), mean speed, frequency, and regime
    │   └── make_sph_summary.py      # Generates results_sph/SUMMARY_SPH.md
    ├── tests_sph/
    │   └── test_sph_suite.py        # Pytest wrapper verifying C++ Tests 1-7
    └── results_sph/
        ├── validation/
        ├── drops/
        │   └── frames/              # Rendered Seb Lague-style particle/vorticity snapshots (PNG)
        ├── comparison/
        └── SUMMARY_SPH.md
```

---

## 4. Physics & Mathematical Specification

### 4.1 2D Wendland $C^2$ Smoothing Kernel & Exact Gradient

For particle separation $r = \vert{}\mathbf{r}_i - \mathbf{r}_j\vert{}$, smoothing length $h_{\text{sml}} = 1.3 \Delta x$, and dimensionless radius $q = r / h_{\text{sml}} \in [0, 2]$ (compact support $r_c = 2 h_{\text{sml}}$):

$$
W(r, h_{\text{sml}}) = \frac{7}{4 \pi h_{\text{sml}}^2} \left(1 - \frac{q}{2}\right)^4 (2q + 1)
$$

Differentiating with respect to $\mathbf{r}_i$ gives the **exact gradient**:

$$
\nabla_i W(\mathbf{r}_{ij}, h_{\text{sml}}) = -\frac{35 q}{4 \pi h_{\text{sml}}^3} \left(1 - \frac{q}{2}\right)^3 \hat{\mathbf{r}}_{ij} = -\frac{35}{4 \pi h_{\text{sml}}^4} \left(1 - \frac{q}{2}\right)^3 (\mathbf{r}_i - \mathbf{r}_j)
$$

where $\hat{\mathbf{r}}_{ij} = (\mathbf{r}_i - \mathbf{r}_j)/r$. For $q \ge 2$ or $r = 0$, $\nabla_i W = \mathbf{0}$.

### 4.2 Density Summation & Weakly Compressible Tait EOS

Compute fluid density via summation over fluid neighbors $j$ and Akinci boundary neighbors $b$ (with boundary volume $\Psi_b = 1 / \sum_{k \in \text{boundary}} W_{bk}$):

$$
\rho_i = \sum_{j \in \text{fluid}} m_j W_{ij} + \rho_0 \sum_{b \in \text{boundary}} \Psi_b W_{ib}
$$

Compute pressure via the **Tait Equation of State** ($\gamma = 7$):

$$
p_i = \frac{\rho_0 c_0^2}{\gamma} \left[ \left(\frac{\rho_i}{\rho_0}\right)^\gamma - 1 \right] + p_{\text{bg}}
$$

where $\rho_0 = \rho_f$, $c_0 = 10 \max(U_t, \sqrt{g H_{\text{tank}}})$ keeps density variations below $\sim 1\%$, and a small positive background pressure $p_{\text{bg}}$ prevents tensile void formation behind the plate.

### 4.3 Momentum Equation, Physical Laminar Viscosity & Artificial Viscosity Definition

$$
\frac{d\mathbf{v}_i}{dt} = -\sum_{j \in \text{fluid}} m_j \left( \frac{p_i}{\rho_i^2} + \frac{p_j}{\rho_j^2} + \Pi_{ij} \right) \nabla_i W_{ij} + 2 \nu \sum_{j \in \text{fluid}} \frac{m_j}{\rho_j} \frac{\mathbf{v}_i - \mathbf{v}_j}{r_{ij}^2 + 0.01 h_{\text{sml}}^2} (\mathbf{r}_{ij} \cdot \nabla_i W_{ij}) + \mathbf{g} + \frac{\mathbf{F}_{i \leftarrow \text{boundary}}}{m_i}
$$

where $\nu = \mu / \rho_f$ is the physical kinematic viscosity.

* **Definition of Monaghan Artificial Viscosity $\Pi_{ij}$:**

$$
\Pi_{ij} = \begin{cases} \frac{-\alpha_{\text{art}} c_0 \mu_{ij}}{\bar{\rho}_{ij}} & \text{if } \mathbf{v}_{ij} \cdot \mathbf{r}_{ij} < 0 \\ 0 & \text{otherwise} \end{cases}, \qquad \mu_{ij} = \frac{h_{\text{sml}} (\mathbf{v}_i - \mathbf{v}_j) \cdot (\mathbf{r}_i - \mathbf{r}_j)}{r_{ij}^2 + 0.01 h_{\text{sml}}^2}
$$

* **Critical Rule on Artificial Viscosity:** Because $\alpha_{\text{art}} > 0$ introduces a numerical kinematic viscosity $\nu_{\text{art}} \approx \frac{1}{8} \alpha_{\text{art}} c_0 h_{\text{sml}}$ that swamps physical viscosity at $\text{Re} \ge 100$, **set $\alpha_{\text{art}} = 0.0$ by default** for all viscous validation tests and falling-plate runs (only enable $\alpha_{\text{art}} > 0$ if needed for the inviscid Dam-Break shock test). Always compute and report both the nominal Reynolds number $\text{Re} = U L / \nu$ and the effective Reynolds number $\text{Re}_{\text{eff}} = U L / (\nu + \nu_{\text{art}})$ in `SUMMARY_SPH.md`.

### 4.4 Elliptical Rigid Plate Geometry & Two-Way Coupling (Akinci et al. 2012)

To match the exact geometry of the Step 1 ODE added-mass model, the rigid plate is an **ellipse with semi-major axis $a = L/2$ and semi-minor axis $b = h/2$** (area $A = \pi a b$, mass $M_{\text{plate}} = \rho_s A$, moment of inertia $I_{\text{plate}} = \frac{1}{4} M_{\text{plate}} (a^2 + b^2)$).

* Discretize the interior and perimeter of the ellipse on a body-fitted lattice at spacing $\Delta x$, recording the exact particle count across the minor axis $N_h = h / \Delta x$.
* Each plate boundary particle $b$ has position $\mathbf{r}_b = \mathbf{R} + \mathbf{Q}(\theta)\mathbf{r}_b^{(0)}$ and velocity $\mathbf{v}_b = \mathbf{V} + \omega \hat{\mathbf{k}} \times (\mathbf{r}_b - \mathbf{R})$.
* **Fluid-Boundary Interaction Force $\mathbf{f}_{i \leftarrow b}$ (Correct Viscous Sign $\mathbf{v}_i - \mathbf{v}_b$):**

$$
\mathbf{f}_{i \leftarrow b} = -m_i \rho_0 \Psi_b \left( \frac{p_i}{\rho_i^2} + \frac{p_b}{\rho_0^2} + \Pi_{ib} \right) \nabla_i W_{ib} + 2 \nu m_i \Psi_b \frac{\mathbf{v}_i - \mathbf{v}_b}{r_{ib}^2 + 0.01 h_{\text{sml}}^2} (\mathbf{r}_{ib} \cdot \nabla_i W_{ib})
$$

Note the sign: since $(\mathbf{r}_{ib} \cdot \nabla_i W_{ib}) \le 0$, using $(\mathbf{v}_i - \mathbf{v}_b)$ provides positive viscous dissipation (damping velocity differences between fluid particle $i$ and boundary particle $b$).

* **Boundary Pressure Extrapolation (Breaking the $p_b \leftrightarrow \mathbf{a}_b$ Algebraic Loop):**
  In Adami et al. (2012), boundary pressure is extrapolated from surrounding fluid particles:

$$
p_b = \frac{\sum_i p_i W_{bi} + \rho_0 \sum_i (\mathbf{g} - \mathbf{a}_b) \cdot (\mathbf{r}_b - \mathbf{r}_i) W_{bi}}{\sum_i W_{bi}}
$$

Break the algebraic loop between $p_b$ and rigid-body acceleration $\mathbf{a}_b$ using **previous half-step acceleration $\mathbf{a}_b^{(n-1/2)}$ with 2-iteration Picard under-relaxation ($\omega_{\text{relax}} = 0.5$)** so light plates ($I^* = 0.05$, where fluid added mass $m_{22} \gg M_{\text{plate}}$) remain unconditionally stable. Document this in `sph_solver.cpp` and verify in Test 6.

* **Total Force & Torque on the Rigid Plate:**

$$
\mathbf{F}_{\text{fluid}} = \sum_{b \in \text{Plate}} \sum_{i \in \text{fluid}} (-\mathbf{f}_{i \leftarrow b}), \qquad \tau_{\text{fluid}} = \sum_{b \in \text{Plate}} (\mathbf{r}_b - \mathbf{R}) \times \sum_{i \in \text{fluid}} (-\mathbf{f}_{i \leftarrow b})
$$

### 4.5 Synchronous Kick-Drift-Kick (KDK) Time Integration

Advance **both** the fluid particles and the rigid plate synchronously within the same KDK step:

1. **Half-Kick ($t^n \to t^{n+1/2}$):** Advance fluid velocities $\mathbf{v}_i^{n+1/2}$ and rigid-body velocities $(\mathbf{V}^{n+1/2}, \omega^{n+1/2})$ by $\Delta t / 2$.
2. **Drift ($t^n \to t^{n+1}$):** Advance fluid positions $\mathbf{r}_i^{n+1}$, plate center $\mathbf{R}^{n+1}$, and orientation $\theta^{n+1}$ by $\Delta t$; update plate boundary particle positions and velocities.
3. **Force Evaluation at $t^{n+1}$:** Rebuild spatial hash, compute densities, pressures, extrapolated boundary pressures $p_b^{n+1}$, fluid accelerations, and plate accelerations.
4. **Second Half-Kick ($t^{n+1/2} \to t^{n+1}$):** Advance fluid and rigid-body velocities to $t^{n+1}$ by $\Delta t / 2$.

---

## 5. Nondimensional Numbers, Tank Sizing & Comparison Metrics

1. **Input vs. Measured Reynolds Numbers (Distinguish Clearly):**

* **Input (Froude-based) Reynolds Number:** $\text{Re}_{\text{in}} = \frac{\rho_f U_t L}{\mu}$, where $U_t = \sqrt{\left(\frac{\rho_s}{\rho_f} - 1\right) g h}$.
* **Measured (a posteriori) Reynolds Number:** $\text{Re}_{\text{meas}} = \frac{\rho_f U_{\text{mean}} L}{\mu}$, where $U_{\text{mean}}$ is the post-transient mean vertical descent speed.

2. **Tank Dimensions & Stopping Criterion:**

* Use **tank width $W_{\text{tank}} \ge 12 L$** ($\le 8.3\%$ broadside blockage; report $L / W_{\text{tank}}$ in captions).
* Compare **$\theta(t)$, angular velocity $\omega(t)$, post-transient mean vertical fall speed $U_{\text{mean}}$, dominant flutter frequency $f$ ($\text{St}$), and dynamical regime** (rather than $X(t)$ overlays).
* **Stopping Criterion:** Stop the run when the plate reaches **$2 L$ above the floor** or **$2 L$ from either side wall**.

---

## 6. Sebastian Lague-Style Visual Renderer in C++ (`software_renderer.cpp` & Optional GUI)

Implement a crisp, high-resolution 2D visual renderer in C++ (`software_renderer.hpp/.cpp`) that renders directly to an RGBA pixel buffer (and saves PNG frames via `stb_image_write.h` or displays live in a window if Raylib/GLFW is available):

* **Clean White Canvas (`#FFFFFF`):** Dark tank boundary walls (`#1E2430`) and subtle ruler tick marks in mm.
* **Anti-Aliased Fluid Particles:** Soft-edged circles colored by either **Velocity Magnitude $\vert{}\mathbf{v}\vert{}$** (Seb Lague blue-cyan-teal-orange ramp) or **Vorticity $\omega_z = \partial v_y/\partial x - \partial v_x/\partial y$** (diverging crimson-white-navy ramp showing shed Kármán/leading-edge vortices).
* **Elliptical Coin & Wake Ribbon:** Renders the solid elliptical coin (`#222831`) with its major-axis orientation arrow, center-of-mass trajectory trail, and top HUD bar displaying live `t`, `I*`, `Re_in`, `theta`, and explicit mode label (`"MODE A: 2D ODE Replay"` or `"MODE B: 2D C++ WCSPH-FSI Simulation"`).

---

## 7. Verification, Validation & Convergence Ladder (Tests 1–7)

All 7 validation tests must be executed via `sph_runner` and documented in `results_sph/SUMMARY_SPH.md`:

1. **Test 1 (Kernel Partition of Unity, Zero-Gradient & Linear-Field Gradient Matrix):**
   On a 2D interior particle lattice with volume $V_j = \Delta x^2$:

* Partition of unity: $\left\vert{}\sum_j V_j W_{ij} - 1\right\vert{} < 0.01$.
* Constant-field gradient: $\left\vert{}\sum_j V_j \nabla_i W_{ij}\right\vert{} < 10^{-6}$.
* **Linear-field gradient renormalization check:** Verify that $\mathbf{L}_i = -\sum_j V_j (\mathbf{r}_j - \mathbf{r}_i) \otimes \nabla_i W_{ij}$ satisfies $\Vert{}\mathbf{L}_i - \mathbf{I}\Vert{}_\infty < 0.02$.

2. **Test 2 (Hydrostatic Tank & Archimedes Buoyancy):**

* Part A: Still water column settles to hydrostatic pressure $p(y) = \rho_f g (H - y)$ within $5\%$ RMS error.
* Part B: Stationary submerged elliptical body experiences vertical fluid force matching $\rho_f g (\pi a b)$ within $5\%$.

3. **Test 3 (Viscous Operator Validation — Planar Poiseuille/Couette Flow & Taylor-Green Vortex Decay):**

* Part A (2D Planar Poiseuille or Couette Flow): Velocity profile $u(y, t)$ between parallel walls matches the analytical Navier–Stokes solution within $5\%$ L2 error.
* Part B (2D Taylor-Green Vortex Decay): On a periodic domain at $\text{Re} = 100$ (with $\alpha_{\text{art}} = 0$), verify kinetic energy decays as $E(t) = E_0 \exp(-4 \nu k^2 t)$ with fitted $\nu_{\text{meas}} / \nu \in [0.90, 1.10]$.

4. **Test 4 (2D Dam-Break Surge Front):**
   Compare dimensionless surge-front position $X_{\text{front}}(t)/W_0$ against the Martin & Moyce (1952) benchmark.
5. **Test 5 (Drag Past a Fixed Circular Cylinder at $\text{Re} = 20$ and $\text{Re} = 40$):**
   Compute steady drag coefficient $C_D = 2 F_D / (\rho_f U_0^2 D)$ in a channel of width $W \ge 12 D$ at $\text{Re} \in \{20, 40\}$ and compare against standard 2D Navier–Stokes literature benchmarks ($C_D(\text{Re}=20) \approx 2.0\text{--}2.2$, $C_D(\text{Re}=40) \approx 1.5\text{--}1.7$ with blockage noted).
6. **Test 6 (Low-$I^*$ Added-Mass Coupling Stability Test):**
   Run the lightest plate case ($I^* = 0.05$, where $m_{22} \gg M_{\text{plate}}$) for $2000$ timesteps and verify bounded synchronous KDK coupling without blow-up.
7. **Test 7 (Spatial Resolution Study at Constant $h_{\text{sml}} / \Delta x = 1.3$):**
   Run a fluttering drop across three spacings ($\Delta x \in \{L/12, L/16, L/20\}$) keeping $h_{\text{sml}}/\Delta x = 1.3$ constant. Report $N_h = h/\Delta x$, $U_{\text{mean}}$, $f$, and $\theta_{\max}$ honestly at each resolution.

---

## 8. Numerical Experiments (`scripts_sph/run_fsi_experiments.py`)

1. **Experiment 1 (Matched Cases Loaded Directly from Step 1 ODE Runs):**
   Load exact parameters `(rho_s, L, h, rho_f, mu, I*, Re_in, Re_meas)` from saved Step 1 ODE cases (`I* = 0.06` steady, `I* = 0.68` fluttering, `I* = 1.20` tumbling, `I* = 2.35` mixed) within $\text{Re}_{\text{meas}} \le 5000$. Compare $\theta(t)$, $\omega(t)$, $U_{\text{mean}}$, $f$, and regime between 2D SPH-FSI and 2D ODE.
2. **Experiment 2 (Explicit Viscosity / $\text{Re}_{\text{in}}$ Sweep at Fixed $I^* = 0.65$):**
   At fixed geometry and $I^* = 0.65$ ($\alpha_{\text{art}} = 0$), vary physical viscosity $\mu$ so $\text{Re}_{\text{in}} \in \{25, 100, 300, 800\}$. Report $\text{Re}_{\text{meas}}$, $\theta(t)$ amplitude, descent speed, and regime at each viscosity.
3. **Experiment 3 (Seb Lague-Style Particle & Vorticity Frame Renders):**
   Render high-resolution white-background PNG snapshots (`results_sph/frames/`) showing the fluid particles colored by velocity and vorticity $\omega_z(x, y)$ around the falling coin during fluttering and tumbling, plus Mode A ODE replay frames.

---

## 9. Task Order (Checklist)

* [ ] 1. Scaffold `cpp_sph/` C++newt20 project, `stb_image_write.h`, and build script.
* [ ] 2. Implement `kernels.cpp` (with exact $-35q/(4\pi h^3)$ gradient) and `spatial_hash.cpp` + **Test 1**.
* [ ] 3. Implement `sph_solver.cpp` ($\alpha_{\text{art}} = 0$ default) + **Tests 2A, 3A, 3B, 4** (Hydrostatic, Poiseuille/Couette, Taylor-Green, Dam-break).
* [ ] 4. Implement `rigid_ellipse.cpp`, Akinci coupling ($\mathbf{v}_i - \mathbf{v}_b$ viscous sign), and `integrator_kdk.hpp` + **Tests 2B, 5, 6** (Buoyancy, Cylinder Drag at Re=20 & 40, Low-$I^*$ stability).
* [ ] 5. Implement `software_renderer.cpp` (Seb Lague-style particle/vorticity renderer) and `ode_replay.hpp`.
* [ ] 6. Run **Test 7** (3-grid resolution study at fixed $h_{\text{sml}}/\Delta x$) and **Experiments 1, 2, 3**.
* [ ] 7. Generate `results_sph/SUMMARY_SPH.md` and update Slides 17–19 of the presentation with the C++ SPH results and wake snapshots.

```

<FollowUp>Would you like any adjustments to the CMake configuration or specific build scripts for compiling this with OpenMP on your setup?</FollowUp>

```
