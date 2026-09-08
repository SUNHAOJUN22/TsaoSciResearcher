import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { networkInterfaces } from 'node:os';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const viteBin = path.join(projectRoot, 'node_modules', 'vite', 'bin', 'vite.js');
const host = '0.0.0.0';
const healthHost = '127.0.0.1';
const previewPort = 4174;
const debugPort = 9224;
const healthUrl = `http://${healthHost}:${previewPort}`;
const networkHosts = Object.values(networkInterfaces()).flat().filter(Boolean).filter((entry) => entry.family === 'IPv4' && !entry.internal).map((entry) => entry.address);
const appUrlCandidates = [...new Set([process.env.RESINDB_UI_HOST, '127.0.0.1', 'localhost', ...networkHosts].filter(Boolean).map((candidate) => `http://${candidate}:${previewPort}`))];
const artifactDir = path.join(projectRoot, 'artifacts');
const screenshotPaths = {
  dashboard: path.join(artifactDir, 'ui-dashboard-zh-light.png'),
  emptyState: path.join(artifactDir, 'ui-empty-state.png'),
  productDetail: path.join(artifactDir, 'ui-product-detail.png'),
  analytics: path.join(artifactDir, 'ui-scientific-analytics.png'),
  dependencyMap: path.join(artifactDir, 'ui-dependency-map.png'),
  dashboardEnDark: path.join(artifactDir, 'ui-dashboard-en-dark.png'),
  mobile: path.join(artifactDir, 'ui-mobile-dashboard.png'),
};

const chromeCandidates = [
  process.env.CHROME_BIN,
  '/usr/bin/google-chrome-stable',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);
const chromeBin = chromeCandidates.find((candidate) => existsSync(candidate));
if (!chromeBin) {
  throw new Error(
    `No Chromium-compatible browser found. Checked: ${chromeCandidates.join(', ')}`,
  );
}

const preview = spawn(
  process.execPath,
  [viteBin, 'preview', '--host', host, '--port', String(previewPort), '--strictPort'],
  {
    cwd: projectRoot,
    env: { ...process.env, NODE_ENV: 'production' },
    stdio: ['ignore', 'pipe', 'pipe'],
  },
);

