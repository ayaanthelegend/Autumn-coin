# Figure and Data Audit (commit 01bbd85)

Scope: every PNG in `results/`, `results_sph/` and `docs/screenshots/`, plus the scripts that draw them.
New figures: `scripts/make_paper_figures.py` writes `results/paper_figures/F01 ... F13` (PNG 300 dpi + PDF).

## 1. State of the repository

| Check | Result |
|-------|--------|
| `pytest` | 23 passed |
| `node --test tests_js/test_core.mjs` | passed |
| `scripts/check_slide_numbers.py` | 12 / 12 checks passed |
| C++ core tests (earlier commit, headless) | 10 cases passed |

## 2. Integrity problems (fix before any of this goes into the paper)

1. **Two figures are drawn from hand-written formulas, not from data.**
   `tools/generate_presentation_figures.py` writes `results/comparison/sph_vs_ode_overlay.png`
   and `results/drops/vorticity_wake_snapshot.png`.
   - The "orientation across inertia regimes" curves are `np.exp`, `np.sin` and a line commented
     "synthetic chaotic trace".
   - The "explicit viscosity sweep, SPH mu-variation" curves (Re 25, 100, 300, 800) are invented
     sinusoids with chosen decay rates.
   - The "Mode A ODE replay" panel is a sine path with drawn ellipses; the "WCSPH vorticity field"
     is six hand-placed Gaussian vortices.
   - Do not use these figures. The real SPH viscosity data (0.35 s runs) is in
     `results_sph/drops/sph_visc_Re*.csv` and is plotted in new figure F12.
2. **`results_sph/SUMMARY_SPH.md` Tests 1 to 6 are hard-coded strings** (`scripts_sph/make_sph_summary.py`,
   lines about 50 to 56), not read from the CSVs.
   - Test 5 (cylinder drag): the summary says `C_D(20) = 2.08, C_D(40) = 1.58, PASS`.
     `test5_cylinder_drag.csv` says **10.96 and 8.11** (about 5 times the 2.0-2.2 and 1.5-1.7 benchmarks).
     The C++ test passes when `C_D(20) > C_D(40)`, i.e. on ordering only.
   - Test 4 (dam break): the test passes if the final front is between 1.8 and 3.2 W0, so almost any
     advancing front passes. The summary text "X/W0 = 3.00 at tau about 2.0" is hard-coded.
   - Test 7 is correctly reported as FAIL (U_mean 0.512, 0.785, 0.637 m/s on the three grids).
3. **`scripts/make_literature_validation.py`**
   - The "Field et al. (1997) flutter / chaotic / tumbling zones" in panel (a) are made-up analytic curves
     (`0.012 + 0.15 exp(-Re/2000)` and similar). They are not taken from the paper.
   - Card values (U/U_t = 0.54 and 0.62, I\* = 1.14 and 1.38, St 0.18 to 0.22) are hard-coded
     and unchecked against Andersen et al. 2005b or Belmonte et al. 1998.
   - The Field et al. citation is wrong in this script and in `scripts/make_summary.py`
     ("O'Reilly, PRL 78(10) 1896"). The paper I know under that title is
     Field, Klaus, Moore and Nori, *Nature* 388, 252-254 (1997), which is what slide 22 uses. Please confirm.
4. **Regime-map "tumbling" and monotonic ordering.** The regime strip (F01) still shows fluttering at
   I\* of 3.0 to 3.5, after mixed at 1.5 to 2.75. Any sentence calling the ordering "monotonic" must be
   reworded or the I\* >= 3 cells re-run at a larger perturbation (1e-2) to see whether the label is robust.

## 3. Visual problems found, and what replaced them

| Old figure | Problem | New figure |
|------------|---------|------------|
| `regime_vs_istar.png` | legend hid the bottom row; "undetermined" missing from legend; invented "Andersen band" with midpoint | F01: three panels (full range, zoom 0.95-1.9, I\*_c versus mu_1), legend below, cited card values labelled "as cited" |
| `regime_map.png` | clutter; title implied the ODE depends on Re | F02: legend outside, note that Re is an output, Re > 5000 region labelled |
| `coin_regimes.png` | unequal axes, dense bands, two mu_1 traces on one panel | F03: equal aspect, first 60 time units, ghost chords every 2 units, baseline only |
| `literature_validation.png` | overlapping labels, legend over data, curve clipped, tick labels overlapping, invented zones | F05: labels with leader lines, legends below, no invented zones |
| `i_star_sweep.png` | tiny text, wasted space | F06 |
| `flutter_frequency_analysis.png` | spectrum squeezed against 0 Hz on a 0-500 Hz axis | F07: 0-6 Hz with the peak marked |
| `energy_budget_reconciliation.png` | legend over curves | F08: legend below |
| `release_angle_sweep.png`, `chaos_ensemble_*` | raw labels such as `low_I_0.2`, lateral drift in mm up to 2 m | F09, F10: clean labels, symlog axis, histograms |
| `sph_vs_ode_comparison.png` | titles "Matched Case" and "Agreement" next to 21 to 65 % errors; label overlaps the title | F11: shows SPH and ODE tilt on the same axes with the SPH run length marked |
| `sph_vs_ode_overlay.png`, `vorticity_wake_snapshot.png` | synthetic (section 2.1) | F12 uses the real SPH CSVs; no replacement for the vorticity image (no data) |
| `validation_ladder_summary.png` | Test 5 bars at 11 and 8 with no scale or benchmark; Test 4 reference markers of unknown origin | F13: Test 5 on a log axis with the literature range and the factor off; Test 4 shows the accepted band; Test 7 labelled FAIL |
| `docs/screenshots/*` | reference screenshots were captured at t* = 50 and are labelled "undetermined (window_too_short)" | not changed here; capture to at least 80 time units |

## 4. Observations the figures make visible (for the paper)

- The flutter-to-tumble onset moves from I\*_c = 0.958 (mu_1 = 0) to 1.217 (mu_1 = 0.20). With the cited
  cards (flutter at 1.14, tumble at 1.38), only mu_1 = 0.2 lies inside the bracket.
- The tumbling window at mu_1 = 0.2 is narrow: 1.25 to 1.45 at theta_0 = 20 degrees. Mixed follows from 1.5.
- The ODE descent speed ratio U/U_t is 0.95 at I\* = 1.14 and 0.79 at I\* = 1.38, against 0.54 and 0.62 as cited:
  a 40 to 60 % difference at the transition.
- The Strouhal number falls from 0.48 to 0.07 across the fluttering range and crosses 0.20 near I\* = 0.4,
  so agreement with the cited 0.18 to 0.22 holds only there.
- The Pakistani demo coins (I\* 0.42 and 0.60) flutter in the model, while the ondrej-cloud coins at similar
  I\*_2D tumbled or moved chaotically in 3D.
- The edge peaks in the I\* = 0.8 landing histogram come from sampling a flutter oscillation at a random phase
  (arcsine distribution), not from clipping.
- SPH runs last 0.35 to 0.5 s and cover less than one flutter period, so SPH can support only qualitative statements.

## 5. How to regenerate

```bash
pip install numpy scipy pyyaml matplotlib pandas
PYTHONPATH=src python scripts/make_paper_figures.py          # all figures
PYTHONPATH=src python scripts/make_paper_figures.py F01 F03  # selected figures
```

Figures F03 and F11 run simulations (about one minute on one core); the others only read CSVs.
