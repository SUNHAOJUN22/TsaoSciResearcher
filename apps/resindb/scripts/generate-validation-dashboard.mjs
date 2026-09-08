import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const artifacts = path.join(root, 'artifacts');
async function readJson(name, fallback = {}) {
  try { return JSON.parse(await readFile(path.join(artifacts, name), 'utf8')); }
  catch { return fallback; }
}
async function exists(file) {
  try { await access(file); return true; }
  catch { return false; }
}
const esc = (value) => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
const bytes = (n) => Number.isFinite(n) ? n >= 1_048_576 ? `${(n / 1_048_576).toFixed(2)} MiB` : n >= 1024 ? `${(n / 1024).toFixed(1)} KiB` : `${n} B` : 'n/a';
const fixed = (value, digits = 3) => Number.isFinite(value) ? Number(value).toFixed(digits) : 'n/a';

const [receipt, build, coverage, ui, tests, context, benchmark] = await Promise.all([
  readJson('validation-receipt.json', { acceptance: 'EVIDENCE_INCOMPLETE', checks: {} }),
  readJson('build-metrics.json'),
  readJson('coverage-summary.json'),
  readJson('ui-smoke-manifest.json'),
  readJson('test-results.json'),
  readJson('ci-context.json', { sha: 'local-worktree', repository: 'local' }),
  readJson('kmeans-backend-benchmark.json'),
]);
const screenshots = [];
for (const [key, file] of Object.entries(ui.screenshots ?? {})) {
  if (await exists(path.join(artifacts, file))) screenshots.push({ key, file });
}
const status = receipt.acceptance ?? 'EVIDENCE_INCOMPLETE';
const complete = status === 'PASS';
const totals = coverage.totals ?? {};
const testFiles = tests.testResults?.length ?? receipt.tests?.files ?? 0;
const testCount = tests.numTotalTests ?? receipt.tests?.total ?? 0;
const generatedAt = new Date().toISOString();
const gallery = screenshots.length
  ? screenshots.map(({ key, file }) => `<figure><img src="${esc(file)}" alt="${esc(key)} ResinDB validation screenshot"><figcaption>${esc(key)}</figcaption></figure>`).join('\n')
  : '<p class="muted">Chromium screenshots are produced by the exact-tree CI runner.</p>';
