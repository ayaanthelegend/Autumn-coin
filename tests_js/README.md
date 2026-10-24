# Autumn Coin: JavaScript Core Test Suite

Automated verification suite testing the pure mathematical physics engine and trajectory regime classifier extracted directly from `visualizer.html`.

## Test Execution

Run using Node.js (Node 18+ supported, zero external npm dependencies):

```bash
node tests_js/test_core.mjs
```

## What is Verified

1. **DOM-Free Core Extraction**:
   - Isolates the `// <CORE>` ... `// </CORE>` block from `visualizer.html` and executes it inside Node's `node:vm` context.
2. **Classifier Thresholds Synchronization**:
   - Asserts classifier defaults match [`config/base.yaml`](../config/base.yaml) dynamically.
3. **Andersen et al. (2005b) Benchmark Reproduction**:
   - Simulates thin plate cards ($h/L = 0.01$) released at $\theta_0 = 0.1\,\text{rad}$ with $v_0 = -U_0$ for $t^* = 50$:
     - $I^* = 1.10 \to (7.26, -32.94) a$ vs reference $(7.3, -33.0) a$ (error $0.073 a < 0.3 a$).
     - $I^* = 1.40 \to (-26.14, -24.25) a$ vs reference $(-26.1, -24.3) a$ (error $0.060 a < 0.3 a$).
     - $I^* = 1.60 \to (6.09, -29.30) a$ vs reference $(6.1, -29.3) a$ (error $0.008 a < 0.3 a$).
4. **Catalog Coin Regime Parity**:
   - Simulates all 9 enabled catalog coins from [`config/coins.yaml`](../config/coins.yaml) to $H_\text{fall} = 80 L$.
   - Asserts exact regime match with [`results/coin_regimes.csv`](../results/coin_regimes.csv).
5. **Preset Mappings**:
   - Verifies Presets [2]–[4] map to fluttering, tumbling, and mixed coins; Preset [1] (steady) is cleanly disabled with explanatory tooltip.
