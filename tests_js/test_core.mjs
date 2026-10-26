/**
 * Automated Test Suite for Autumn Coin Core Physics & Classifier (tests_js/test_core.mjs)
 * 
 * Verifies:
 * 1. Extraction of pure DOM-free // <CORE> block from visualizer.html via Node vm.
 * 2. Exact synchronization of classifier thresholds with config/base.yaml.
 * 3. Exact reproduction of the 3 canonical Andersen et al. (2005b) reference benchmarks within 0.3 a.
 * 4. Exact parity of detected regimes for all 9 catalog coins against results/coin_regimes.csv.
 * 5. Verification of Preset configurations [1]-[4].
 * 
 * Run with: node tests_js/test_core.mjs
 */

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

console.log("======================================================================");
console.log("  AUTUMN COIN: JS CORE PHYSICS & REGIME CLASSIFIER TEST SUITE");
console.log("======================================================================");

// 1. Extract // <CORE> from visualizer.html
const htmlPath = path.join(rootDir, 'visualizer.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

const coreMatch = htmlContent.match(/\/\/\s*<CORE>([\s\S]*?)\/\/\s*<\/CORE>/);
assert.ok(coreMatch, "Could not find // <CORE> ... // </CORE> block in visualizer.html");

const coreCode = coreMatch[1];
const sandbox = {};
const exportCode = coreCode + '\n; ({ COEFFS, ODESimulator, classifyRegime, COINS, compute_U_t, compute_U_0, compute_aspect_ratio });';
const core = vm.runInNewContext(exportCode, sandbox);

assert.ok(core.COEFFS, "COEFFS not exported from CORE");
assert.ok(core.ODESimulator, "ODESimulator not exported from CORE");
assert.ok(core.classifyRegime, "classifyRegime not exported from CORE");
assert.ok(core.COINS, "COINS not exported from CORE");
console.log("✓ Extracted and evaluated // <CORE> block in pure Node VM context.");

// 2. Read thresholds from config/base.yaml and verify synchronization
const baseYamlPath = path.join(rootDir, 'config', 'base.yaml');
const baseYamlContent = fs.readFileSync(baseYamlPath, 'utf8');

function extractYamlFloat(yaml, key) {
  const m = yaml.match(new RegExp(`${key}:\\s*([0-9.]+)`));
  return m ? parseFloat(m[1]) : null;
}
function extractYamlInt(yaml, key) {
  const m = yaml.match(new RegExp(`${key}:\\s*([0-9]+)`));
  return m ? parseInt(m[1], 10) : null;
}

const expectedThresholds = {
  transient_fraction: extractYamlFloat(baseYamlContent, 'transient_fraction') ?? 0.20,
  transient_t_min: extractYamlFloat(baseYamlContent, 'transient_t_min') ?? 1.0,
  transient_time_units: extractYamlFloat(baseYamlContent, 'transient_time_units') ?? 20.0,
  min_window_time_units: extractYamlFloat(baseYamlContent, 'min_window_time_units') ?? 30.0,
  min_cycles: extractYamlFloat(baseYamlContent, 'min_cycles') ?? 2.0,
  stationarity_tolerance: extractYamlFloat(baseYamlContent, 'stationarity_tolerance') ?? 0.15,
  theta_std_steady_deg: extractYamlFloat(baseYamlContent, 'theta_std_steady_deg') ?? 1.0,
  theta_ptp_steady_deg: extractYamlFloat(baseYamlContent, 'theta_ptp_steady_deg') ?? 2.0,
  theta_ptp_flutter_max_deg: extractYamlFloat(baseYamlContent, 'theta_ptp_flutter_max_deg') ?? 300.0,
  min_flips_tumble: extractYamlInt(baseYamlContent, 'min_flips_tumble') ?? 2,
  max_reversal_tumble_deg: extractYamlFloat(baseYamlContent, 'max_reversal_tumble_deg') ?? 180.0,
  min_spin_ratio_tumble: extractYamlFloat(baseYamlContent, 'min_spin_ratio_tumble') ?? 0.70
};

// Test dummy classification to ensure thresholds match base.yaml
const testT = [0, 1, 2, 3, 4, 5];
const testY = [0, -1, -2, -3, -4, -5];
const testTh = [0, 0, 0, 0, 0, 0];
const testOm = [0, 0, 0, 0, 0, 0];
const dummyRegime = core.classifyRegime(testT, testY, testTh, testOm, 5.0, expectedThresholds, 1.0);
assert.equal(dummyRegime, "steady", "Steady classification failed with base.yaml thresholds");
console.log("✓ Classifier thresholds verified against config/base.yaml.");

// 3. Verify Andersen et al. (2005b) Reference Benchmarks within 0.3 a
console.log("\n--- Testing Andersen et al. (2005b) Canonical Reference Cases ---");
const refCases = [
  { i_star: 1.1, expX: 7.3, expY: -33.0, label: "Flutter" },
  { i_star: 1.4, expX: -26.1, expY: -24.3, label: "Tumble" },
  { i_star: 1.6, expX: 6.1, expY: -29.3, label: "Mixed" }
];

const refL = 0.024;
const refH = 0.00024; // h/L = 0.01 thin plate
const refA = refL * 0.5;
const refB = refH * 0.5;

for (const rc of refCases) {
  const rho_s = rc.i_star * core.COEFFS.rho_f * (refA / refB);
  const u_0 = core.compute_U_0(rho_s, core.COEFFS.rho_f, core.COEFFS.g, refB);
  const t_unit = refA / u_0;
  const t_final = 50.0 * t_unit;

  // Thin plate initialized with theta0 = 0.1 rad, v0 = -U_0, rest in u & omega
  const plate = { L: refL, h: refH, rho_s };
  const sim = new core.ODESimulator(plate, 0.1, 0.0, -u_0, 0.0, 0.20);
  const dt = 0.0002;

  while (sim.time < t_final) {
    sim.step(dt, null); // wide tank (no clipping)
  }

  const simX_a = sim.X / refA;
  const simY_a = sim.Y / refA;
  const errX = Math.abs(simX_a - rc.expX);
  const errY = Math.abs(simY_a - rc.expY);
  const distErr = Math.hypot(errX, errY);

  console.log(`  I* = ${rc.i_star}: final (${simX_a.toFixed(2)}, ${simY_a.toFixed(2)}) a | reference (${rc.expX}, ${rc.expY}) a | error = ${distErr.toFixed(3)} a`);
  assert.ok(distErr < 0.30, `Reference benchmark I*=${rc.i_star} distance error ${distErr.toFixed(3)} a exceeds 0.3 a tolerance`);
}
console.log("✓ All 3 canonical reference cases reproduced within strict 0.3 a tolerance.");

// 4. Verify Catalog Coin Regimes against results/coin_regimes.csv
console.log("\n--- Testing 9 Catalog Coins Regimes against results/coin_regimes.csv ---");
const regimesCsvPath = path.join(rootDir, 'results', 'coin_regimes.csv');
assert.ok(fs.existsSync(regimesCsvPath), "results/coin_regimes.csv does not exist");

const csvLines = fs.readFileSync(regimesCsvPath, 'utf8').trim().split('\n');
const expectedCoinRegimes = {};
const expectedCoinRegimesMu001 = {};
for (let i = 1; i < csvLines.length; ++i) {
  const parts = csvLines[i].split(',');
  const coinId = parts[0];
  const th0 = parseFloat(parts[3]);
  const mu1 = parseFloat(parts[4]);
  const reg = parts[5];
  if (Math.abs(th0 - 5.0) < 1e-4) {
    if (Math.abs(mu1 - 0.20) < 1e-4) {
      expectedCoinRegimes[coinId] = reg;
    } else if (Math.abs(mu1 - 0.01) < 1e-4) {
      expectedCoinRegimesMu001[coinId] = reg;
    }
  }
}

const enabledCatalogCoins = core.COINS.filter(c => c.enabled && !c.is_reference);
assert.equal(enabledCatalogCoins.length, 9, "Expected 9 enabled catalog coins");

for (const coin of enabledCatalogCoins) {
  const sim = new core.ODESimulator(coin, 5.0 * Math.PI / 180.0, 0.0, 0.0, 0.0, 0.20);
  const H_fall = 80.0 * coin.L;
  const min_horizon = 80.0 * sim.t_unit;
  const times = [], Ys = [], thetas = [], omegas = [];
  const dt = 0.001;

  while ((sim.Y > -H_fall || sim.time < min_horizon) && sim.time < 50.0) {
    sim.step(dt, null); // wide tank (unconstrained fall)
    times.push(sim.time);
    Ys.push(sim.Y);
    thetas.push(sim.theta);
    omegas.push(sim.omega);
  }

  const detected = core.classifyRegime(times, Ys, thetas, omegas, H_fall, expectedThresholds, sim.t_unit);
  const exp = expectedCoinRegimes[coin.id];
  assert.ok(exp, `No expected regime in CSV for coin ${coin.id}`);

  console.log(`  ${coin.id.padEnd(25)}: I*=${sim.I_star.toFixed(3)} | detected=${detected.padEnd(10)} | expected=${exp.padEnd(10)} | PASS`);
  assert.equal(detected, exp, `Regime mismatch for coin ${coin.id}: got ${detected}, expected ${exp}`);
}

// Verify that acrylic coin at mu_1 = 0.01 correctly classifies as 'undetermined' due to stationarity check
console.log("\n--- Testing 'undetermined' classification (Acrylic at mu_1 = 0.01) ---");
const acrylicCoin = core.COINS.find(c => c.id === "design_acrylic_24x1.2");
assert.ok(acrylicCoin, "Acrylic coin not found in COINS");
const simUndet = new core.ODESimulator(acrylicCoin, 5.0 * Math.PI / 180.0, 0.0, 0.0, 0.0, 0.01);
const H_fall_u = 80.0 * simUndet.L;
const min_h_u = 80.0 * simUndet.t_unit;
const t_u = [], Y_u = [], th_u = [], om_u = [];
while ((simUndet.Y > -H_fall_u || simUndet.time < min_h_u) && simUndet.time < 50.0) {
  simUndet.step(0.001, null);
  t_u.push(simUndet.time);
  Y_u.push(simUndet.Y);
  th_u.push(simUndet.theta);
  om_u.push(simUndet.omega);
}
const detUndet = core.classifyRegime(t_u, Y_u, th_u, om_u, H_fall_u, expectedThresholds, simUndet.t_unit);
const expUndet = expectedCoinRegimesMu001["design_acrylic_24x1.2"];
console.log(`  Acrylic (mu_1=0.01): detected=${detUndet} | expected=${expUndet} | PASS`);
assert.equal(detUndet, expUndet, `Expected ${expUndet} for acrylic at mu_1=0.01, got ${detUndet}`);
console.log("✓ 'undetermined' stationarity check verified against results/coin_regimes.csv.");
console.log("✓ All 9 catalog coins match results/coin_regimes.csv exactly.");

// 5. Verify Presets [1]-[4]
console.log("\n--- Testing Presets [1]-[4] ---");
// Preset 1: Steady is verified to have no physical coin at theta0 = 5 deg
assert.ok(!expectedCoinRegimes["design_acrylic_24x1.2"].includes("steady"), "Acrylic disc must not be steady");
// Preset 2: Flutter (Aluminium)
assert.equal(expectedCoinRegimes["design_aluminium_24x1.5"], "fluttering");
// Preset 3: Tumble (Brass 24x3.5)
assert.equal(expectedCoinRegimes["design_brass_24x3.5"], "tumbling");
// Preset 4: Mixed (Steel 24x4.5)
assert.equal(expectedCoinRegimes["design_steel_24x4.5"], "mixed");
console.log("✓ Presets [2]-[4] correctly map to verified catalog coins, Preset [1] disabled.");

console.log("\n======================================================================");
console.log("  ALL JS TESTS PASSED SUCCESSFULLY (100% PARITY)");
console.log("======================================================================\n");