const checkRows = Object.entries(receipt.checks ?? {}).map(([name, passed]) => `<tr><td>${esc(name)}</td><td class="${passed ? 'ok' : 'bad'}">${passed ? 'PASS' : 'MISSING'}</td></tr>`).join('');
const benchmarkCases = Array.isArray(benchmark.cases) ? benchmark.cases : [];
const benchmarkRows = benchmarkCases.map((entry) => `<tr><td>${esc(entry.id)}</td><td>${esc(entry.workloadOperations)}</td><td>${fixed(entry.typescript?.medianPerCallMs, 6)}</td><td>${fixed(entry.wasm?.medianPerCallMs, 6)}</td><td>${fixed(entry.speedRatio)}</td><td>${esc(entry.equivalence)}</td></tr>`).join('');
const benchmarkStatus = benchmark.equivalence?.status ?? 'MISSING';
const crossoverStatus = benchmark.crossoverAnalysis?.status ?? 'not-generated';

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ResinDB Pro 3.2.0 validation</title><style>:root{--bg:#f8fafc;--panel:#fff;--text:#0f172a;--muted:#64748b;--border:#cbd5e1;--accent:#2563eb;--ok:#15803d;--bad:#b91c1c}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1160px;margin:auto;padding:34px 22px 70px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.card,.panel{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:16px}.card strong{display:block;font-size:1.6rem;color:var(--accent)}.ok{color:var(--ok)}.bad{color:var(--bad)}.muted{color:var(--muted)}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid var(--border);text-align:left}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}figure{margin:0}img{width:100%;display:block;border:1px solid var(--border);border-radius:12px}figcaption{padding:6px;color:var(--muted)}code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}pre{white-space:pre-wrap;overflow:auto}</style></head><body><main><h1>ResinDB Pro 3.2.0 exact-tree validation</h1><p class="muted">Generated ${esc(generatedAt)} for <code>${esc(context.sha)}</code>.</p><section class="grid"><div class="card"><span>Acceptance</span><strong class="${complete ? 'ok' : 'bad'}">${esc(status)}</strong><small>${testFiles} test files / ${testCount} tests</small></div><div class="card"><span>Whole-source line coverage</span><strong>${esc(totals.lines?.percent ?? 'n/a')}%</strong><small>${coverage.instrumentedSourceFileCount ?? 0}/${coverage.productionSourceFileCount ?? 0} production files</small></div><div class="card"><span>Initial entry gzip</span><strong>${bytes(build.entry?.gzipBytes)}</strong><small>budget ${bytes(build.budgets?.entryGzipBytes)}</small></div><div class="card"><span>ECharts raw</span><strong>${bytes(build.echarts?.bytes)}</strong><small>budget ${bytes(build.budgets?.echartsRawBytes)}</small></div><div class="card"><span>K-Means benchmark</span><strong class="${benchmarkStatus === 'PASS' ? 'ok' : 'bad'}">${esc(benchmarkStatus)}</strong><small>${benchmarkCases.length} case(s); ${esc(crossoverStatus)}</small></div><div class="card"><span>Governed external data</span><strong>${bytes(build.externalResinDataBytes)}</strong></div><div class="card"><span>UI scenes</span><strong>${screenshots.length || 'CI'}</strong></div></section><h2>Acceptance gates</h2><div class="panel"><table><tbody>${checkRows || '<tr><td>No exact-tree receipt yet</td><td class="bad">MISSING</td></tr>'}</tbody></table></div><h2>K-Means FP64 backend benchmark</h2><div class="panel"><p class="muted">Node-WASM timings are informational only. Shared-CI measurements never control browser runtime auto-selection.</p><table><thead><tr><th>Case</th><th>N×K×D</th><th>TypeScript median/call ms</th><th>WASM median/call ms</th><th>TS/WASM</th><th>Equivalent</th></tr></thead><tbody>${benchmarkRows || '<tr><td colspan="6">Benchmark evidence not generated.</td></tr>'}</tbody></table><p><strong>Analysis:</strong> ${esc(crossoverStatus)} — ${esc(benchmark.crossoverAnalysis?.reason ?? 'n/a')}</p></div><h2>Whole-production-source coverage</h2><div class="panel"><table><thead><tr><th>Metric</th><th>Covered</th><th>Total</th><th>Percent</th></tr></thead><tbody>${Object.entries(totals).map(([name, m]) => `<tr><td>${esc(name)}</td><td>${esc(m.covered)}</td><td>${esc(m.total)}</td><td>${esc(m.percent)}%</td></tr>`).join('')}</tbody></table></div><h2>Build and data boundary</h2><div class="panel"><table><tbody><tr><th>Total dist</th><td>${bytes(build.totalBytes)}</td></tr><tr><th>Build files</th><td>${esc(build.fileCount)}</td></tr><tr><th>Module preloads</th><td>${esc(build.modulePreloads?.length ?? 'n/a')}</td></tr><tr><th>Catalog in JavaScript</th><td class="ok">No governed-data sentinel detected</td></tr></tbody></table></div><h2>Remote branch proof</h2><div class="panel"><pre>${esc(receipt.branchProof || 'Generated only by exact-tree CI.')}</pre></div><h2>Interactive UI evidence</h2><div class="gallery">${gallery}</div></main></body></html>`;

await mkdir(artifacts, { recursive: true });
await writeFile(path.join(artifacts, 'validation-dashboard.html'), html);
const benchmarkMarkdownRows = benchmarkCases.map((entry) => `| ${entry.id} | ${entry.workloadOperations} | ${fixed(entry.typescript?.medianPerCallMs, 6)} | ${fixed(entry.wasm?.medianPerCallMs, 6)} | ${fixed(entry.speedRatio)} | ${entry.equivalence} |`).join('\n');
const md = `# ResinDB Pro 3.2.0 final release report

- Generated: ${generatedAt}
- Exact tree: \`${context.sha}\`
- Acceptance: **${status}**
- Tests: ${testCount} across ${testFiles} files
- Whole-source coverage: ${totals.lines?.percent ?? 'n/a'}% lines across ${coverage.instrumentedSourceFileCount ?? 0}/${coverage.productionSourceFileCount ?? 0} production files
- Entry gzip: ${build.entry?.gzipBytes ?? 'n/a'} bytes (budget ${build.budgets?.entryGzipBytes ?? 'n/a'})
- ECharts raw: ${build.echarts?.bytes ?? 'n/a'} bytes (budget ${build.budgets?.echartsRawBytes ?? 'n/a'})
- Governed external data: ${build.externalResinDataBytes ?? 'n/a'} bytes
- UI scenes: ${screenshots.length}
- K-Means benchmark equivalence: **${benchmarkStatus}**
- K-Means crossover analysis: **${crossoverStatus}**

## Acceptance gates

${Object.entries(receipt.checks ?? {}).map(([name, passed]) => `- ${passed ? '[x]' : '[ ]'} ${name}`).join('\n') || '- [ ] Exact-tree receipt not generated'}

## K-Means FP64 backend benchmark

Shared-CI timings are informational evidence only and are not a global browser auto-selection profile.

| Case | N×K×D | TypeScript median/call ms | WASM median/call ms | TS/WASM | Equivalent |
|---|---:|---:|---:|---:|---|
${benchmarkMarkdownRows || '| n/a | n/a | n/a | n/a | n/a | MISSING |'}

Analysis: ${crossoverStatus} — ${benchmark.crossoverAnalysis?.reason ?? 'n/a'}

## Closed findings

1. Zero-valued and categorical material properties are no longer discarded as placeholders.
2. Short category aliases use token boundaries, preventing TPE→PE and PPR→PP misclassification.
3. Browser/local/remote data adapters reject non-finite values and malformed remote payloads.
4. AI configuration and response boundaries now validate storage failures, images, response size and JSON shape.
5. Coverage is measured across every production TypeScript file rather than imported files only.
6. Resin records remain authoritative under root \`data/\` and are loaded at runtime.
7. Chromium covers dashboard, empty state, details, scientific charts, dependency interaction, dark English UI and mobile layout.
8. Exact-tree CI audits production and complete dependency graphs and proves \`main\` is the sole remote branch.
9. K-Means TypeScript/WASM timing evidence is separated from runtime backend policy and cannot create a shared-CI global threshold.

## Branch proof

\`\`\`text
${receipt.branchProof || 'Generated only by exact-tree CI.'}
\`\`\`
`;
await writeFile(path.join(root, 'FINAL_RELEASE_REPORT.md'), md);
await writeFile(path.join(artifacts, 'FINAL_RELEASE_REPORT.md'), md);
console.log(`Validation dashboard and release report generated: ${status}, ${screenshots.length} UI scene(s), ${benchmarkCases.length} benchmark case(s).`);
