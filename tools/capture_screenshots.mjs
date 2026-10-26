/**
 * Browser Automation and Screenshot Capture Script (tools/capture_screenshots.mjs)
 * 
 * Uses native Node 24 and Headless Chrome via Chrome DevTools Protocol (CDP).
 * Zero external npm dependencies.
 * 
 * Verifies & Produces:
 * - Page loads with zero console errors
 * - Desktop layout at 1440x900 px
 * - Mobile responsive layout at 375x812 px with document.documentElement.scrollWidth <= 375
 * - Screenshots of all 9 catalog coins with visible chartTraj
 * - Screenshots of the 3 canonical reference thin-plate benchmarks (I* = 1.1, 1.4, 1.6) run to t* = 50
 * - Screenshot of the multi-coin comparison grid modal (with axis ticks & common scale)
 * - Validation manifest written to docs/screenshots/manifest.json asserting distinct I* values
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const outDir = path.join(rootDir, 'docs', 'screenshots');
fs.mkdirSync(outDir, { recursive: true });

const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const port = 9333;
const tempProfile = path.join(os.tmpdir(), 'chrome_cdp_profile_' + Date.now());

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
    this.consoleErrors = [];
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method === 'Runtime.consoleAPICalled') {
        const type = msg.params.type;
        const text = msg.params.args.map(a => a.value ?? a.description ?? '').join(' ');
        if (type === 'error') {
          this.consoleErrors.push(text);
          console.error(`[Browser Console Error]: ${text}`);
        }
      } else if (msg.method === 'Runtime.exceptionThrown') {
        const text = msg.params.exceptionDetails.text || msg.params.exceptionDetails.exception?.description || "Exception";
        this.consoleErrors.push(text);
        console.error(`[Browser Uncaught Exception]: ${text}`);
      }
    };
  }

  async waitOpen() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise(resolve => { this.ws.onopen = resolve; });
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expr) {
    const res = await this.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (res.exceptionDetails) {
      const errText = res.exceptionDetails.exception?.description || res.exceptionDetails.text || "Eval Exception";
      throw new Error(`Browser Eval Error: ${errText}\nExpression was:\n${expr}`);
    }
    return res.result ? res.result.value : undefined;
  }

  async setViewport(width, height) {
    await this.send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: width < 600
    });
  }

  async captureScreenshot(filePath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    const buf = Buffer.from(res.data, 'base64');
    fs.writeFileSync(filePath, buf);
    console.log(`Saved screenshot: ${path.relative(rootDir, filePath)}`);
  }

  async close() {
    this.ws.close();
  }
}

async function main() {
  const osInfo = `${os.type()} ${os.release()} (${os.arch()})`;
  console.log("======================================================================");
  console.log("  AUTUMN COIN: CDP AUTOMATED SCREENSHOT & VERIFICATION RUNNER");
  console.log("======================================================================");
  console.log(`Operating System: ${osInfo}`);
  console.log(`Browser: Google Chrome (Headless) at ${chromePath}`);
  console.log(`Port: ${port}\n`);

  const chromeProc = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${tempProfile}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    'about:blank'
  ], { stdio: 'ignore' });

  // Connect to Chrome
  let wsUrl = null;
  for (let i = 0; i < 30; ++i) {
    await new Promise(r => setTimeout(r, 200));
    try {
      const resp = await fetch(`http://127.0.0.1:${port}/json/list`);
      const tabs = await resp.json();
      const pageTab = tabs.find(t => t.type === 'page');
      if (pageTab && pageTab.webSocketDebuggerUrl) {
        wsUrl = pageTab.webSocketDebuggerUrl;
        break;
      }
    } catch (e) {}
  }

  if (!wsUrl) {
    chromeProc.kill();
    throw new Error("Could not get Chrome debugging WebSocket URL");
  }

  const client = new CDPClient(wsUrl);
  await client.waitOpen();
  await client.send('Page.enable');
  await client.send('Runtime.enable');

  const fileUrl = 'file:///' + path.join(rootDir, 'visualizer.html').replace(/\\/g, '/');
  console.log("Navigating to:", fileUrl);
  await client.send('Page.navigate', { url: fileUrl });
  await new Promise(r => setTimeout(r, 1200));

  const manifest = {
    generated_at: new Date().toISOString(),
    environment: {
      os: osInfo,
      browser: "Google Chrome Headless CDP",
      viewport_desktop: "1440x900",
      viewport_mobile: "375x812"
    },
    screenshots: []
  };

  // 1. Verify 1440px desktop
  console.log("\n--- Testing Desktop Viewport (1440x900) ---");
  await client.setViewport(1440, 900);
  await client.eval(`(() => {
    window.dispatchEvent(new Event('resize'));
    const el = document.getElementById("chartTraj");
    if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
  })()`);
  await new Promise(r => setTimeout(r, 600));
  const deskFile = path.join(outDir, 'desktop_1440_overview.png');
  await client.captureScreenshot(deskFile);
  manifest.screenshots.push({
    file: 'desktop_1440_overview.png',
    type: 'overview_desktop',
    status: 'captured'
  });

  // 2. Verify 375px mobile
  console.log("\n--- Testing Mobile Viewport (375x812) ---");
  await client.setViewport(375, 812);
  await client.eval(`(() => {
    window.dispatchEvent(new Event('resize'));
  })()`);
  await new Promise(r => setTimeout(r, 600));
  const scrollW = await client.eval(`(() => document.documentElement.scrollWidth)()`);
  console.log(`Mobile document scrollWidth: ${scrollW} px (must be <= 375)`);
  if (scrollW > 375) {
    throw new Error(`FAIL: Horizontal scroll detected at 375px (scrollWidth = ${scrollW}px)`);
  }
  const mobileFile = path.join(outDir, 'mobile_375_overview.png');
  await client.captureScreenshot(mobileFile);
  manifest.screenshots.push({
    file: 'mobile_375_overview.png',
    type: 'overview_mobile',
    status: 'captured',
    scrollWidth: scrollW
  });

  // Restore desktop viewport
  await client.setViewport(1440, 900);
  await client.eval(`(() => {
    window.dispatchEvent(new Event('resize'));
  })()`);
  await new Promise(r => setTimeout(r, 400));

  // 3. Capture Catalog Coins
  console.log("\n--- Capturing Screenshots for 9 Catalog Coins ---");
  const catalogCoins = [
    "pk_rs10",
    "pk_rs5_2002",
    "design_acrylic_24x1.2",
    "design_aluminium_24x1.5",
    "design_brass_24x3.0",
    "design_brass_24x3.5",
    "design_steel_24x4.5",
    "design_lead_24x3.5",
    "design_tungsten_24x3.0"
  ];

  for (const cid of catalogCoins) {
    // Select coin inside IIFE
    await client.eval(`(() => {
      const sel = document.getElementById("selCoin");
      sel.value = "${cid}";
      onCoinSelect("${cid}");
      // Run 30 physics frames to establish visible trajectory
      for (let f = 0; f < 30; ++f) {
        stepPhysicsFrame();
      }
      // Scroll sidebar so chartTraj is visibly centered
      const el = document.getElementById("chartTraj");
      if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
    })()`);

    // Verify selection and read state back
    const state = await client.eval(`(() => {
      const sel = document.getElementById("selCoin").value;
      const act = activeCoin ? activeCoin.id : null;
      const istar = activeCoin ? activeCoin.I_star : null;
      const reg = (typeof getActiveRegime === "function") ? getActiveRegime() : (document.getElementById("regimeBadge")?.innerText || "");
      return { sel, act, istar, reg };
    })()`);

    if (state.sel !== cid || state.act !== cid) {
      throw new Error(`Coin select mismatch for ${cid}: selCoin=${state.sel}, activeCoin=${state.act}`);
    }

    await new Promise(r => setTimeout(r, 300));
    const filename = `coin_${cid}.png`;
    await client.captureScreenshot(path.join(outDir, filename));

    manifest.screenshots.push({
      file: filename,
      coin_id: cid,
      I_star: state.istar,
      regime: state.reg,
      group: 'catalog'
    });
  }

  // 4. Capture Canonical Reference Benchmarks (I* = 1.1, 1.4, 1.6)
  console.log("\n--- Capturing Canonical Reference Benchmarks (I* = 1.1, 1.4, 1.6) ---");
  const refCoins = [
    { id: "ref_1.1", file: "ref_istar_1.1_flutter.png", expectedIStar: 1.1, expectedRegime: "fluttering" },
    { id: "ref_1.4", file: "ref_istar_1.4_tumble.png", expectedIStar: 1.4, expectedRegime: "tumbling" },
    { id: "ref_1.6", file: "ref_istar_1.6_mixed.png", expectedIStar: 1.6, expectedRegime: "mixed" }
  ];

  for (const rc of refCoins) {
    // Select coin & run to t* = 50 in isolated IIFE
    await client.eval(`(() => {
      const sel = document.getElementById("selCoin");
      sel.value = "${rc.id}";
      onCoinSelect("${rc.id}");
    })()`);

    // Verify selection before running
    const preCheck = await client.eval(`(() => {
      const sel = document.getElementById("selCoin").value;
      const act = activeCoin ? activeCoin.id : null;
      const istar = activeCoin ? activeCoin.I_star : null;
      return { sel, act, istar };
    })()`);

    if (preCheck.sel !== rc.id || preCheck.act !== rc.id) {
      throw new Error(`Pre-run selection mismatch for ${rc.id}: sel=${preCheck.sel}, act=${preCheck.act}`);
    }
    if (Math.abs(preCheck.istar - rc.expectedIStar) > 0.05) {
      throw new Error(`Reference I* mismatch for ${rc.id}: got ${preCheck.istar}, expected ${rc.expectedIStar}`);
    }

    // Step physics to t* = 50 tau_0
    await client.eval(`(() => {
      const targetT = 50.0 * odeSim.t_unit;
      while (odeSim.time < targetT && odeSim.time < 30.0) {
        stepPhysicsFrame();
      }
      // Ensure chartTraj is scrolled into view in the sidebar
      const el = document.getElementById("chartTraj");
      if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
    })()`);

    // Read back final state
    const postState = await client.eval(`(() => {
      const sel = document.getElementById("selCoin").value;
      const act = activeCoin ? activeCoin.id : null;
      const istar = activeCoin ? activeCoin.I_star : null;
      const reg = (typeof getActiveRegime === "function") ? getActiveRegime() : (document.getElementById("regimeBadge")?.innerText || "");
      const reason = window.__currentRegimeReason || null;
      return { sel, act, istar, reg, reason };
    })()`);

    if (postState.sel !== rc.id || postState.act !== rc.id) {
      throw new Error(`Post-run selection mismatch for ${rc.id}: sel=${postState.sel}, act=${postState.act}`);
    }

    await new Promise(r => setTimeout(r, 400));
    await client.captureScreenshot(path.join(outDir, rc.file));

    manifest.screenshots.push({
      file: rc.file,
      coin_id: rc.id,
      I_star: postState.istar,
      regime: postState.reg,
      reason: postState.reason,
      group: 'reference'
    });
  }

  // Check that all 3 reference screenshots have distinct I* values
  console.log("\n--- Validating Reference Benchmark Distinctness ---");
  const refEntries = manifest.screenshots.filter(s => s.group === 'reference');
  assert.equal(refEntries.length, 3, "Expected exactly 3 reference screenshots in manifest");

  const istars = refEntries.map(s => Number(s.I_star.toFixed(3)));
  const uniqueIstars = new Set(istars);
  console.log(`Reference screenshot I* values: ${JSON.stringify(istars)}`);
  if (uniqueIstars.size !== 3) {
    throw new Error(`FAIL: Reference screenshots share I* values! Values found: ${JSON.stringify(istars)}`);
  }
  console.log("PASS: All 3 reference screenshots have distinct I* values.");

  // 5. Capture Multi-Coin Comparison Modal
  console.log("\n--- Capturing Multi-Coin Comparison Modal ---");
  await client.eval(`(() => {
    openCompareModal();
  })()`);
  await new Promise(r => setTimeout(r, 800));
  const compFile = path.join(outDir, 'compare_coins_grid.png');
  await client.captureScreenshot(compFile);
  manifest.screenshots.push({
    file: 'compare_coins_grid.png',
    type: 'comparison_grid',
    status: 'captured'
  });

  await client.eval(`(() => {
    closeCompareModal();
  })()`);

  // Write manifest.json
  const manifestPath = path.join(outDir, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8');
  console.log(`\nSaved manifest: ${path.relative(rootDir, manifestPath)}`);

  // Check console errors
  console.log("\n--- Verifying Console Errors ---");
  if (client.consoleErrors.length === 0) {
    console.log("PASS: 0 console errors detected throughout entire session.");
  } else {
    console.error(`FAIL: ${client.consoleErrors.length} console error(s) logged:`, client.consoleErrors);
    throw new Error(`Encountered ${client.consoleErrors.length} browser console errors`);
  }

  await client.close();
  chromeProc.kill();
  try { fs.rmSync(tempProfile, { recursive: true, force: true }); } catch (e) {}

  console.log("\n======================================================================");
  console.log("  ALL SCREENSHOTS CAPTURED AND VALIDATED SUCCESSFULLY");
  console.log("======================================================================\n");
}

main().catch(err => {
  console.error("FATAL ERROR in capture_screenshots:", err);
  process.exit(1);
});
