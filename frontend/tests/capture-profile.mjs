import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const fixtureUrl = process.argv[2] ?? "http://127.0.0.1:4175/tests/visual-profile.html";
const projectRoot = path.resolve(import.meta.dirname, "..", "..");
const outputDirectory = path.join(projectRoot, "docs", "screenshots");
const temporaryProfile = await mkdtemp(path.join(os.tmpdir(), "smartanalytics-chrome-qa-"));
const resolvedTemporaryProfile = path.resolve(temporaryProfile);
if (!resolvedTemporaryProfile.startsWith(path.resolve(os.tmpdir()) + path.sep)) {
  throw new Error("Refusing to use a temporary profile outside the system temp directory.");
}
const devToolsPortFile = path.join(temporaryProfile, "DevToolsActivePort");

await mkdir(outputDirectory, { recursive: true });

const chrome = spawn(chromePath, [
  "--headless=new",
  "--disable-gpu",
  "--hide-scrollbars",
  "--no-first-run",
  "--no-default-browser-check",
  "--remote-debugging-port=0",
  `--user-data-dir=${temporaryProfile}`,
  "about:blank",
], { stdio: "ignore" });

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function stopChrome() {
  if (chrome.exitCode !== null) return;
  const exited = new Promise((resolve) => chrome.once("exit", resolve));
  chrome.kill();
  await Promise.race([exited, delay(5_000)]);
}

async function waitForPort() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const [port] = (await readFile(devToolsPortFile, "utf8")).trim().split(/\r?\n/);
      if (port) return Number(port);
    } catch (error) {
      if (error?.code !== "ENOENT" && error?.code !== "EBUSY") throw error;
    }
    await delay(100);
  }
  throw new Error("Chrome DevTools did not become ready.");
}

class CdpClient {
  constructor(url) {
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.socket = new WebSocket(url);
  }

  async open() {
    await new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, { once: true });
      this.socket.addEventListener("error", reject, { once: true });
    });
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message));
        else pending.resolve(message.result);
        return;
      }
      const callbacks = this.listeners.get(message.method) ?? [];
      this.listeners.delete(message.method);
      callbacks.forEach((callback) => callback(message.params));
    });
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  once(method) {
    return new Promise((resolve) => {
      const callbacks = this.listeners.get(method) ?? [];
      callbacks.push(resolve);
      this.listeners.set(method, callbacks);
    });
  }

  close() {
    this.socket.close();
  }
}

async function evaluate(client, expression) {
  const result = await client.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

async function loadViewport(client, viewport) {
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: viewport.width < 600,
    screenWidth: viewport.width,
    screenHeight: viewport.height,
  });
  await client.send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-reduced-motion", value: "reduce" }],
  });
  const loaded = client.once("Page.loadEventFired");
  await client.send("Page.navigate", { url: fixtureUrl });
  await loaded;
  await evaluate(client, "document.fonts.ready.then(() => true)");
  await delay(250);
}

async function capture(client, filename) {
  const result = await client.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(path.join(outputDirectory, filename), Buffer.from(result.data, "base64"));
}

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];

let client;
try {
  const port = await waitForPort();
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const target = targets.find((candidate) => candidate.type === "page");
  if (!target) throw new Error("Chrome did not expose a page target.");
  client = new CdpClient(target.webSocketDebuggerUrl);
  await client.open();
  await client.send("Page.enable");
  await client.send("Runtime.enable");

  const report = [];
  for (const viewport of viewports) {
    await loadViewport(client, viewport);
    await evaluate(client, "document.activeElement?.blur(); true");
    await client.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
    await client.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
    const metrics = await evaluate(client, `(() => {
      const focus = document.activeElement ? getComputedStyle(document.activeElement) : null;
      return {
        viewport: { width: innerWidth, height: innerHeight },
        globalScrollWidth: document.documentElement.scrollWidth,
        globalOverflow: document.documentElement.scrollWidth > innerWidth,
        tables: document.querySelectorAll('table').length,
        selectors: document.querySelectorAll('.sa-viz-selector select').length,
        chartDataPanels: document.querySelectorAll('.sa-profile-chart-data').length,
        heatmapRegionKeyboardScrollable: document.querySelector('.sa-heatmap-scroll')?.tabIndex === 0,
        focusedElement: document.activeElement?.tagName,
        focusOutline: focus ? focus.outlineStyle + ' ' + focus.outlineWidth : null,
        focusVisible: document.activeElement?.matches(':focus-visible') ?? false,
        reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
      };
    })()`);
    if (metrics.globalOverflow) throw new Error(`Global horizontal overflow at ${viewport.name}.`);
    if (metrics.tables < 4 || metrics.selectors !== 3 || metrics.chartDataPanels !== 3) {
      throw new Error(`Accessible chart structure is incomplete at ${viewport.name}.`);
    }
    if (!metrics.heatmapRegionKeyboardScrollable || metrics.focusedElement !== "SELECT") {
      throw new Error(`Keyboard access check failed at ${viewport.name}.`);
    }
    if (!metrics.reducedMotion || !metrics.focusVisible || metrics.focusOutline?.startsWith("none")) {
      throw new Error(`Motion/focus check failed at ${viewport.name}: ${JSON.stringify(metrics)}.`);
    }
    await capture(client, `advanced-insights-${viewport.name}.png`);
    report.push({ name: viewport.name, ...metrics });
  }

  await loadViewport(client, viewports[0]);
  await evaluate(client, "document.querySelector('.sa-correlation-card').scrollIntoView({ block: 'start' })");
  await delay(150);
  await capture(client, "advanced-insights-heatmap.png");
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} finally {
  client?.close();
  await stopChrome();
  await rm(resolvedTemporaryProfile, { recursive: true, force: true });
}
