/**
 * Browser Automation and Screenshot Capture Script (scripts/capture_screenshots.mjs)
 * 
 * Uses native Node 24 and Headless Chrome via Chrome DevTools Protocol (CDP).
 * Zero external npm dependencies.
 * 
 * Verifies:
 * - Page loads with zero console errors
 * - Desktop layout at 1440x900 px
 * - Mobile responsive layout at 375x812 px with document.documentElement.scrollWidth <= 375
 * - Screenshots of all 9 catalog coins
 * - Screenshots of the 3 reference thin-plate benchmarks (I* = 1.1, 1.4, 1.6)
 * - Screenshot of the multi-coin comparison grid modal
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
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
        const text = msg.params.exceptionDetails.text;
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
    return res.result.value;
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
  console.log("Launching Headless Chrome on port", port, "...");
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

  // 1. Verify 1440px desktop
  console.log("\n--- Testing Desktop Viewport (1440x900) ---");
  await client.setViewport(1440, 900);
  await client.eval("window.dispatchEvent(new Event('resize'));");
  await new Promise(r => setTimeout(r, 600));
  await client.captureScreenshot(path.join(outDir, 'desktop_1440_overview.png'));

  // 2. Verify 375px mobile
  console.log("\n--- Testing Mobile Viewport (375x812) ---");
  await client.setViewport(375, 812);
  await client.eval("window.dispatchEvent(new Event('resize'));");
  await new Promise(r => setTimeout(r, 600));
  const scrollW = await client.eval("document.documentElement.scrollWidth;");
  console.log(`Mobile document scrollWidth: ${scrollW} px (must be <= 375)`);
  if (scrollW > 375) {
    console.error(`FAIL: Horizontal scroll detected at 375px (scrollWidth = ${scrollW}px)`);
  } else {
    console.log("PASS: No horizontal scroll at 375px.");
  }
  await client.captureScreenshot(path.join(outDir, 'mobile_375_overview.png'));

  // Restore desktop viewport
  await client.setViewport(1440, 900);
  await client.eval("window.dispatchEvent(new Event('resize'));");
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
    await client.eval(`
      document.getElementById("selCoin").value = "${cid}";
      onCoinSelect("${cid}");
      // Run 20 physics frames to establish motion and trajectory
      for (let f = 0; f < 30; ++f) {
        stepPhysicsFrame();
      }
    `);
    await new Promise(r => setTimeout(r, 300));
    await client.captureScreenshot(path.join(outDir, `coin_${cid}.png`));
  }

  // 4. Capture Reference Benchmarks (I* = 1.1, 1.4, 1.6)
  console.log("\n--- Capturing Canonical Reference Benchmarks (I* = 1.1, 1.4, 1.6) ---");
  const refCoins = [
    { id: "ref_1.1", file: "ref_istar_1.1_flutter.png" },
    { id: "ref_1.4", file: "ref_istar_1.4_tumble.png" },
    { id: "ref_1.6", file: "ref_istar_1.6_mixed.png" }
  ];

  for (const rc of refCoins) {
    await client.eval(`
      document.getElementById("selCoin").value = "${rc.id}";
      onCoinSelect("${rc.id}");
      // Run to t* = 50
      const targetT = 50.0 * odeSim.t_unit;
      while (odeSim.time < targetT && odeSim.time < 30.0) {
        stepPhysicsFrame();
      }
    `);
    await new Promise(r => setTimeout(r, 400));
    await client.captureScreenshot(path.join(outDir, rc.file));
  }

  // 5. Capture Multi-Coin Comparison Modal
  console.log("\n--- Capturing Multi-Coin Comparison Modal ---");
  await client.eval("openCompareModal();");
  await new Promise(r => setTimeout(r, 800));
  await client.captureScreenshot(path.join(outDir, 'compare_coins_grid.png'));
  await client.eval("closeCompareModal();");

  // Check console errors
  console.log("\n--- Verifying Console Errors ---");
  if (client.consoleErrors.length === 0) {
    console.log("PASS: 0 console errors detected throughout entire session.");
  } else {
    console.error(`FAIL: ${client.consoleErrors.length} console error(s) logged:`, client.consoleErrors);
  }

  await client.close();
  chromeProc.kill();
  try { fs.rmSync(tempProfile, { recursive: true, force: true }); } catch (e) {}

  console.log("\n✓ All screenshots captured and saved to docs/screenshots/");
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