const chromeProfile = path.join('/tmp', `resindb-ui-smoke-${process.pid}`);
const chrome = spawn(
  chromeBin,
  [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--no-proxy-server',
    '--proxy-bypass-list=<-loopback>',
    '--hide-scrollbars',
    '--remote-allow-origins=*',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${chromeProfile}`,
    '--window-size=1600,1000',
    'about:blank',
  ],
  { stdio: ['ignore', 'pipe', 'pipe'] },
);

let previewError = '';
let chromeError = '';
preview.stdout.on('data', (chunk) => process.stdout.write(chunk));
preview.stderr.on('data', (chunk) => {
  previewError += chunk.toString();
  process.stderr.write(chunk);
});
chrome.stderr.on('data', (chunk) => {
  chromeError += chunk.toString();
});

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitForHttp(url, attempts = 60) {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_000) });
      if (response.ok) return response;
    } catch {
      // Keep waiting until the process is ready.
    }
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

class CdpSession {
  constructor(webSocketUrl) {
    this.socket = new WebSocket(webSocketUrl);
    this.sequence = 0;
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
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(JSON.stringify(message.error)));
        else resolve(message.result || {});
      } else {
        this.events.push(message);
      }
    });
  }

  command(method, params = {}) {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.socket.close();
  }
}

async function evaluate(session, expression) {
  const response = await session.command('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
    userGesture: true,
  });
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text || JSON.stringify(response.exceptionDetails));
  }
  return response.result?.value;
}

async function waitForCondition(session, expression, description, attempts = 80) {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    if (await evaluate(session, expression)) return;
    await sleep(125);
  }
  throw new Error(`Timed out waiting for ${description}`);
}

async function capture(session, targetPath) {
  const screenshot = await session.command('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
    fromSurface: true,
  });
  writeFileSync(targetPath, Buffer.from(screenshot.data, 'base64'));
}

async function clickButtonByTitle(session, patterns) {
  const serialized = JSON.stringify(patterns);
  const clicked = await evaluate(session, `(() => {
    const patterns = ${serialized};
    const button = Array.from(document.querySelectorAll('button')).find((candidate) =>
      patterns.some((pattern) => (candidate.title || '').includes(pattern))
    );
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`Unable to find button title matching: ${patterns.join(', ')}`);
}

async function waitForDashboard(session) {
  for (let attempt = 1; attempt <= 80; attempt += 1) {
    const state = await evaluate(
      session,
      `(() => ({
        ready: document.readyState,
        text: document.body?.innerText || '',
        alert: (document.body?.innerText || '').includes('System Alert')
      }))()`,
    );
    if (state.alert) throw new Error('Authenticated UI rendered the System Alert error boundary');
    if (
      state.ready === 'complete' &&
      (state.text.includes('DATA WAREHOUSE') || state.text.includes('数据中心')) &&
      state.text.includes('13 RECORDS')
    ) {
      return state.text;
    }
    await sleep(250);
  }
  throw new Error('Authenticated dashboard did not become ready');
}

function stop(processHandle) {
  if (processHandle.exitCode === null) processHandle.kill('SIGTERM');
}

try {
  await waitForHttp(healthUrl);
  await waitForHttp(`http://${healthHost}:${debugPort}/json/version`);
  const pages = await fetch(`http://${healthHost}:${debugPort}/json/list`).then((response) => response.json());
  const target = pages.find((page) => page.type === 'page');
  if (!target) throw new Error('Chromium did not expose a page target');

  const session = new CdpSession(target.webSocketDebuggerUrl);
  await session.open();
  await session.command('Page.enable');
  await session.command('Runtime.enable');
  await session.command('Log.enable');
  await session.command('Emulation.setDeviceMetricsOverride', {
    width: 1600,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });
  let appUrl = '';
  const navigationErrors = [];
  for (const candidate of appUrlCandidates) {
    const navigation = await session.command('Page.navigate', { url: candidate });
    if (navigation.errorText) {
      navigationErrors.push(`${candidate}: ${navigation.errorText}`);
      continue;
    }
    for (let attempt = 1; attempt <= 40; attempt += 1) {
      const currentUrl = await evaluate(session, 'location.href');
      if (currentUrl.startsWith(candidate)) {
        appUrl = candidate;
        break;
      }
      await sleep(100);
    }
    if (appUrl) break;
    navigationErrors.push(`${candidate}: navigation did not settle`);
  }
  if (!appUrl) throw new Error(`Chromium could not reach preview. ${navigationErrors.join('; ')}`);

  const admin = JSON.stringify({
    id: 'demo-admin',
    name: 'Demo Admin',
    email: 'admin@example.invalid',
    role: 'admin',
  });
  await evaluate(
    session,
    `sessionStorage.setItem('resindb-session', ${JSON.stringify(admin)});
     localStorage.setItem('resindb-tour-completed', 'true');
     localStorage.setItem('resindb-language', 'zh');
     localStorage.setItem('resindb-theme', 'light');
     localStorage.setItem('resindb-color-theme', 'indigo');`,
  );
  await session.command('Page.reload', { ignoreCache: true });
  const bodyText = await waitForDashboard(session);

  const cjkFontEvidence = await evaluate(
    session,
    `(async () => {
      if (!document.fonts) return { available: false, family: null, status: 'unsupported' };
      await document.fonts.ready;
      const sample = '树脂数据库科学图表中文验收';
      const candidates = [
        'Noto Sans CJK SC',
        'Noto Sans SC',
        'Microsoft YaHei',
        'PingFang SC',
        'WenQuanYi Micro Hei'
      ];
      const family = candidates.find((name) => document.fonts.check('16px "' + name + '"', sample)) || null;
      return { available: Boolean(family), family, status: document.fonts.status };
    })()`,
  );
  if (!cjkFontEvidence.available) {
    throw new Error(`No usable CJK font is available to Chromium: ${JSON.stringify(cjkFontEvidence)}`);
  }

  const runtimeErrors = session.events.filter(
    (event) =>
      event.method === 'Runtime.exceptionThrown' ||
      (event.method === 'Runtime.consoleAPICalled' && event.params?.type === 'error') ||
      (event.method === 'Log.entryAdded' && event.params?.entry?.level === 'error'),
  );
  if (runtimeErrors.length > 0) {
    const summaries = runtimeErrors
      .map((event) => {
        const entry = event.params?.entry;
        const detail = entry?.url ? `${entry.text} (${entry.url})` : entry?.text;
        return detail || event.params?.exceptionDetails?.text || event.method;
      })
      .join('; ');
    throw new Error(`Browser console contains ${runtimeErrors.length} error(s): ${summaries}`);
  }

  mkdirSync(artifactDir, { recursive: true });
  await capture(session, screenshotPaths.dashboard);

  await evaluate(session, `(() => {
    const input = document.querySelector('#global-search-input');
    if (!input) throw new Error('Global search input is unavailable');
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, '__NO_MATCH_RESINDB_UI_TEST__');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
  await waitForCondition(session, `document.querySelectorAll('tbody tr[data-index]').length === 0 && !!Array.from(document.querySelectorAll('button')).find((button) => /重置|Reset/.test(button.textContent || ''))`, 'empty-state feedback');
  await capture(session, screenshotPaths.emptyState);

  await evaluate(session, `(() => {
    const input = document.querySelector('#global-search-input');
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, '');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
  await waitForCondition(session, `document.querySelectorAll('tbody tr[data-index]').length > 0`, 'data grid rows after clearing search');
  await evaluate(session, `(() => {
    const row = document.querySelector('tbody tr[data-index]');
    if (!row) throw new Error('No product row available');
    row.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
    return true;
  })()`);
  await waitForCondition(session, `!!document.querySelector('button[aria-label="Close details"]')`, 'product detail drawer');
  await capture(session, screenshotPaths.productDetail);
  await evaluate(session, `document.querySelector('button[aria-label="Close details"]').click()`);
  await waitForCondition(session, `!document.querySelector('button[aria-label="Close details"]')`, 'product detail drawer close');

  await clickButtonByTitle(session, ['科研可视化', 'Scientific Visualization']);
  await waitForCondition(session, `document.body.innerText.includes('科学图表') || document.body.innerText.includes('Scientific Charts')`, 'scientific analytics view');
  const rheologyActivated = await evaluate(session, `(() => {
    const button = Array.from(document.querySelectorAll('button'))
      .find((candidate) => /RHEOLOGY/i.test(candidate.textContent || ''));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (!rheologyActivated) throw new Error('Unable to activate the rheology scientific chart');
  await waitForCondition(
    session,
    `(() => {
      const figure = Array.from(document.querySelectorAll('[data-scientific-figure="true"]'))
        .find((candidate) => candidate.dataset.scientificFigureState === 'ready'
          && Number(candidate.dataset.scientificFigurePoints || 0) > 0);
      const surface = figure?.querySelector('[data-scientific-chart-rendered="true"]');
      const canvas = surface?.querySelector('canvas');
      return Boolean(canvas && canvas.width >= 500 && canvas.height >= 250);
    })()`,
    'completed non-empty rheology chart rendering',
    160,
  );
  const analyticsEvidence = await evaluate(session, `(() => {
    const figure = Array.from(document.querySelectorAll('[data-scientific-figure="true"]'))
      .find((candidate) => candidate.dataset.scientificFigureState === 'ready'
        && Number(candidate.dataset.scientificFigurePoints || 0) > 0);
    const canvas = figure?.querySelector('[data-scientific-chart-rendered="true"] canvas');
    if (!canvas) return { ready: false, reason: 'canvas-missing' };
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return { ready: false, reason: '2d-context-missing' };
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const pixelCount = canvas.width * canvas.height;
    const stride = Math.max(1, Math.floor(Math.sqrt(pixelCount / 120000)));
    let sampled = 0;
    let nonBackground = 0;
    let chromatic = 0;
    for (let y = 0; y < canvas.height; y += stride) {
      for (let x = 0; x < canvas.width; x += stride) {
        const index = (y * canvas.width + x) * 4;
        const red = pixels[index];
        const green = pixels[index + 1];
        const blue = pixels[index + 2];
        const alpha = pixels[index + 3];
        sampled += 1;
        if (alpha > 8 && Math.min(red, green, blue) < 242) nonBackground += 1;
        if (alpha > 8 && Math.max(red, green, blue) - Math.min(red, green, blue) > 12) chromatic += 1;
      }
    }
    return {
      ready: nonBackground > 500 && chromatic > 50,
      width: canvas.width,
      height: canvas.height,
      sampled,
      nonBackground,
      chromatic,
      points: Number(figure.dataset.scientificFigurePoints || 0)
    };
  })()`);
  if (!analyticsEvidence.ready) {
    throw new Error(`Scientific chart canvas is blank or lacks plotted signal: ${JSON.stringify(analyticsEvidence)}`);
  }
  await sleep(250);
  await capture(session, screenshotPaths.analytics);

  await clickButtonByTitle(session, ['依赖网络谱图', 'Dependency']);
  await waitForCondition(session, `!!document.querySelector('[data-testid="dependency-map-svg"]')`, 'dependency map');
  await evaluate(session, `(() => {
    const node = document.querySelector('[data-testid="dependency-map-svg"] g');
    if (!node) throw new Error('Dependency map has no clickable nodes');
    node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  })()`);
  await waitForCondition(session, `document.body.innerText.includes('CAS：') || document.body.innerText.includes('chemical') || document.body.innerText.includes('resin')`, 'dependency node details');
  await capture(session, screenshotPaths.dependencyMap);

  await clickButtonByTitle(session, ['数据仓库', 'Data Warehouse']);
  await waitForCondition(session, `document.body.innerText.includes('13 RECORDS')`, 'dashboard before responsive capture');
  await session.command('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  });
  await sleep(500);
  await capture(session, screenshotPaths.mobile);
  await session.command('Emulation.setDeviceMetricsOverride', {
    width: 1600,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });

  const preferenceState = await evaluate(
    session,
    `(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const languageButton = buttons.find((button) => button.title?.includes('Switch to English'));
      const themeButton = buttons.find((button) => button.title?.includes('深色夜间模式'));
      const paletteButton = buttons.find((button) => button.title?.includes('皮肤配色主题'));
      if (!languageButton || !themeButton || !paletteButton) {
        throw new Error('Language/theme/palette controls are not visible in the top bar');
      }
      languageButton.click();
      themeButton.click();
      paletteButton.click();
      return true;
    })()`,
  );
  if (!preferenceState) throw new Error('Failed to activate preference controls');
  await sleep(500);

  await evaluate(
    session,
    `(() => {
      const emeraldButton = Array.from(document.querySelectorAll('button'))
        .find((button) => button.textContent?.includes('Emerald Bio'));
      if (!emeraldButton) throw new Error('Emerald palette option is unavailable');
      emeraldButton.click();
      return true;
    })()`,
  );
  await sleep(500);

  const savedPreferences = await evaluate(
    session,
    `(() => ({
      language: localStorage.getItem('resindb-language'),
      theme: localStorage.getItem('resindb-theme'),
      colorTheme: localStorage.getItem('resindb-color-theme'),
      htmlLanguage: document.documentElement.lang,
      dark: document.documentElement.classList.contains('dark')
    }))()`,
  );
  if (
    savedPreferences.language !== 'en' ||
    savedPreferences.theme !== 'dark' ||
    savedPreferences.colorTheme !== 'emerald' ||
    savedPreferences.htmlLanguage !== 'en' ||
    !savedPreferences.dark
  ) {
    throw new Error(`Preference controls did not persist correctly: ${JSON.stringify(savedPreferences)}`);
  }

  await clickButtonByTitle(session, ['Scientific Visualization', '科研可视化']);
  await clickButtonByTitle(session, ['Data Warehouse', '数据中心']);
  await sleep(500);
  await capture(session, screenshotPaths.dashboardEnDark);

  const finalRuntimeErrors = session.events.filter(
    (event) =>
      event.method === 'Runtime.exceptionThrown' ||
      (event.method === 'Runtime.consoleAPICalled' && event.params?.type === 'error') ||
      (event.method === 'Log.entryAdded' && event.params?.entry?.level === 'error'),
  );
  if (finalRuntimeErrors.length > 0) {
    const summaries = finalRuntimeErrors.map((event) => event.params?.entry?.text || event.params?.exceptionDetails?.exception?.description || event.params?.exceptionDetails?.text || event.method).join('; ');
    throw new Error(`Browser runtime emitted ${finalRuntimeErrors.length} error(s) during interactive flows: ${summaries}`);
  }

  const artifactManifest = {
    schemaVersion: 2,
    generatedAt: new Date().toISOString(),
    appUrl,
    recordCount: bodyText.includes('13 RECORDS') ? 13 : null,
    screenshots: Object.fromEntries(Object.entries(screenshotPaths).map(([name, file]) => [name, path.basename(file)])),
    preferences: savedPreferences,
    cjkFont: cjkFontEvidence,
    scientificCanvas: analyticsEvidence,
  };
  writeFileSync(path.join(artifactDir, 'ui-smoke-manifest.json'), `${JSON.stringify(artifactManifest, null, 2)}
`);
  session.close();

  console.log(
    'UI smoke test passed: readable CJK typography, dashboard, empty state, product details, non-blank scientific chart, dependency map, responsive layout and preferences are interactive.',
  );
  console.log(`CJK font: ${cjkFontEvidence.family}`);
  console.log(`Scientific canvas evidence: ${JSON.stringify(analyticsEvidence)}`);
  console.log(`Screenshots: ${Object.values(screenshotPaths).join(', ')}`);
} catch (error) {
  const diagnostics = [
    error instanceof Error ? error.stack || error.message : String(error),
    previewError ? `\nPreview stderr:\n${previewError}` : '',
    chromeError ? `\nChromium stderr (tail):\n${chromeError.slice(-4_000)}` : '',
  ].join('');
  throw new Error(diagnostics);
} finally {
  stop(chrome);
  stop(preview);
}
