import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPORT = path.join(ROOT, 'reports', 'UNICODE_INTEGRITY_REPORT.json');
const EXTENSIONS = new Set([
  '.cfg', '.cjs', '.css', '.csv', '.html', '.ini', '.js', '.jsx', '.json', '.jsonl',
  '.md', '.mdx', '.mjs', '.ps1', '.py', '.scss', '.sh', '.sql', '.svg', '.toml', '.ts',
  '.tsx', '.tsv', '.txt', '.xml', '.yaml', '.yml',
]);
const EXCLUDED_PARTS = new Set([
  '.git', 'artifacts', 'build', 'coverage', 'dist', 'node_modules', '.vite', '.vitest',
]);
const token = (...values) => String.fromCodePoint(...values);
const MOJIBAKE = [
  ['latin1-replacement', token(0x00ef, 0x00bf, 0x00bd)],
  ['smart-apostrophe', token(0x00e2, 0x20ac, 0x2122)],
  ['smart-quote', token(0x00e2, 0x20ac, 0x0153)],
  ['gbk-replacement', token(0x951f, 0x65a4, 0x62f7)],
];

function trackedTextFiles() {
  const raw = execFileSync('git', ['-C', ROOT, 'ls-files', '-z']);
  return raw
    .toString('utf8')
    .split('\0')
    .filter(Boolean)
    .map((relative) => relative.replaceAll('\\', '/'))
    .filter((relative) => {
      const parts = relative.split('/');
      return !parts.some((part) => EXCLUDED_PARTS.has(part))
        && EXTENSIONS.has(path.extname(relative).toLowerCase());
    })
    .sort();
}

export function auditBytes(relative, data) {
  const failures = [];
  if (data.length >= 3 && data[0] === 0xef && data[1] === 0xbb && data[2] === 0xbf) {
    failures.push({ path: relative, category: 'bom', detail: 'UTF-8 BOM is forbidden' });
  }
  if (data.includes(0x0d)) {
    failures.push({ path: relative, category: 'line_endings', detail: 'CR or CRLF is forbidden' });
  }
  if (data.length > 0 && data[data.length - 1] !== 0x0a) {
    failures.push({ path: relative, category: 'terminal_lf', detail: 'missing terminal LF' });
  } else if (data.length > 1 && data[data.length - 2] === 0x0a) {
    failures.push({ path: relative, category: 'terminal_lf', detail: 'more than one terminal LF' });
  }

  let text;
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(data);
  } catch (error) {
    failures.push({ path: relative, category: 'invalid_utf8', detail: String(error) });
    return failures;
  }
  if (text.includes(String.fromCodePoint(0xfffd))) {
    failures.push({ path: relative, category: 'replacement_character', detail: 'U+FFFD is forbidden' });
  }
  if (text.normalize('NFC') !== text) {
    failures.push({ path: relative, category: 'nfc', detail: 'text is not NFC-normalized' });
  }
  const controls = [...text]
    .filter((character) => {
      const value = character.codePointAt(0);
      return value !== 0x09 && value !== 0x0a
        && ((value >= 0 && value <= 0x08) || (value >= 0x0b && value <= 0x1f) || value === 0x7f);
    })
    .map((character) => `U+${character.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')}`);
  if (controls.length > 0) {
    failures.push({
      path: relative,
      category: 'control_character',
      detail: [...new Set(controls)].sort().join(', '),
    });
  }
  const markers = MOJIBAKE.filter(([, marker]) => text.includes(marker)).map(([label]) => label);
  if (markers.length > 0) {
    failures.push({ path: relative, category: 'mojibake', detail: markers.join(', ') });
  }
  return failures;
}

export function normalizeBytes(data) {
  let text = new TextDecoder('utf-8', { fatal: true }).decode(data);
  if (text.startsWith(String.fromCodePoint(0xfeff))) text = text.slice(1);
  text = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n').normalize('NFC');
  return Buffer.from(`${text.replace(/\n+$/u, '')}\n`, 'utf8');
}

export function normalizeTrackedText() {
  let changed = 0;
  for (const relative of trackedTextFiles()) {
    const absolute = path.join(ROOT, relative);
    const stat = fs.lstatSync(absolute);
    if (!stat.isFile() || stat.isSymbolicLink()) {
      throw new Error(`unsafe tracked text path: ${relative}`);
    }
    const before = fs.readFileSync(absolute);
    const after = normalizeBytes(before);
    if (!before.equals(after)) {
      fs.writeFileSync(absolute, after, { mode: stat.mode });
      changed += 1;
    }
  }
  return changed;
}

export function auditTrackedText() {
  const failures = [];
  const files = trackedTextFiles();
  for (const relative of files) {
    const absolute = path.join(ROOT, relative);
    const stat = fs.lstatSync(absolute);
    if (!stat.isFile() || stat.isSymbolicLink()) {
      failures.push({ path: relative, category: 'unsafe_path', detail: 'not a regular tracked file' });
      continue;
    }
    failures.push(...auditBytes(relative, fs.readFileSync(absolute)));
  }
  failures.sort((left, right) =>
    `${left.path}\0${left.category}\0${left.detail}`.localeCompare(
      `${right.path}\0${right.category}\0${right.detail}`,
    ),
  );
  return {
    schemaVersion: 'resindb.unicode-integrity/v1',
    verdict: failures.length === 0 ? 'PASS' : 'FAIL',
    scannedTextFiles: files.length,
    failures,
  };
}

function render(report) {
  return `${JSON.stringify(report, null, 2)}\n`;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const mode = process.argv[2] ?? '--audit';
  let normalizedFiles = 0;
  if (mode === '--normalize') normalizedFiles = normalizeTrackedText();
  const report = auditTrackedText();
  const rendered = render(report);
  if (mode === '--write' || mode === '--normalize') {
    fs.mkdirSync(path.dirname(REPORT), { recursive: true });
    fs.writeFileSync(REPORT, rendered, 'utf8');
  } else if (mode === '--check') {
    if (!fs.existsSync(REPORT)) throw new Error(`Unicode report is missing: ${REPORT}`);
    if (fs.readFileSync(REPORT, 'utf8') !== rendered) throw new Error('Unicode report is stale; run with --write');
  } else if (mode !== '--audit') {
    throw new Error(`unsupported mode: ${mode}`);
  }
  process.stdout.write(rendered);
  if (mode === '--normalize') process.stdout.write(`normalizedTextFiles=${normalizedFiles}\n`);
  if (report.verdict !== 'PASS') process.exitCode = 1;
}
