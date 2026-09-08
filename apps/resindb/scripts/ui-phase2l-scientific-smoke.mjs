import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import { networkInterfaces } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const vite = path.join(root, 'node_modules', 'vite', 'bin', 'vite.js');
const previewPort = 4176;
const debugPort = 9226;
const artifacts = path.join(root, 'artifacts');
const downloads = path.join('/tmp', `resindb-phase2l-${process.pid}`);
const hosts = Object.values(networkInterfaces()).flat().filter(Boolean)
  .filter((entry) => entry.family === 'IPv4' && !entry.internal)
  .map((entry) => entry.address);
const appCandidates = [...new Set([
  process.env.RESINDB_UI_HOST,
  '127.0.0.1',
  'localhost',
  ...hosts,
].filter(Boolean).map((host) => `http://${host}:${previewPort}`))];
const dependencyShot = path.join(artifacts, 'ui-phase2l-dependency-heatmap.png');
const rheologyShot = path.join(artifacts, 'ui-phase2l-rheology-proxy.png');
const manifestPath = path.join(artifacts, 'ui-phase2l-manifest.json');

const chromeCandidates = [
  process.env.CHROME_BIN,
  '/usr/bin/google-chrome-stable',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);
const chromeBin = chromeCandidates.find((candidate) => existsSync(candidate));
if (!chromeBin) throw new Error(`No Chromium found: ${chromeCandidates.join(', ')}`);

