<USER_REQUEST>
# Autumn Coin: real-time C++ visualiser for the 2D quasi-steady ODE model

A C++17 desktop application that integrates the 2D quasi-steady falling-plate ODE system
(Andersen, Pesavento & Wang, 2005) in real time and draws a coin falling through water inside a
glass tank. Live plots of the motion are drawn next to the tank while the coin falls.

This document is both the **README** and the **implementation spec**. It is written so that a
developer (or an AI coding agent) can build the whole project from it.

> Background: IYPT / TMF problem 12, *Autumn coin*: "The motion of a coin falling to the bottom of
> a tank filled with liquid can be remarkably similar to the fluttering and tumbling of a falling
> autumn leaf. Investigate how the motion of the coin depends on relevant parameters."

---

## 1. Goals

| # | Goal | Status in this spec |
|---|------|---------------------|
| G1 | Port the existing Python ODE model to C++ with identical physics | Section 4, Section 9 |
| G2 | Draw a coin falling in a **glass container** (2D side view, glass walls, water fill) | Section 5 |
| G3 | Plot the motion **live** in a side panel while it is being generated | Section 6 |
| G4 | Choose **different coin types / parameter sets** at run time (demo class: Pakistani rupee coins; washers come later) | Section 7 |
| G5 | Choose the **release angle** (0 to 360 degrees) and see steady / fluttering / tumbling / chaotic motion | Section 8 |
| G6 | Fix the visual errors of the current simulation | Section 10 |
| G7 | Verify the C++ results against the Python model and the physics tests | Section 9 |

### Non-goals (for this version)

- No 3D physics, no FSI / SPH. This is a 2D ODE model. 3D is a stated limitation and future work.
- No wall or bottom hydrodynamic interaction in the ODE. The tank is a visual boundary plus a
  stop condition (Section 4.6).
- No video tracking. Experimental data is only used for comparison and parameter presets.
- **Washers are a later feature.** The first version ships Pakistani rupee coins only (Section 7). The code keeps a `kind` field so washers can be added without a redesign.
- No free-surface physics. The water is assumed **perfectly still** and the model treats the coin as fully immersed from t = 0 (Section 4.5).

---

## 2. Background and experimental setup (from the reference repository)

Reference: <https://github.com/ondrej-cloud/autumn-coin> (Ondrej Novotny, team *Olomoucke srnky*,
Czech TMF problem 12).

**Their experiment, which the visualiser mirrors:**

- An electromagnet releases the coin at the water surface, so every drop starts from the same
  position and orientation.
- Water tank: **38 x 32 x 38 cm**. The coins fall through about **38 cm** of water.
- Two phones film the tank from perpendicular sides (front view gives X and depth Y, side view
  gives Z and depth Y).
- 143 tracked drops: six Czech coins and two washers with different hole sizes.
- Findings: motion is close to chaotic, so a single trajectory says little. Coins sit in the
  tumbling / chaotic part of the *(Re, I\*)* phase diagram. Washers (a hole lowers I\*) move toward
  fluttering. The large-hole washer is the most stable.

Reference coins from that repository (useful for validation presets):

| Coin | Mass | Diameter |
|------|-----:|---------:|
| 1 CZK | 3.6 g | 20.0 mm |
| 2 CZK | 3.7 g | 21.5 mm |
| 5 CZK | 4.8 g | 23.0 mm |
| 10 CZK | 7.62 g | 24.5 mm |
| 20 CZK | 8.42 g | 26.0 mm |
| 50 CZK | 9.7 g | 27.5 mm |

Coin **thickness is not given** in that repository. The 2D model needs it (Section 7), so thickness
must be measured or looked up for every coin you add.

Our project replaces the Czech coins with **Pakistani rupee coins** (a demo class in Section 7.3).
Pakistani washers are planned as a later feature.

**Key dimensionless numbers:**

```
I*  = rho_s * h / (rho_f * L)              dimensionless moment of inertia
Re  = rho_f * U * L / mu                   Reynolds number (U = mean descent speed)
U_t = sqrt((rho_s/rho_f - 1) * g * h)      Froude-type velocity scale
```

Coins have a roughly fixed density ratio rho_s/rho_f of about 7 to 8 and a thickness ratio h/L of
about 0.07 to 0.1, so real coins sit at I\* of roughly 0.5 to 1. That is why a **release-angle**
study plus a **coin-type** study is the natural way to see different regimes.

---

## 3. Existing Python model (the source of truth)

Repository: <https://github.com/ayaanthelegend/Autumn-coin> (`src/autumn/`).

The C++ code must reproduce this model exactly. If this document and the Python code disagree,
**the Python code wins** until the discrepancy is investigated.

### 3.1 State vector

```
state = [X, Y, theta, u, v, omega]
```

