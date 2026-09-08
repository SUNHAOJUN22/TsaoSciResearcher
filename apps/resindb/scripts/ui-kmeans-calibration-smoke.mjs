import { spawn } from 'node:child_process';
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { networkInterfaces } from 'node:os';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const viteBin = path.join(projectRoot, 'node_modules', 'vite', 'bin', 'vite.js');
const host = '0.0.0.0';
const healthHost = '127.0.0.1';
const previewPort = 4175;
const debugPort = 9225;
const healthUrl = `http://${healthHost}:${previewPort}`;
const networkHosts = Object.values(networkInterfaces())
  .flat()
  .filter(Boolean)
  .filter((entry) => entry.family === 'IPv4' && !entry.internal)
  .map((entry) => entry.address);
const appUrlCandidates = [...new Set([
  process.env.RESINDB_UI_HOST,
  '127.0.0.1',
  'localhost',
  ...networkHosts,
].filter(Boolean).map((candidate) => `http://${candidate}:${previewPort}`))];
const artifactDir = path.join(projectRoot, 'artifacts');
const screenshotPath = path.join(artifactDir, 'ui-kmeans-device-calibration.png');
const auditScreenshotPath = path.join(artifactDir, 'ui-kmeans-profile-audit.png');
const manifestPath = path.join(artifactDir, 'ui-smoke-manifest.json');
const downloadDir = path.join('/tmp', `resindb-kmeans-audit-download-${process.pid}`);

const chromeCandidates = [
  process.env.CHROME_BIN,
  '/usr/bin/google-chrome-stable',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);
const chromeBin = chromeCandidates.find((candidate) => existsSync(candidate));
if (!chromeBin) {
  throw new Error(`No Chromium-compatible browser found. Checked: ${chromeCandidates.join(', ')}`);
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
const chromeProfile = path.join('/tmp', `resindb-kmeans-calibration-${process.pid}`);
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
      // Keep waiting for the preview or debugging endpoint.
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
    throw new Error(
      response.exceptionDetails.exception?.description
      || response.exceptionDetails.text
      || JSON.stringify(response.exceptionDetails),
    );
  }
  return response.result?.value;
}

async function waitForCondition(session, expression, description, attempts = 100) {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    if (await evaluate(session, expression)) return;
    await sleep(125);
  }
  throw new Error(`Timed out waiting for ${description}`);
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

