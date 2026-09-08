import { jsPDF } from 'jspdf';
import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fitSingleLineFontSize } from './report-layout.mjs';

const root = path.resolve(import.meta.dirname, '..');
const artifacts = path.join(root, 'artifacts');
await mkdir(artifacts, { recursive: true });
const readJson = async (name, fallback = {}) => { try { return JSON.parse(await readFile(path.join(artifacts, name), 'utf8')); } catch { return fallback; } };
const exists = async (file) => { try { await access(file); return true; } catch { return false; } };
const [receipt, build, coverage, ui, tests, context, benchmark] = await Promise.all([
  readJson('validation-receipt.json', { acceptance: 'EVIDENCE_INCOMPLETE', checks: {} }),
  readJson('build-metrics.json'),
  readJson('coverage-summary.json'),
  readJson('ui-smoke-manifest.json'),
  readJson('test-results.json'),
  readJson('ci-context.json', { sha: 'local-worktree' }),
  readJson('kmeans-backend-benchmark.json'),
]);
const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4', compress: true });
const W = doc.internal.pageSize.getWidth();
const H = doc.internal.pageSize.getHeight();
function header(title, subtitle) { doc.setFillColor(15, 23, 42); doc.rect(0, 0, W, 74, 'F'); doc.setTextColor(255); doc.setFont('helvetica', 'bold'); doc.setFontSize(22); doc.text(title, 34, 34); doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.text(subtitle, 34, 54); doc.setTextColor(15, 23, 42); }
function footer(page) { doc.setDrawColor(203, 213, 225); doc.line(30, H - 28, W - 30, H - 28); doc.setFontSize(8); doc.setTextColor(100); doc.text(`ResinDB Pro 3.2.0 | page ${page}`, 34, H - 14); }
function metric(x, y, w, label, value, note = '') {
  const valueText = String(value);
  const valueMaxWidth = w - 24;
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(203, 213, 225);
  doc.roundedRect(x, y, w, 76, 8, 8, 'FD');
  doc.setFontSize(9);
  doc.setTextColor(100);
  doc.text(label, x + 12, y + 18);
  doc.setFont('helvetica', 'bold');
  const valueFontSize = fitSingleLineFontSize(
    valueText,
    valueMaxWidth,
    (_text, fontSize) => {
      doc.setFontSize(fontSize);
      return doc.getTextWidth(_text);
    },
  );
  doc.setFontSize(valueFontSize);
  doc.setTextColor(37, 99, 235);
  doc.text(valueText, x + 12, y + 45);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(100);
  if (note) doc.text(note, x + 12, y + 63, { maxWidth: valueMaxWidth });
}

header('ResinDB Pro 3.2.0 final validation', 'Exact-tree scientific data, computation, browser interaction and release evidence');
const totals = coverage.totals ?? {};
const testCount = tests.numTotalTests ?? receipt.tests?.total ?? 0;
const testFiles = tests.testResults?.length ?? receipt.tests?.files ?? 0;
metric(34, 100, 165, 'Acceptance', receipt.acceptance ?? 'INCOMPLETE', `${testFiles} files / ${testCount} tests`);
metric(211, 100, 165, 'Whole-source lines', `${totals.lines?.percent ?? 'n/a'}%`, `${coverage.instrumentedSourceFileCount ?? 0}/${coverage.productionSourceFileCount ?? 0} files`);
metric(388, 100, 165, 'Initial entry gzip', `${build.entry?.gzipBytes ?? 'n/a'} B`, `budget ${build.budgets?.entryGzipBytes ?? 'n/a'} B`);
metric(565, 100, 165, 'K-Means benchmark', benchmark.equivalence?.status ?? 'MISSING', `${benchmark.cases?.length ?? 0} case(s); timing informational`);
doc.setFontSize(13); doc.setFont('helvetica', 'bold'); doc.text('Acceptance gates', 34, 210); doc.setFont('helvetica', 'normal'); doc.setFontSize(10);
let y = 236;
const checks = Object.entries(receipt.checks ?? {});
for (const [name, passed] of checks.length ? checks : [['exactTreeReceipt', false]]) {
  doc.setFillColor(passed ? 21 : 185, passed ? 128 : 28, passed ? 61 : 28); doc.circle(41, y - 3, 3, 'F'); doc.setTextColor(15, 23, 42); doc.text(`${passed ? 'PASS' : 'MISSING'}  ${name}`, 52, y, { maxWidth: 350 }); y += 25;
}
doc.setFont('helvetica', 'bold'); doc.text('Trust-boundary improvements', 430, 210); doc.setFont('helvetica', 'normal');
const findings = [
  'Zero and categorical values remain valid scientific data.',
  'Short aliases use token boundaries; malformed remote products are rejected.',
  'AI storage, image, response-size and JSON-shape boundaries are validated.',
  'Coverage now instruments every production TypeScript source file.',
  'Production and full dependency audits are release gates.',
  `K-Means benchmark: ${benchmark.equivalence?.status ?? 'MISSING'} equivalence; ${benchmark.crossoverAnalysis?.status ?? 'no crossover conclusion'}.`,
  'Shared-CI timing is evidence only and cannot control browser auto-selection.',
];
y = 236;
for (const finding of findings) { doc.setFillColor(37, 99, 235); doc.circle(437, y - 3, 3, 'F'); doc.setTextColor(15, 23, 42); doc.text(finding, 448, y, { maxWidth: 330 }); y += 30; }
footer(1);

const shots = Object.entries(ui.screenshots ?? {});
let page = 1;
for (const [name, file] of shots) {
  const filePath = path.join(artifacts, file);
  if (!(await exists(filePath))) continue;
  doc.addPage('a4', 'landscape'); page += 1;
  header(`UI evidence: ${name}`, `Source: ${file} | commit ${context.sha ?? 'local-worktree'}`);
  const data = await readFile(filePath);
  const props = doc.getImageProperties(data);
  const maxW = W - 68; const maxH = H - 130; const ratio = Math.min(maxW / props.width, maxH / props.height);
  const iw = props.width * ratio; const ih = props.height * ratio;
  doc.addImage(data, 'PNG', (W - iw) / 2, 92, iw, ih, undefined, 'FAST'); footer(page);
}
const out = path.join(artifacts, 'ResinDB-Pro-3.2.0-Final-Validation-Report.pdf');
await writeFile(out, Buffer.from(doc.output('arraybuffer')));
console.log(`PDF validation report generated: ${out}, ${page} page(s).`);