| Symbol | Meaning | Unit |
|--------|---------|------|
| X, Y | position in the lab frame, **Y points up**, gravity is -Y | m |
| theta | angle of the major axis (chord) from the +X axis | rad |
| u | body-frame velocity along the chord (major axis) | m/s |
| v | body-frame velocity along the thickness (minor axis) | m/s |
| omega | angular velocity, d(theta)/dt | rad/s |

### 3.2 Equations of motion (per unit depth)

Kinematics:

```
dX/dt     = u cos(theta) - v sin(theta)
dY/dt     = u sin(theta) + v cos(theta)
dtheta/dt = omega
```

Dynamics (Kirchhoff equations with quasi-steady forces):

```
(m + m11) du/dt     = (m + m22) v omega - rho_f * Gamma * v - F_u - (m - m_f) g sin(theta)
(m + m22) dv/dt     = -(m + m11) u omega + rho_f * Gamma * u - F_v - (m - m_f) g cos(theta)
(I + I_a) domega/dt = (m11 - m22) u v - tau
```

### 3.3 Hydrodynamic closures

```
|V|    = sqrt(u^2 + v^2)
alpha  = atan2(-v, u)                         angle of attack

Gamma  = -C_T * L * u v / |V|  +  0.5 * C_R * L^2 * omega        (m^2/s)
C_D    = C_D0 - C_D1 * cos(2 alpha)
F_u    = 0.5 * rho_f * L * C_D * |V| * u
F_v    = 0.5 * rho_f * L * C_D * |V| * v
tau    = 0.5 * C_tau * rho_f * L^4 * |omega| * omega  +  c_lin * omega
```

Regularisation: if `|V| < eps_V` (1e-7 m/s) the translational part of Gamma is set to 0.

### 3.4 Geometry, masses and added mass (elliptical cross-section)

```
a = L / 2,   b = h / 2                  semi-axes
A = pi a b                              area (per unit depth)
m   = rho_s * A                         solid mass
m_f = rho_f * A                         displaced fluid mass
I   = m (a^2 + b^2) / 4                 solid moment of inertia
m11 = rho_f pi b^2                      added mass along the chord
m22 = rho_f pi a^2                      added mass along the thickness
I_a = rho_f pi (a^2 - b^2)^2 / 8        added moment of inertia
```

### 3.5 Default coefficients (`config/base.yaml`)

| Name | Default | Note |
|------|--------:|------|
| rho_f | 998 kg/m^3 | water at 20 C |
| mu | 0.001 Pa s | |
| g | 9.81 m/s^2 | |
| C_T | 1.2 | translational circulation |
| C_R | pi | rotational circulation |
| C_D0 | 1.4 | drag |
| C_D1 | 1.0 | drag angle dependence |
| C_tau | 0.075 | rotational damping, strip-theory estimate |
| c_lin | 0.0 | optional linear damping |
| eps_V | 1e-7 m/s | |

> **Verify before citing.** The YAML comments say the coefficients and equation numbers are
> "verified" against Andersen et al. 2005b. Check each one against the paper yourself before
> putting equation numbers in a research paper.

### 3.6 Known issues to settle in the Python repo (they affect the C++ port)

1. `README.md` in the Python repo currently contains a pasted code-review message, not a README,
   and there is a second file named `Readme`. Replace both with a real README.
2. The lift term in `model.py` already multiplies by `rho_f` (`lift_u = rho_f * gamma * v`).
   Keep it that way in C++. Gamma is in m^2/s and the force is `rho_f * Gamma * V`.
3. Gamma uses `C_T` with `C_L = C_T sin(2 alpha)`, so peak `C_L = 1.2`. The ordering of terms is
   already consistent with the docstring; make sure the C++ unit test (Section 9) checks this.
4. `coin_sets.yaml` entries are labelled illustrative, not measured. Real coins need real data.

---

## 4. Simulation design

### 4.1 Language and dependencies

- C++17, built with CMake 3.20+.
- **raylib** for the window, tank drawing and input.
- **Dear ImGui** + **ImPlot** for the control panel and the live plots.
- **rlImGui** to connect ImGui to raylib.
- **yaml-cpp** to read the same `base.yaml` and coin files as the Python code.
- **Catch2** or **doctest** for unit tests.
- Everything is pulled in with CMake `FetchContent`, so a fresh clone builds with one command.

### 4.2 Integrator

- Default: **fixed-step classical RK4** with a small internal step (`dt_phys = 1e-4 s`), run
  several sub-steps per rendered frame. Deterministic and simple.
- Optional: **Dormand-Prince RK45 (adaptive)** to compare against the Python `DOP853` run.
- The right-hand side is a pure function `rhs(t, state) -> dstate` with no hidden state, exactly
  like `AutumnModel.rhs` in Python.
- Simulation time and wall-clock time are decoupled: a **time scale** slider (0.1x to 5x, plus
  pause and single-step) controls how fast the coin falls on screen.

### 4.3 Frame loop