async function clickButtonByText(session, patterns) {
  const serialized = JSON.stringify(patterns);
  const clicked = await evaluate(session, `(() => {
    const patterns = ${serialized};
    const button = Array.from(document.querySelectorAll('button')).find((candidate) =>
      patterns.some((pattern) => (candidate.textContent || '').includes(pattern))
    );
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`Unable to find button text matching: ${patterns.join(', ')}`);
}

async function capture(session, targetPath) {
  const screenshot = await session.command('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
    fromSurface: true,
  });
  writeFileSync(targetPath, Buffer.from(screenshot.data, 'base64'));
}

async function waitForAuditDownload(attempts = 80) {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const files = existsSync(downloadDir)
      ? readdirSync(downloadDir).filter((file) => file.endsWith('.json'))
      : [];
    if (files.length > 0) return path.join(downloadDir, files[0]);
    await sleep(125);
  }
  throw new Error('Timed out waiting for the K-Means profile audit JSON download');
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
  mkdirSync(downloadDir, { recursive: true });
  await session.command('Browser.setDownloadBehavior', {
    behavior: 'allow',
    downloadPath: downloadDir,
    eventsEnabled: true,
  });

  let appUrl = '';
  for (const candidate of appUrlCandidates) {
    const navigation = await session.command('Page.navigate', { url: candidate });
    if (navigation.errorText) continue;
    for (let attempt = 1; attempt <= 40; attempt += 1) {
      const currentUrl = await evaluate(session, 'location.href');
      if (currentUrl.startsWith(candidate)) {
        appUrl = candidate;
        break;
      }
      await sleep(100);
    }
    if (appUrl) break;
  }
  if (!appUrl) throw new Error('Chromium could not reach the preview');

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
  await waitForCondition(
    session,
    `(document.body?.innerText || '').includes('13 RECORDS')`,
    'authenticated dashboard',
  );

  await clickButtonByTitle(session, ['科研可视化', 'Scientific Visualization']);
  await waitForCondition(
    session,
    `document.body.innerText.includes('科学图表') || document.body.innerText.includes('Scientific Charts')`,
    'scientific analytics view',
  );
  await clickButtonByText(session, ['Canvas 热力散点图', 'Canvas']);
  await waitForCondition(
    session,
    `!!document.querySelector('[data-testid="kmeans-backend-calibration"]')`,
    'K-Means calibration panel',
  );

  await clickButtonByText(session, ['K-Means 自动聚类分组', 'K-Means Auto Grouping']);
  await waitForCondition(
    session,
    `Array.from(document.querySelectorAll('button')).some((button) =>
      (button.textContent || '').includes('清除聚类')
      || (button.textContent || '').includes('Clear Clusters')
    )`,
    'K-Means workload completion',
  );

  await evaluate(
    session,
    `document.querySelector('[data-testid="kmeans-calibration-toggle"]').click()`,
  );
  await waitForCondition(
    session,
    `!!document.querySelector('[data-testid="kmeans-calibration-privacy"]')
      && !!document.querySelector('[data-testid="kmeans-calibration-run"]')
      && !!document.querySelector('[data-testid="kmeans-calibration-clear"]')`,
    'K-Means calibration controls',
  );

  const panelState = await evaluate(session, `(() => {
    const privacy = document.querySelector('[data-testid="kmeans-calibration-privacy"]')?.textContent || '';
    const run = document.querySelector('[data-testid="kmeans-calibration-run"]');
    const clear = document.querySelector('[data-testid="kmeans-calibration-clear"]');
    return {
      privacy,
      runVisible: !!run,
      clearVisible: !!clear,
      profileDatabasePresent: indexedDB !== undefined,
    };
  })()`);
  if (
    !panelState.runVisible
    || !panelState.clearVisible
    || !panelState.profileDatabasePresent
    || !panelState.privacy.includes('IndexedDB')
    || !panelState.privacy.includes('不会上传')
  ) {
    throw new Error(`K-Means calibration controls are incomplete: ${JSON.stringify(panelState)}`);
  }

  mkdirSync(artifactDir, { recursive: true });
  await capture(session, screenshotPath);

  await evaluate(session, `(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (text) => { window.__resindbCopiedAuditSummary = text; },
      },
    });
    document.querySelector('[data-testid="kmeans-audit-toggle"]').click();
    return true;
  })()`);
  await waitForCondition(
    session,
    `!!document.querySelector('[data-testid="kmeans-audit-details"]')
      && !!document.querySelector('[data-testid="kmeans-audit-copy"]')
      && !!document.querySelector('[data-testid="kmeans-audit-download"]')
      && (document.querySelector('[data-testid="kmeans-audit-details"]')?.textContent || '').includes('SHA-256')`,
    'K-Means profile audit controls',
  );

  await evaluate(session, `document.querySelector('[data-testid="kmeans-audit-copy"]').click()`);
  await waitForCondition(
    session,
    `typeof window.__resindbCopiedAuditSummary === 'string'
      && window.__resindbCopiedAuditSummary.includes('schema=kmeans-profile-audit-1.0.0')
      && window.__resindbCopiedAuditSummary.includes('notice=not-a-cross-device-performance-conclusion')`,
    'K-Means audit summary copy',
  );
  await evaluate(session, `document.querySelector('[data-testid="kmeans-audit-download"]').click()`);
  const auditFile = await waitForAuditDownload();
  const auditDocument = JSON.parse(readFileSync(auditFile, 'utf8'));
  if (
    auditDocument.schemaVersion !== 'kmeans-profile-audit-1.0.0'
    || auditDocument.notice !== 'not-a-cross-device-performance-conclusion'
    || !/^[0-9a-f]{64}$/.test(auditDocument.digest)
    || auditDocument.workload?.sampleCount !== 13
    || !(auditDocument.workload?.dimensions > 0)
    || !(auditDocument.workload?.maxClusters > 0)
    || auditDocument.autoDecision?.selectedBackend !== 'typescript'
    || auditDocument.autoDecision?.reason !== 'missing-compatible-local-profile'
    || JSON.stringify(auditDocument).includes('gradeName')
    || JSON.stringify(auditDocument).includes('manufacturer')
  ) {
    throw new Error(`K-Means profile audit JSON is invalid: ${JSON.stringify(auditDocument)}`);
  }
  const expectedExcluded = [
    'product-data',
    'clustering-inputs',
    'raw-benchmark-samples',
    'user-identity',
    'network-addresses',
  ];
  if (JSON.stringify(auditDocument.excludedFields) !== JSON.stringify(expectedExcluded)) {
    throw new Error(`K-Means audit excluded field contract changed: ${JSON.stringify(auditDocument.excludedFields)}`);
  }

  await capture(session, auditScreenshotPath);

  const runtimeErrors = session.events.filter(
    (event) =>
      event.method === 'Runtime.exceptionThrown'
      || (event.method === 'Runtime.consoleAPICalled' && event.params?.type === 'error')
      || (event.method === 'Log.entryAdded' && event.params?.entry?.level === 'error'),
  );
  if (runtimeErrors.length > 0) {
    const summaries = runtimeErrors
      .map((event) => event.params?.entry?.text || event.params?.exceptionDetails?.text || event.method)
      .join('; ');
    throw new Error(`Browser emitted ${runtimeErrors.length} error(s): ${summaries}`);
  }

  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  manifest.screenshots = {
    ...(manifest.screenshots ?? {}),
    kmeansCalibration: path.basename(screenshotPath),
    kmeansProfileAudit: path.basename(auditScreenshotPath),
  };
  manifest.kmeansCalibration = {
    panelVisible: true,
    privacyDisclosure: true,
    runControlVisible: true,
    clearControlVisible: true,
    sharedCiCalibrationExecuted: false,
    profileStorage: 'device-local-indexeddb',
    actualWorkloadCaptured: true,
    auditDetailsVisible: true,
    auditSummaryCopied: true,
    auditJsonDownloaded: true,
    auditSchemaVersion: auditDocument.schemaVersion,
    auditDigest: auditDocument.digest,
    auditProductDataExcluded: true,
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  session.close();

  console.log('K-Means calibration and profile audit UI smoke passed: actual workload, privacy, copy, JSON download and field whitelist are verified.');
  console.log(`Screenshots: ${screenshotPath}, ${auditScreenshotPath}`);
  console.log(`Audit JSON: ${auditFile}`);
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