const preview = spawn(process.execPath, [vite, 'preview', '--host', '0.0.0.0', '--port', String(previewPort), '--strictPort'], {
  cwd: root,
  env: { ...process.env, NODE_ENV: 'production' },
  stdio: ['ignore', 'pipe', 'pipe'],
});
const chrome = spawn(chromeBin, [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--no-proxy-server',
  '--proxy-bypass-list=<-loopback>', '--hide-scrollbars', '--remote-allow-origins=*',
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=/tmp/resindb-phase2l-chrome-${process.pid}`,
  '--window-size=1600,1000', 'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

let previewError = '';
let chromeError = '';
preview.stdout.on('data', (chunk) => process.stdout.write(chunk));
preview.stderr.on('data', (chunk) => { previewError += chunk; process.stderr.write(chunk); });
chrome.stderr.on('data', (chunk) => { chromeError += chunk; });
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitHttp(url, attempts = 80) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1000) });
      if (response.ok) return;
    } catch {}
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

class Cdp {
  constructor(url) {
    this.socket = new WebSocket(url);
    this.id = 0;
    this.pending = new Map();
    this.events = [];
  }
  async open() {
    await new Promise((resolve, reject) => {
      this.socket.addEventListener('open', resolve, { once: true });
      this.socket.addEventListener('error', reject, { once: true });
    });
    this.socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
        else pending.resolve(message.result || {});
      } else this.events.push(message);
    });
  }
  command(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { this.socket.close(); }
}

async function evaluate(cdp, expression) {
  const result = await cdp.command('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
    userGesture: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  }
  return result.result?.value;
}

async function waitCondition(cdp, expression, label, attempts = 120) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluate(cdp, expression)) return;
    await sleep(125);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

async function clickTitle(cdp, titles) {
  const clicked = await evaluate(cdp, `(() => {
    const titles = ${JSON.stringify(titles)};
    const button = Array.from(document.querySelectorAll('button')).find((item) =>
      titles.some((title) => (item.title || '').includes(title))
    );
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`Missing titled button: ${titles.join(', ')}`);
}

async function clickText(cdp, labels) {
  const clicked = await evaluate(cdp, `(() => {
    const labels = ${JSON.stringify(labels)};
    const button = Array.from(document.querySelectorAll('button')).find((item) =>
      labels.some((label) => (item.textContent || '').includes(label))
    );
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`Missing text button: ${labels.join(', ')}`);
}

async function capture(cdp, file) {
  const screenshot = await cdp.command('Page.captureScreenshot', {
    format: 'png', captureBeyondViewport: false, fromSurface: true,
  });
  writeFileSync(file, Buffer.from(screenshot.data, 'base64'));
}

async function exportPng(cdp, testId) {
  const before = readdirSync(downloads).filter((name) => name.endsWith('.png')).length;
  await evaluate(cdp, `document.querySelector('[data-testid="${testId}"]').click()`);
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const files = readdirSync(downloads).filter((name) => name.endsWith('.png') && !name.endsWith('.crdownload'));
    if (files.length > before) return files.sort().at(-1);
    await sleep(125);
  }
  throw new Error(`PNG export failed for ${testId}`);
}

async function triggerTooltip(cdp, rootSelector, expected) {
  const centered = await evaluate(cdp, `(() => {
    const canvas = document.querySelector('${rootSelector} canvas');
    if (!canvas) return false;
    canvas.scrollIntoView({ block: 'center', inline: 'nearest' });
    return true;
  })()`);
  if (!centered) return false;
  await sleep(300);

  const rect = await evaluate(cdp, `(() => {
    const canvas = document.querySelector('${rootSelector} canvas');
    if (!canvas) return null;
    const box = canvas.getBoundingClientRect();
    return {
      left: box.left,
      top: box.top,
      right: box.right,
      bottom: box.bottom,
      width: box.width,
      height: box.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    };
  })()`);
  if (!rect || rect.width < 200 || rect.height < 200) return false;

  const left = Math.max(1, rect.left);
  const top = Math.max(1, rect.top);
  const right = Math.min(rect.viewportWidth - 2, rect.right);
  const bottom = Math.min(rect.viewportHeight - 2, rect.bottom);
  const visibleWidth = right - left;
  const visibleHeight = bottom - top;
  if (visibleWidth < 200 || visibleHeight < 200) return false;

  await cdp.command('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 1, y: 1 });
  const probeRatios = [
    [0.2, 0.2], [0.35, 0.2], [0.5, 0.2], [0.65, 0.2], [0.8, 0.2],
    [0.2, 0.35], [0.35, 0.35], [0.5, 0.35], [0.65, 0.35], [0.8, 0.35],
    [0.2, 0.5], [0.35, 0.5], [0.5, 0.5], [0.65, 0.5], [0.8, 0.5],
    [0.2, 0.65], [0.35, 0.65], [0.5, 0.65], [0.65, 0.65], [0.8, 0.65],
    [0.2, 0.8], [0.35, 0.8], [0.5, 0.8], [0.65, 0.8], [0.8, 0.8],
  ];
  for (const [fx, fy] of probeRatios) {
    await cdp.command('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: left + visibleWidth * fx,
      y: top + visibleHeight * fy,
    });
    await sleep(120);
    const visible = await evaluate(cdp, `Array.from(document.querySelectorAll('div')).some((node) => {
      const text = node.innerText || '';
      const style = getComputedStyle(node);
      const box = node.getBoundingClientRect();
      return (style.position === 'absolute' || style.position === 'fixed')
        && style.pointerEvents === 'none'
        && box.width > 0 && box.height > 0
        && box.right > 0 && box.bottom > 0
        && box.left < window.innerWidth && box.top < window.innerHeight
        && ${JSON.stringify(expected)}.some((value) => text.includes(value));
    })`);
    if (visible) return true;
  }
  return false;
}

function runtimeErrors(cdp) {
  return cdp.events.filter((event) =>
    event.method === 'Runtime.exceptionThrown'
    || (event.method === 'Runtime.consoleAPICalled' && event.params?.type === 'error')
    || (event.method === 'Log.entryAdded' && event.params?.entry?.level === 'error')
  );
}

function stop(processHandle) {
  if (processHandle.exitCode === null) processHandle.kill('SIGTERM');
}

try {
  await waitHttp(`http://127.0.0.1:${previewPort}`);
  await waitHttp(`http://127.0.0.1:${debugPort}/json/version`);
  const pages = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((response) => response.json());
  const page = pages.find((item) => item.type === 'page');
  if (!page) throw new Error('Chromium page target is unavailable');
  const cdp = new Cdp(page.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.command('Page.enable');
  await cdp.command('Runtime.enable');
  await cdp.command('Log.enable');
  await cdp.command('Emulation.setDeviceMetricsOverride', {
    width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false,
  });
  mkdirSync(artifacts, { recursive: true });
  mkdirSync(downloads, { recursive: true });
  await cdp.command('Browser.setDownloadBehavior', {
    behavior: 'allow', downloadPath: downloads, eventsEnabled: true,
  });

  let appUrl = '';
  for (const candidate of appCandidates) {
    const navigation = await cdp.command('Page.navigate', { url: candidate });
    if (navigation.errorText) continue;
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if ((await evaluate(cdp, 'location.href')).startsWith(candidate)) {
        appUrl = candidate;
        break;
      }
      await sleep(100);
    }
    if (appUrl) break;
  }
  if (!appUrl) throw new Error('Chromium could not reach the preview');

  const admin = JSON.stringify({
    id: 'demo-admin', name: 'Demo Admin', email: 'admin@example.invalid', role: 'admin',
  });
  await evaluate(cdp, `sessionStorage.setItem('resindb-session', ${JSON.stringify(admin)});
    localStorage.setItem('resindb-tour-completed', 'true');
    localStorage.setItem('resindb-language', 'zh');
    localStorage.setItem('resindb-theme', 'light');
    localStorage.setItem('resindb-color-theme', 'indigo');`);
  await cdp.command('Page.reload', { ignoreCache: true });
  await waitCondition(cdp, `(document.body?.innerText || '').includes('13 RECORDS')`, 'dashboard');

  await clickTitle(cdp, ['性能指数引擎', 'Performance Index Engine']);
  await waitCondition(cdp, `document.body.innerText.includes('Performance Index Engine')`, 'formula editor');
  await clickText(cdp, ['Dependencies Heatmap']);
  await waitCondition(cdp, `!!document.querySelector('[data-testid="dependency-heatmap-migrated"]')`, 'dependency heatmap');
  await evaluate(cdp, `document.querySelector('[data-testid="dependency-heatmap-migrated"]').scrollIntoView({ block: 'start' })`);
  await waitCondition(cdp, `(() => {
    const root = document.querySelector('[data-testid="dependency-heatmap-migrated"]');
    const chart = root?.querySelector('[data-phase2l-chart="dependency-heatmap"]');
    const box = root?.querySelector('canvas')?.getBoundingClientRect();
    return root?.dataset.legacyWrapper === 'false'
      && root?.dataset.scientificBoundary === 'local-perturbation-not-causality'
      && Number(chart?.dataset.phase2lReadyCount ?? '0') >= 1
      && box?.width > 300 && box?.height > 250;
  })()`, 'dependency shared lifecycle');
  const dependencyInitialReady = Number(await evaluate(cdp, `document.querySelector('[data-phase2l-chart="dependency-heatmap"]')?.dataset.phase2lReadyCount || '0'`));
  if (dependencyInitialReady < 1) throw new Error(`Dependency chart ready count is invalid: ${dependencyInitialReady}`);
  const dependencyState = await evaluate(cdp, `(() => {
    const root = document.querySelector('[data-testid="dependency-heatmap-migrated"]');
    const text = root?.innerText || '';
    const selector = root?.querySelector('[data-testid="dependency-keyboard-cell-selector"]');
    return {
      boundary: text.includes('没有计算统计相关性') || text.includes('不是统计相关') || text.includes('Statistical association is not computed'),
      missing: text.includes('不会伪装成零') || text.includes('never as zero'),
      formula: text.includes('公式依赖') || text.includes('formula-dependency'),
      proxy: text.includes('规则生成代理') || text.includes('rule-generated proxies'),
      options: selector?.options?.length || 0,
    };
  })()`);
  if (!dependencyState.boundary || !dependencyState.missing || !dependencyState.formula
      || !dependencyState.proxy || dependencyState.options < 2) {
    throw new Error(`Dependency semantics failed: ${JSON.stringify(dependencyState)}`);
  }
  await evaluate(cdp, `(() => {
    const selector = document.querySelector('[data-testid="dependency-keyboard-cell-selector"]');
    const option = Array.from(selector.options).find((item) => item.value.includes('mfr::formula')) || selector.options[1];
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(selector, option.value);
    selector.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  await waitCondition(cdp, `!!document.querySelector('[data-testid="dependency-selection-summary"]')`, 'dependency selection');
  const dependencyTooltip = await triggerTooltip(cdp, '[data-testid="dependency-heatmap-scientific-chart"]', ['证据类型', 'Evidence type']);
  if (!dependencyTooltip) throw new Error('Dependency tooltip evidence type was not visible');
  await cdp.command('Emulation.setDeviceMetricsOverride', { width: 1380, height: 900, deviceScaleFactor: 1, mobile: false });
  await sleep(350);
  await cdp.command('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
  await sleep(350);
  const dependencyReady = Number(await evaluate(cdp, `document.querySelector('[data-phase2l-chart="dependency-heatmap"]')?.dataset.phase2lReadyCount || '0'`));
  if (dependencyReady !== dependencyInitialReady) {
    throw new Error(`Dependency chart reinitialized across resize: before=${dependencyInitialReady}, after=${dependencyReady}`);
  }
  await evaluate(cdp, `window.dispatchEvent(new CustomEvent('resindb-theme-change', { detail: 'dark' }))`);
  await waitCondition(cdp, `document.documentElement.classList.contains('dark')`, 'dependency dark theme');
  const dependencyPng = await exportPng(cdp, 'dependency-export-png');
  await capture(cdp, dependencyShot);
  await evaluate(cdp, `window.dispatchEvent(new CustomEvent('resindb-theme-change', { detail: 'light' }))`);
  await waitCondition(cdp, `!document.documentElement.classList.contains('dark')`, 'dependency light restore');
  await evaluate(cdp, `(() => {
    const modal = Array.from(document.querySelectorAll('div.fixed.inset-0')).find((node) =>
      (node.innerText || '').includes('Performance Index Engine'));
    const close = modal?.querySelector('button:has(svg.lucide-x)');
    if (!close) throw new Error('Formula editor close control missing');
    close.click();
  })()`);
  await waitCondition(cdp, `!document.querySelector('[data-testid="dependency-heatmap-migrated"]')`, 'formula editor close');

  await clickTitle(cdp, ['科研可视化', 'Scientific Visualization']);
  await waitCondition(cdp, `document.body.innerText.includes('科学图表') || document.body.innerText.includes('Scientific Charts')`, 'analytics');
  await clickText(cdp, ['流变动力学', 'Rheology Curve']);
  await waitCondition(cdp, `!!document.querySelector('[data-testid="rheology-graph-migrated"]')`, 'rheology graph');
  await waitCondition(cdp, `(() => {
    const root = document.querySelector('[data-testid="rheology-graph-migrated"]');
    const chart = root?.querySelector('[data-phase2l-chart="rheology-graph"]');
    const box = root?.querySelector('canvas')?.getBoundingClientRect();
    return root?.dataset.legacyWrapper === 'false'
      && root?.dataset.scientificBoundary === 'mfr-derived-proxy-not-measurement'
      && Number(chart?.dataset.phase2lReadyCount ?? '0') >= 1
      && box?.width > 300 && box?.height > 250;
  })()`, 'rheology shared lifecycle', 160);
  const rheologyInitialReady = Number(await evaluate(cdp, `document.querySelector('[data-phase2l-chart="rheology-graph"]')?.dataset.phase2lReadyCount || '0'`));
  if (rheologyInitialReady < 1) throw new Error(`Rheology chart ready count is invalid: ${rheologyInitialReady}`);
  await waitCondition(cdp, `(() => {
    const text = document.querySelector('[data-testid="rheology-graph-migrated"]')?.innerText || '';
    return text.includes('R² =') || text.includes('No positive proxy points') || text.includes('没有可拟合');
  })()`, 'rheology fit state', 160);
  const rheologyState = await evaluate(cdp, `(() => {
    const text = document.querySelector('[data-testid="rheology-graph-migrated"]')?.innerText || '';
    return {
      boundary: text.includes('不是实测流变') || text.includes('not measured rheology'),
      proxy: text.includes('MFR 派生') || text.includes('MFR-derived'),
      fitted: text.includes('代理点') || text.includes('proxy points'),
      units: text.includes('Pa·s'),
    };
  })()`);
  if (!rheologyState.boundary || !rheologyState.proxy || !rheologyState.fitted || !rheologyState.units) {
    throw new Error(`Rheology semantics failed: ${JSON.stringify(rheologyState)}`);
  }
  const rheologyTooltip = await triggerTooltip(cdp, '[data-testid="rheology-scientific-chart"]', ['筛选代理', 'Screening proxy']);
  if (!rheologyTooltip) throw new Error('Rheology tooltip evidence was not visible');
  await cdp.command('Emulation.setDeviceMetricsOverride', { width: 1420, height: 920, deviceScaleFactor: 1, mobile: false });
  await sleep(350);
  await cdp.command('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
  await sleep(350);
  const rheologyReady = Number(await evaluate(cdp, `document.querySelector('[data-phase2l-chart="rheology-graph"]')?.dataset.phase2lReadyCount || '0'`));
  if (rheologyReady !== rheologyInitialReady) {
    throw new Error(`Rheology chart reinitialized across resize: before=${rheologyInitialReady}, after=${rheologyReady}`);
  }
  await evaluate(cdp, `window.dispatchEvent(new CustomEvent('resindb-theme-change', { detail: 'dark' }))`);
  await waitCondition(cdp, `document.documentElement.classList.contains('dark')`, 'rheology dark theme');
  const rheologyPng = await exportPng(cdp, 'rheology-export-png');
  await capture(cdp, rheologyShot);

  const errors = runtimeErrors(cdp);
  if (errors.length) {
    throw new Error(`Chromium emitted ${errors.length} error(s): ${errors.map((event) =>
      event.params?.entry?.text || event.params?.exceptionDetails?.exception?.description || event.method).join('; ')}`);
  }
  const manifest = {
    schemaVersion: 'phase2l-chromium-evidence-1.0.0',
    generatedAt: new Date().toISOString(),
    appUrl,
    dependencyHeatmap: {
      sharedScientificEChart: true,
      legacyWrapperRemoved: true,
      scientificBoundaryVisible: true,
      missingEvidenceNotZero: true,
      keyboardSelectionVerified: true,
      tooltipVerified: true,
      initialReadyCount: dependencyInitialReady,
      resizeReinitializationCount: dependencyReady - dependencyInitialReady,
      lightAndDarkThemeVerified: true,
      pngExport: dependencyPng,
      screenshot: path.basename(dependencyShot),
    },
    rheologyGraph: {
      sharedScientificEChart: true,
      legacyWrapperRemoved: true,
      proxyAndFitSemanticsVerified: true,
      logarithmicUnitsVisible: true,
      tooltipVerified: true,
      initialReadyCount: rheologyInitialReady,
      resizeReinitializationCount: rheologyReady - rheologyInitialReady,
      lightAndDarkThemeVerified: true,
      pngExport: rheologyPng,
      screenshot: path.basename(rheologyShot),
    },
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  cdp.close();
  console.log('Phase 2L Chromium smoke passed: both migrations, semantics, lifecycle, theme, tooltip and PNG export are verified.');
} catch (error) {
  throw new Error([
    error instanceof Error ? error.stack || error.message : String(error),
    previewError ? `\nPreview stderr:\n${previewError}` : '',
    chromeError ? `\nChromium stderr tail:\n${chromeError.slice(-4000)}` : '',
  ].join(''));
} finally {
  stop(chrome);
  stop(preview);
}