```
while window open:
    handle input and UI
    if running:
        sim_time_budget += frame_dt * time_scale
        while sim_time_budget >= dt_phys:
            rk4_step(state, dt_phys)
            append sample to ring buffers every dt_sample
            check termination (bottom, wall, t_max)
            sim_time_budget -= dt_phys
    draw tank, water, coin, trail
    draw ImGui panels and ImPlot plots from the ring buffers
```

Cap the number of sub-steps per frame (for example 5000) so a slow frame can never freeze the UI.

### 4.4 Coordinate and unit conventions

This is the most likely source of visual bugs, so it is fixed here:

- Physics works in **metres and radians**, Y up, theta measured counter-clockwise from +X.
- **World origin: the water surface at the horizontal centre of the tank.** So the release point is
  `(X, Y) = (0, 0)`, the floor is at `Y = -H_water` and the walls are at `X = +-W/2`.
- Screen space has **Y down**. All conversion happens in **one place**, `world_to_screen()`
  (`tank_origin` is the screen position of the inner top-left corner of the tank, which lies on the
  water surface):

```
screen.x = tank_origin.x + (X + W/2) * px_per_m
screen.y = tank_origin.y + (-Y)      * px_per_m
```

- Coin drawing rotation: raylib rotates clockwise for positive angles on screen, so draw with
  `-theta` converted to degrees, or build the corner points manually from `(cos theta, sin theta)`.
  Pick one approach and test it with the orientation test in Section 9.
- Never mix body-frame and lab-frame values in plots. Label every axis with symbol and unit.

### 4.5 Initial conditions

Release follows the experiment's electromagnet drop, but **at the water surface with the coin half
submerged**, so the coin starts with its centre exactly on the surface and the angle of attack is
set by the release angle alone. The water is assumed **still** (no waves, no flow, no surface motion).

```
X0     = 0   (middle of the tank, horizontally)
Y0     = 0   (coin centre on the free surface: half of the coin below the water line)
theta0 = chosen by the user, 0..360 degrees
u0 = v0 = omega0 = 0
```

`release_offset` (default `0`, metres, positive = coin centre above the surface, negative = below)
is available in the config for later experiments.

**Honest limitation of the half-submerged start.** The ODE assumes the whole plate is immersed in
fluid. At t = 0 half of the coin is in air, so the first fraction of a second (partial buoyancy,
partial added mass, surface tension, splash) is **not modelled**. The model behaves as if the coin
were fully immersed from the start, with buoyancy computed for the full volume. Treat the first
few coin diameters of the fall as a transient, and say so in the paper. The classifier already
discards the first 20% of the fall as transient (Section 8.1).

**Important physics note on exact symmetry.** With zero initial velocities, some angles are
perfectly symmetric:

- `theta0 = 0` or `180` deg: the coin is horizontal. `g_u = 0`, so `u` stays exactly 0 and the coin
  falls perfectly flat forever in the model.
- `theta0 = 90` or `270` deg: the coin is vertical (edge-on) and falls edge-first for the same
  reason.

Real coins never start exactly like that. The app therefore has an optional **release
perturbation** (default `1e-6 rad` on theta, plus an optional small initial `u`) so these angles
can still show instability. Display the perturbation value in the UI so results stay honest.

**Expected symmetries (turn them into unit tests, do not assume):**

- `theta0` and `theta0 + 180` deg give identical lab trajectories (a flat plate looks the same
  after a half turn).
- `theta0` and `180 - theta0` deg give mirrored trajectories (`X -> -X`).

So a sweep over 0 to 360 deg contains only about a quarter of the information; the UI should say so.

### 4.6 Tank, termination and wall handling

Default tank (matches the experiment), side view:

| Parameter | Default |
|-----------|--------:|
| Inner width | 38 cm |
| Water height | 38 cm |
| Glass thickness (drawn only) | 6 mm |
| Water level (top) | 38 cm above the floor (`Y = 0`) |

The coin is released from the centre of the surface, so the nearest wall is 19 cm away. Stop conditions:

1. **Bottom:** the lowest point of the coin outline reaches the floor (`Y_low <= -H_water`). Mark landing, freeze, report.
2. **Side wall:** the coin outline touches a wall (`|X| + half-extent >= W/2`, measured on the rotated outline). Freeze, mark "hit wall", and show it in the
   results table. (The ODE has no wall physics; the experiment also saw coins reach the walls.)
3. **Timeout:** `t_max` reached.

Keep these three outcomes separate in the results panel.

---

## 5. Visuals: the glass container

Side view of a tank:

- **Glass:** semi-transparent pale blue-green walls and floor with a thin lighter edge line and a
  subtle highlight strip on the left of each wall. The walls have visible thickness.
- **Water:** a rectangle filling the inside up to the water level, light blue with slight vertical
  gradient (lighter at the surface). A thin lighter line marks the free surface.
- **Coin:** drawn to scale as a rectangle (chord L by thickness h). At release it straddles the water line: draw the part above the surface untinted and the part below with the water tint (clip with raylib scissor mode, or draw the water overlay with alpha on top). Thin coins can be a few pixels
  thick, so offer an **exaggerate thickness** toggle (visual only) and a **zoom / follow camera**.
- **Trail:** the centre-of-mass path as a fading polyline, plus optional faint **ghost outlines**
  of the coin every N milliseconds (a stroboscopic view, like the experiment's overlays).
- **Orientation marker:** a small tick on one face so tumbling direction is visible.
- **Scale bar and ruler:** a centimetre ruler on the left glass wall so sizes are readable.
- **Presentation theme:** white window background and **dark (near-black) text and plot labels**,
  independent of any system dark mode.
- At 700 px of tank height, 38 cm gives about 18 px per cm, so a 2 cm coin is about 37 px wide.
  Use a configurable `px_per_m` and let the window resize cleanly.

Layout:

```
+--------------------------------------+---------------------------+
|                                      |  Controls                 |
|            Glass tank                |  (coin, angle, run)       |
|            (side view)               +---------------------------+
|                                      |  Live plots (ImPlot)      |
|                                      |   - X-Y trajectory        |
|                                      |   - theta(t), omega(t)    |
|                                      |   - speed / depth         |
|                                      |   - phase: theta vs omega |
+--------------------------------------+---------------------------+
|  Status bar: t, I*, Re, regime, outcome                           |
+-------------------------------------------------------------------+
```

---

## 6. Live graphs

Plots are driven by **ring buffers** (fixed-size arrays, newest data overwrites oldest) filled at
`dt_sample` (default 1 ms of simulated time). ImPlot reads them directly, so the cost per frame
does not grow with run length.

| Plot | X axis | Y axis | Why |
|------|--------|--------|-----|
| Trajectory | X [cm] | Y [cm] | shows the glide, flip and drift shape |
| Angle | t [s] | theta [deg] (unwrapped) | shows flutter (oscillation) vs tumble (monotonic growth) |
| Angular velocity | t [s] | omega [rad/s] | |
| Velocities | t [s] | vertical speed -dY/dt, horizontal dX/dt [cm/s] | terminal velocity |
| Depth | t [s] | fallen depth [cm] | |
| Phase portrait | theta mod 2 pi [rad] | omega [rad/s] | closed loop = flutter, drifting band = tumble |
| Angle of attack | t [s] | alpha [deg] | |
| Energy (optional) | t [s] | T, V, dissipated [mJ/m] | energy budget like the experiment's |

Rules:

- The plotted line grows as the coin falls (auto-scrolling x range, with a pause-and-zoom mode).
- The trajectory plot keeps equal axis scaling so shapes are not distorted.
- Every plot has the symbol and unit in the axis label, black text on white.
- A **compare** toggle keeps previous runs as thin grey lines behind the current one.
- Export buttons: save current run as `run_<coin>_<theta0>.csv` and the plot area as a PNG.

---

## 7. Coin types and parameter sets

### 7.1 What defines a coin in this model

The ODE is 2D (per unit depth), so a coin is reduced to an elliptical cross-section:

| Parameter | Symbol | From |
|-----------|--------|------|
| Diameter | L | measured |
| Thickness | h | measured (not given in the reference repo) |
| Solid density | rho_s | `mass / (pi (L/2)^2 h)` for a solid disc |

**Washers are a later feature.** When they are added, the Python repo's approach is the starting
point: an **effective density** `rho_eff = mass / (pi (L/2)^2 h)` that includes the hole (state this
approximation in the paper). Until then the loader ignores any entry with `kind: washer`.

### 7.2 Built-in presets

Keep the five illustrative presets already in `config/coin_sets.yaml` (reference_card, steady_card,
heavy_coin, light_coin, washer_proxy). They are labelled **illustrative** in the UI. The washer proxy
stays as an illustrative plate, not as the washer feature.

### 7.3 Demo class: Pakistani rupee coins

Starting values from public sources (State Bank of Pakistan press release and Numista). These are
**demo values, not measurements**. Replace them with your own caliper and scale readings before
using any result in the paper. Coin masses also vary between individual coins.

| id | Coin | Mass | Diameter | Thickness | rho_s (derived) | I* (derived) | U_t scale | Source quality |
|----|------|-----:|---------:|----------:|----------------:|-------------:|----------:|----------------|
| `pk_rs10` | Rs 10 (2015 to 2022, brass) | 5.5 g | 25.5 mm | 1.5 mm | about 7180 kg/m^3 | about 0.42 | about 0.30 m/s | Numista; weight varies 5.0 to 6.2 g |
| `pk_rs5_2002` | Rs 5 (2002, cupronickel, older type) | 6.5 g | 24 mm | 2.1 mm | about 6840 kg/m^3 | about 0.60 | about 0.35 m/s | one dealer listing; verify |
| `pk_rs5_2015` | Rs 5 (2015, brass, newer small type) | 3 g | 18.5 mm | **not found, measure** | n/a | n/a | n/a | SBP press release gives mass and diameter only |

Notes:

- `rho_s` is the **effective** density `mass / (pi (L/2)^2 h)` of a flat disc. Real coins have a raised
  rim and relief, so the true thickness is not uniform; this is an approximation for the 2D model.
- `I*` and `U_t` are computed by the app from the three inputs, not typed in. The values above are
  only a check for your implementation.
- `pk_rs5_2015` stays **disabled** until a thickness is entered. Do not guess it.
- You can add Rs 1 and Rs 2 coins the same way once measured.

`config/coins.yaml`:

```yaml
coins:
  - id: pk_rs10
    label: "Rs 10 coin"
    kind: coin               # coin | washer (washers are loaded in a later version)
    mass_g: 5.5
    diameter_mm: 25.5
    thickness_mm: 1.5
    material: "brass"
    source: "demo (Numista), replace with measurement"
    enabled: true
  - id: pk_rs5_2002
    label: "Rs 5 coin (2002, cupronickel)"
    kind: coin
    mass_g: 6.5
    diameter_mm: 24.0
    thickness_mm: 2.1
    material: "cupronickel"
    source: "demo (dealer listing), replace with measurement"
    enabled: true
  - id: pk_rs5_2015
    label: "Rs 5 coin (2015, small)"
    kind: coin
    mass_g: 3.0
    diameter_mm: 18.5
    thickness_mm: null       # measure it, then set enabled: true
    material: "brass"
    source: "SBP press release (mass, diameter)"
    enabled: false
```

The loader computes `rho_s`, `I*` and `U_t`, shows them in the UI, and skips any entry that has a
missing field with a clear message.

### 7.4 Parameters editable at run time

- Per coin: L, h, rho_s (directly or through mass).
- Fluid: rho_f, mu (a water temperature preset: 10, 20, 30 C).
- Coefficients: C_T, C_R, C_D0, C_D1, C_tau, c_lin. A **Reset to defaults** button restores
  `base.yaml` values. Changing a coefficient shows a banner "non-default coefficients".
- Tank: width, water height.

---

## 8. Release angle and regime study

The only release control is the **initial angle theta0, 0 to 360 degrees** (initial velocities are
zero). Controls:

- **Single run:** angle slider and numeric box, plus quick buttons for 0, 30, 45, 60, 90 deg.
- **Range / sweep mode:** choose `theta_min`, `theta_max`, `step` (for example 0 to 360 in 15 deg
  steps). The app runs each angle, overlays the trajectories in different colours (headless
  background integration is fast; draw them as ghost coins) and fills a results table.
- **Seed and perturbation:** release perturbation value (Section 4.5) and an optional random seed
  for small noise if you want repeatable "ensembles" like the experiment's 15 to 20 drops per coin.

### 8.1 Regime classifier (reuse the Python thresholds)

Classify after discarding the first 20% of the fall (and at least 1 s) as transient, using
`regime_classifier` in `base.yaml`:

| Regime | Rule (post-transient) |
|--------|-----------------------|
| Steady descent | std(theta) < 1 deg **and** peak-to-peak(theta) < 2 deg |
| Fluttering | theta oscillates, no net full rotations |
| Tumbling | at least 2 net full rotations, backward excursion at most 180 deg |
| Chaotic / mixed | rotation with reversals of at least 90 deg |

The current regime is shown live in the status bar and logged to the table.

### 8.2 What to expect (to be tested, not assumed)

The regime depends on both **I\*** and the **release angle**, so the same coin can show different
motions for different theta0. Use the phase-diagram idea from the reference repository: plot a
point for every run in the (I\*, regime) plane and a heat-map of regime versus (theta0, coin).
Report honestly if a coin never leaves steady descent: that is a model result worth discussing,
and an early sign to re-check coefficients rather than to tune them until tumbling appears.

---

## 9. Verification and tests

Every item below is an automated test (Catch2 / doctest) and must pass in CI.

1. **Python parity.** Export reference trajectories from the Python model (`scripts/run_single.py`)
   for each preset and several angles to `tests/reference/*.csv`. The C++ result must match within a
   stated tolerance (for example 1e-6 relative on positions at matching times, with RK4 `dt_phys`
   small enough). Document the tolerance.
2. **Dimensional check.** Every term in each of the three dynamics equations has the same unit.
3. **Lift coefficient.** `C_L(alpha) = 2 Gamma / (|V| L)` peaks at `C_T = 1.2` near `alpha = 45 deg`.
4. **Energy.** With drag, torque and circulation switched off the mechanical energy is conserved to
   integrator precision. (Circulation does no work, so this test cannot detect missing factors.)
5. **Terminal velocity.** Broadside fall speed matches the analytic estimate in
   `U_terminal_broadside_est`.
6. **Symmetry.** `theta0` vs `theta0 + 180` identical; `theta0` vs `180 - theta0` mirrored.
7. **Orientation test.** Render a coin at `theta = 0, 45, 90` and compare the drawn corner points to
   the expected rotation (catches Y-flip and rotation-direction bugs).
8. **Integrator convergence.** Halving `dt_phys` changes the result by less than the tolerance.
9. **No-NaN guard.** Fuzz random parameters; the state must stay finite or the run stops with an
   error message.

---

## 10. Fixing the visual errors (checklist)

The current visual simulation has many errors. Before adding features, make sure each of these is
handled by design:

- [ ] Single `world_to_screen()` function; no hand-written conversions elsewhere
- [ ] Y-axis flip handled once, rotation direction verified by the orientation test
- [ ] Coin drawn at true scale with an optional visual-only thickness exaggeration
- [ ] Angle unwrapped for plots (no jumps at +-180 deg) and wrapped only for the phase portrait
- [ ] Plots use ring buffers; no per-frame reallocation; no growing vectors
- [ ] Simulation time is decoupled from frame rate; pausing never loses state
- [ ] Trail and ghost outlines are bounded in length
- [ ] Wall and floor contact detected on the **rotated** outline, not just the centre point
- [ ] High-DPI scaling and window resizing keep the tank proportions
- [ ] Units shown on every axis and every number in the UI
- [ ] White background, dark text everywhere, including ImPlot tick labels and the legend

---

## 11. Project layout

```
autumn-coin-cpp/
  CMakeLists.txt
  README.md
  config/
    base.yaml            # same schema as the Python repo
    coin_sets.yaml       # presets (illustrative)
    coins.yaml           # Pakistani rupee coins (washers added later)
  src/
    main.cpp             # window, frame loop
    model.hpp/.cpp       # state, params, rhs(), added mass, forces
    integrator.hpp/.cpp  # RK4, optional RK45
    config.hpp/.cpp      # yaml loading, derived quantities (I*, Re, U_t)
    regime.hpp/.cpp      # classifier
    tank.hpp/.cpp        # tank geometry, contact tests
    render.hpp/.cpp      # world_to_screen, glass, water, coin, trail
    ui.hpp/.cpp          # ImGui panels
    plots.hpp/.cpp       # ImPlot plots, ring buffers
    sweep.hpp/.cpp       # angle sweep, results table, CSV export
  tests/
    reference/           # CSVs exported from the Python model
    test_*.cpp
  docs/
    screenshots/
```

---

## 12. Build and run

```bash
# Linux / macOS
git clone <this-repo> autumn-coin-cpp
cd autumn-coin-cpp
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/autumn_viz

# Windows (Visual Studio 2022)
cmake -S . -B build -G "Visual Studio 17 2022"
cmake --build build --config Release
build\Release\autumn_viz.exe

# Tests
ctest --test-dir build --output-on-failure
```

Command-line options (all optional):

```
--coin <id>          start with a preset
--theta <deg>        initial angle
--sweep <min:max:step>
--timescale <x>
--config <dir>
--headless --out <file.csv>    run without a window and write the trajectory
```

---

## 13. Milestones

| M | Deliverable | Done when |
|---|-------------|-----------|
| M1 | `model`, `integrator`, `config`, tests 1 to 5, 8, 9 | C++ matches Python for all presets |
| M2 | Window, glass tank, water, coin, trail | orientation test passes; looks right at several sizes |
| M3 | Live ImPlot panel with ring buffers | plots grow in real time without lag |
| M4 | Coin selection, editable parameters, `coins.yaml` loader | the Pakistani demo coins load and show rho_s, I\*, U_t |
| M5 | Release angle control, regime classifier, status bar | all four regimes reachable and labelled |
| M6 | Angle sweep, ghost overlays, results table, CSV/PNG export | table matches headless runs |
| M7 | Symmetry tests, polish, screenshots, README update | all tests green; figures usable in the paper |
| M8 (later) | Washer feature | washers load from `coins.yaml` with effective density and appear in the sweep and regime map |

---

## 14. Using the results in the research paper

- Report the model, coefficients and their sources, and mark which were verified against the paper.
- Show regime maps over (I\*, theta0) and trajectory ensembles next to the ondrej-cloud style
  figures for the Pakistani coins (and washers once that feature exists).
- State the limitations clearly: 2D only, quasi-steady forces, no wall effects, coins approximated by an
  elliptical cross-section, still water, and a half-submerged release that the model treats as fully
  immersed (so the first moments of the fall are not physical).
- Compare qualitatively with the experiment (landing scatter, regime of each coin) and be explicit
  about which agreement is a model prediction and which is a fit.

---

## 15. Decisions made and open questions

**Decided:**

- Release at the horizontal centre of the tank, at the surface, coin half submerged, water still.
- Initial velocities are zero; the release angle is the only release control (0 to 360 degrees).
- Graphics stack: raylib + ImGui/ImPlot. Container: 2D side view with glass walls and water fill.
- Pakistani rupee coins are the demo class; washers come later.

**Still open:**

1. **Thickness data** for each Pakistani coin (calipers), and a few mass readings per denomination.
2. **Perturbation size** for the exactly symmetric angles (0, 90, 180, 270 deg).
3. **Coefficient verification** against Andersen et al. 2005 before any equation numbers are cited.
4. **Surface transient.** Whether to ignore the first moments of the fall (current plan) or add a
   simple partial-immersion correction later.

---

## 16. References

- A. Andersen, U. Pesavento, Z. J. Wang, *Unsteady aerodynamics of fluttering and tumbling plates*,
  J. Fluid Mech. **541**, 65-90 (2005).
- A. Andersen, U. Pesavento, Z. J. Wang, *Analysis of transitions between fluttering, tumbling and
  steady descent of falling cards*, J. Fluid Mech. **541**, 91-104 (2005).
- U. Pesavento, *Unsteady aerodynamics of falling plates*, PhD thesis, Cornell University (2006).
- H. Lamb, *Hydrodynamics*, 6th ed., Cambridge University Press (1932), Section 71.
- Experiment and tracking: <https://github.com/ondrej-cloud/autumn-coin>
- Python ODE model: <https://github.com/ayaanthelegend/Autumn-coin>

---

## Appendix A: C++ implementation notes

These are suggested designs, not requirements. They show the logic that keeps the physics, the
drawing and the plots independent of each other.

### A.1 Core library and app are separate

```
autumn_core   (static lib)  model, integrator, config, regime, tank contact, sweep, CSV
autumn_viz    (executable)  raylib + ImGui/ImPlot, links autumn_core
autumn_tests  (executable)  Catch2/doctest, links autumn_core only
```

`autumn_core` must not include raylib or ImGui. That makes headless runs, sweeps and Python-parity
tests trivial, and it stops rendering code from leaking into the physics.

### A.2 Model (mirrors `model.py` line by line)

```cpp
#include <array>
#include <cmath>

using State = std::array<double, 6>;           // X, Y, theta, u, v, omega

struct Fluid  { double rho_f = 998.0, mu = 1e-3, g = 9.81; };
struct Coeffs { double C_T = 1.2, C_R = M_PI, C_D0 = 1.4, C_D1 = 1.0,
                       C_tau = 0.075, c_lin = 0.0, eps_V = 1e-7; };

struct Plate {                                  // per unit depth, elliptical cross-section
    double rho_s, L, h;
    double a()    const { return 0.5 * L; }
    double b()    const { return 0.5 * h; }
    double mass() const { return rho_s * M_PI * a() * b(); }
    double Isolid() const { return mass() * (a()*a() + b()*b()) / 4.0; }
};

class Model {
public:
    Model(Plate p, Fluid f, Coeffs k) : p_(p), f_(f), k_(k) {
        m_  = p.mass();
        mf_ = f.rho_f * M_PI * p.a() * p.b();
        m11_ = f.rho_f * M_PI * p.b() * p.b();
        m22_ = f.rho_f * M_PI * p.a() * p.a();
        Ia_  = f.rho_f * M_PI * std::pow(p.a()*p.a() - p.b()*p.b(), 2) / 8.0;
        Mu_ = m_ + m11_;  Mv_ = m_ + m22_;  It_ = p.Isolid() + Ia_;
    }

    State rhs(double /*t*/, const State& s) const {
        const double th = s[2], u = s[3], v = s[4], w = s[5];
        const double c = std::cos(th), sn = std::sin(th);
        const double V = std::hypot(u, v);
        const double alpha = std::atan2(-v, u);

        const double gamma = (V < k_.eps_V ? 0.0 : -k_.C_T * p_.L * u * v / V)
                           + 0.5 * k_.C_R * p_.L * p_.L * w;          // m^2/s
        const double cd  = k_.C_D0 - k_.C_D1 * std::cos(2.0 * alpha);
        const double Fu  = 0.5 * f_.rho_f * p_.L * cd * V * u;
        const double Fv  = 0.5 * f_.rho_f * p_.L * cd * V * v;
        const double tau = 0.5 * k_.C_tau * f_.rho_f * std::pow(p_.L, 4) * std::fabs(w) * w
                         + k_.c_lin * w;
        const double W   = (m_ - mf_) * f_.g;                          // buoyant weight

        const double du = (Mv_ * v * w - f_.rho_f * gamma * v - Fu - W * sn) / Mu_;
        const double dv = (-Mu_ * u * w + f_.rho_f * gamma * u - Fv - W * c) / Mv_;
        const double dw = ((m11_ - m22_) * u * v - tau) / It_;

        return { u * c - v * sn, u * sn + v * c, w, du, dv, dw };
    }

private:
    Plate p_; Fluid f_; Coeffs k_;
    double m_, mf_, m11_, m22_, Ia_, Mu_, Mv_, It_;
};
```

Notes: `theta` is integrated as a plain number, so it is already **unwrapped**. Only wrap it
(`std::fmod`) for the phase portrait. Keep the `rho_f` factor on the circulation force.

### A.3 RK4 step

```cpp
template <class F>
State rk4(const F& rhs, double t, const State& y, double dt) {
    auto add = [](const State& a, const State& b, double s) {
        State r; for (int i = 0; i < 6; ++i) r[i] = a[i] + s * b[i]; return r; };
    State k1 = rhs(t, y);
    State k2 = rhs(t + 0.5*dt, add(y, k1, 0.5*dt));
    State k3 = rhs(t + 0.5*dt, add(y, k2, 0.5*dt));
    State k4 = rhs(t + dt,     add(y, k3, dt));
    State r;
    for (int i = 0; i < 6; ++i) r[i] = y[i] + dt/6.0 * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i]);
    return r;
}
```

### A.4 One simulation object that the UI and sweeps both use

```cpp
struct Sample { double t, X, Y, theta, omega, u, v, alpha; };

class Run {
public:
    Run(const Model& m, const Tank& tank, double theta0_deg, double perturb_rad);
    void advance(double sim_seconds);        // sub-steps at dt_phys, stops at termination
    bool finished() const;
    Outcome outcome() const;                 // Bottom | Wall | Timeout | Running
    const std::vector<Sample>& samples() const;   // appended every dt_sample
};
```

The UI calls `advance(frame_dt * time_scale)` once per frame (with a cap on sub-steps). A sweep
creates many `Run` objects and calls `advance(t_max)` on each, in parallel with `std::async`,
because runs share no state.

Initial state: `{0, release_offset, theta0 + perturb, 0, 0, 0}`.

### A.5 Contact test on the rotated outline

```cpp
// Four corners of the coin rectangle (chord L, thickness h), lab frame
std::array<Vec2, 4> corners(const State& s, double L, double h) {
    const double c = std::cos(s[2]), sn = std::sin(s[2]);
    const double lx[4] = {-L/2,  L/2, L/2, -L/2};
    const double ly[4] = {-h/2, -h/2, h/2,  h/2};
    std::array<Vec2, 4> p;
    for (int i = 0; i < 4; ++i)
        p[i] = { s[0] + lx[i]*c - ly[i]*sn,  s[1] + lx[i]*sn + ly[i]*c };
    return p;
}
```

Bottom contact: `min(p[i].y) <= -H_water`. Wall contact: `max(abs(p[i].x)) >= W/2`.

### A.6 Drawing the coin and the glass (raylib)

- Convert the four corners with `world_to_screen()` and draw the coin as two triangles. Raylib wants
  a consistent winding order; the Y flip reverses it, so verify with the orientation test and swap
  vertex order if the coin disappears.
- Water line: draw the water rectangle first, then the coin. To show the half-submerged start, call
  `BeginScissorMode` over the water region and draw the coin again with the water tint on top, or
  draw a semi-transparent water rectangle after the coin.
- Glass: draw filled rectangles for the walls and floor with alpha about 60, a lighter outline, and a
  narrow white highlight strip. Draw them **after** the coin so the glass sits in front.
- Use `DrawLineStrip`/`DrawLineEx` for the fading trail and cap its length (for example 4000 points).

### A.7 Ring buffer for live plots

```cpp
struct ScrollBuf {
    int max = 20000, off = 0;
    std::vector<float> x, y;
    void add(float xv, float yv) {
        if ((int)x.size() < max) { x.push_back(xv); y.push_back(yv); }
        else { x[off] = xv; y[off] = yv; off = (off + 1) % max; }
    }
};
// ImPlot::PlotLine("theta", buf.x.data(), buf.y.data(), (int)buf.x.size(), 0, buf.off, sizeof(float));
```

Check the `PlotLine` signature of the ImPlot version you fetch (the flags argument was added in
newer releases).

### A.8 Regime classifier sketch

Port `classify_regime` from the Python `dimensionless.py` **verbatim** and test against it. The idea:

```
drop first 20% of samples (at least 1 s)
theta_std, theta_ptp  <- post-transient statistics of theta (deg)
if theta_std < 1 and theta_ptp < 2:                    steady
net = |theta_end - theta_start| / (2 pi)               net full rotations
if net >= 2:
    back = largest excursion against the net rotation direction (deg)
    if back <= 180:                                    tumbling
    else if back >= 90:                                chaotic / mixed
else:                                                  fluttering
```

Treat this as a sketch only; the thresholds and edge cases live in the Python code.

### A.9 Things that are easy to get wrong

- Mixing degrees and radians between the UI (degrees) and the model (radians).
- Plotting `Y` upward but drawing it downward on screen without the single conversion function.
- Letting the plot vectors grow forever instead of using the ring buffer.
- Using the coin centre for wall contact instead of the rotated outline.
- Starting at exactly `theta0 = 0, 90, 180, 270` with no perturbation and expecting instability.
- Reporting a "tumbling" result without checking the post-transient window used by the classifier.
- Comparing C++ to Python with different integrators and tolerances and blaming the physics.
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-22T11:15:02+05:00.
</ADDITIONAL_METADATA>