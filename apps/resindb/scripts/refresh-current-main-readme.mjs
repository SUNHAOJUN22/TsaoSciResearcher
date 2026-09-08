#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const P = {
  slug: 'resindb', title: 'ResinDB Pro',
  readmes: [{ path: 'README.md', lang: 'bi' }, { path: 'README.zh-CN.md', lang: 'zh' }, { path: 'README.en.md', lang: 'en' }],
  zh: {
    tagline: '从可追溯树脂数据、有限数值与计算能力探测到可验证科学可视化',
    stages: [['数据合同', 'Schema、来源、状态与单位'], ['数值内核', '有限性、尺度与相似度'], ['计算调度', 'Worker、WASM、GPU 与降级'], ['科学图形', '标签、finished 与非空画布'], ['导出与审计', '语言、哈希、回执与边界']],
    boundary: 'ResinDB Pro 是本地优先的科学数据与分析工作台，不是经认证的 LIMS/ERP、商业力场、工业牌号放行系统或自动科研批准器。',
  },
  en: {
    tagline: 'From traceable resin data, finite numerics and compute-capability probes to verifiable scientific visualization',
    stages: [['Data contract', 'Schema, source, status and units'], ['Numerical core', 'Finiteness, scaling and similarity'], ['Compute dispatch', 'Workers, WASM, GPU and fallback'], ['Scientific figures', 'Labels, finished events and nonblank canvas'], ['Export and audit', 'Language, hashes, receipts and boundaries']],
    boundary: 'ResinDB Pro is a local-first scientific data and analysis workbench, not a certified LIMS/ERP, commercial force field, industrial grade-release system or automatic scientific approval engine.',
  },
  formulas: [
    'C_figure = C_finite ∧ C_labeled ∧ C_finished ∧ C_nonblank',
    'd_M(x, μ) = √((x − μ)ᵀ Σ⁻¹ (x − μ))',
    'u_c² = u_data² + u_model² + u_scale²',
  ],
  code: ['src/data/dataContract.ts', 'src/services/mathUtils.ts', 'src/compute/capabilityProbe.ts'],
};
const START = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:START -->';
const END = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:END -->';
const BAD = [
  String.fromCodePoint(0xfffd),
  String.fromCodePoint(0x00c3),
  String.fromCodePoint(0x00c2),
  String.fromCodePoint(0x00e2, 0x20ac),
  String.fromCodePoint(0x951f, 0x65a4, 0x62f7),
];
const nfc = (v) => v.normalize('NFC');
const esc = (v) => v.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');

function svg(lang) {
  const t = P[lang]; const zh = lang === 'zh';
  const cards = t.stages.map(([h, d], i) => { const x = 44 + 310 * i; return `<g><rect x="${x}" y="230" width="270" height="212" rx="28" fill="url(#card)" stroke="#22d3ee" stroke-width="2"/><text x="${x + 22}" y="280" class="stage">${esc(h)}</text><text x="${x + 22}" y="324" class="detail">${esc(d)}</text><text x="${x + 22}" y="394" class="index">0${i + 1}</text></g>`; });
  const arrows = t.stages.slice(0, -1).map((_, i) => `<path d="M ${319 + 310 * i} 336 H ${348 + 310 * i}" stroke="#67e8f9" stroke-width="5" marker-end="url(#arrow)"/>`);
  const eq = P.formulas.map((f, i) => `<g><rect x="${44 + 505 * i}" y="522" width="465" height="128" rx="22" fill="#071b2e" stroke="#34d399" stroke-width="2"/><text x="${66 + 505 * i}" y="575" class="formula">${esc(f)}</text><text x="${66 + 505 * i}" y="619" class="micro">${zh ? '图形与数值合同' : 'FIGURE AND NUMERICAL CONTRACT'} 0${i + 1}</text></g>`);
  const badge = zh ? 'AI辅助概念设计 · 非科学数据 · 中英文渲染分别验证' : 'AI-ASSISTED CONCEPTUAL DESIGN · NOT SCIENTIFIC DATA · LOCALES VERIFIED SEPARATELY';
  return nfc(`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc"><title id="title">${esc(P.title)} ${zh ? '当前主线验收架构' : 'current-main acceptance architecture'}</title><desc id="desc">${esc(t.tagline)}. ${esc(t.boundary)}</desc><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#020617"/><stop offset=".48" stop-color="#083344"/><stop offset="1" stop-color="#064e3b"/></linearGradient><linearGradient id="card"><stop offset="0" stop-color="#0e3b57"/><stop offset="1" stop-color="#075244"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#67e8f9"/></marker><style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei","PingFang SC","Noto Sans",Arial,sans-serif;fill:#ecfeff}.title{font-size:54px;font-weight:800}.subtitle{font-size:24px;fill:#a5f3fc}.stage{font-size:24px;font-weight:750}.detail{font-size:17px;fill:#ccfbf1}.index{font-size:58px;font-weight:800;fill:#0e7490}.formula{font-family:"STIX Two Math","Cambria Math","Noto Sans Math","Noto Sans CJK SC",sans-serif;font-size:18px;fill:#d1fae5}.micro{font-size:13px;letter-spacing:1.7px;fill:#67e8f9}.boundary{font-size:18px;fill:#dbeafe}.badge{font-size:16px;fill:#99f6e4}</style></defs><rect width="1600" height="900" fill="url(#bg)"/><circle cx="1390" cy="92" r="125" fill="#06b6d4" opacity=".15"/><circle cx="210" cy="790" r="170" fill="#10b981" opacity=".12"/><text x="48" y="88" class="title">${esc(P.title)}</text><text x="48" y="132" class="subtitle">${esc(t.tagline)}</text><text x="48" y="184" class="badge">${esc(badge)}</text>${arrows.join('')}${cards.join('')}${eq.join('')}<rect x="44" y="710" width="1512" height="104" rx="24" fill="#061a24" stroke="#334155"/><text x="76" y="756" class="micro">${zh ? '资格边界' : 'QUALIFICATION BOUNDARY'}</text><text x="76" y="790" class="boundary">${esc(t.boundary)}</text><text x="48" y="866" class="micro">CURRENT MAIN · STRICT UTF-8 · NONBLANK FIGURES · COMPUTE CAPABILITY PROBE · BILINGUAL EVIDENCE</text></svg>
`);
}

function localizedSection(lang) {
  const zh = lang === 'zh'; const t = P[lang]; const heading = zh ? '当前 `main`：数据—计算—图形—证据闭环' : 'Current `main`: data–compute–figure–evidence loop';
  const strategy = zh ? ['导入时先验证 Schema、来源类型、记录状态、单位和有限值。', '相似度、回归、聚类与 UQ 必须显式处理缺失数据、尺度和适用域。', '浏览器图形只有在 ECharts finished、Canvas 非空且标签完整时才可导出。', '中文与英文 README、SVG 和界面字符串分别验收，禁止语言串扰和乱码。'] : ['Validate Schema, source type, record status, units and finite values at import.', 'Similarity, regression, clustering and UQ must expose missing-data, scaling and applicability handling.', 'Browser figures are exportable only after ECharts finished, nonblank canvas and complete labels.', 'Chinese and English README, SVG and UI strings are qualified separately; language leakage and mojibake are rejected.'];
  return nfc([START, `## ${heading}`, '', `<p align="center"><img src="docs/current-main/${P.slug}-current-main-${lang}.svg" width="100%" alt="${heading}"></p>`, '', `> ${zh ? '该图由当前代码合同生成，是科学软件概念设计，不是树脂数据库测量结果。' : 'This figure is generated from current code contracts and is scientific-software conceptual design, not measured resin-database output.'}`, '', `### ${zh ? '核心数理合同' : 'Core mathematical contracts'}`, '', P.formulas.map((f) => `$$\n${f}\n$$`).join('\n\n'), '', `### ${zh ? '使用策略' : 'Usage strategy'}`, '', ...strategy.map((x, i) => `${i + 1}. ${x}`), '', `> **${zh ? '责任边界' : 'Responsibility boundary'}：** ${t.boundary}`, '', `${zh ? '执行提示词' : 'Execution prompt'}: [SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md](docs/SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md)`, END].join('\n'));
}

function bilingualSection() {
  return nfc([START, '## Current `main` / 当前主线：数据—计算—图形—证据闭环', '', '<p align="center">', `  <img src="docs/current-main/${P.slug}-current-main-zh.svg" width="49%" alt="ResinDB Pro 当前主线中文数据计算图形证据架构">`, `  <img src="docs/current-main/${P.slug}-current-main-en.svg" width="49%" alt="ResinDB Pro current-main English data compute figure evidence architecture">`, '</p>', '', '> 中文与英文视觉资产分别生成、分别进行 UTF-8、语言隔离、SVG 安全、可访问性与公式合同验证。', '> Chinese and English visual assets are generated separately and independently checked for UTF-8, language isolation, SVG safety, accessibility and formula contracts.', '', '### Mathematical contracts / 数理合同', '', P.formulas.map((f) => `$$\n${f}\n$$`).join('\n\n'), '', `- ${P.zh.boundary}`, `- ${P.en.boundary}`, '', '[SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md](docs/SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md)', END].join('\n'));
}
function inject(original, generated) { const q = (v) => v.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&'); const re = new RegExp(`${q(START)}[\\s\\S]*?${q(END)}`, 'u'); const base = nfc(`${original.trimEnd()}\n`); return nfc(re.test(base) ? `${base.replace(re, () => generated).trimEnd()}\n` : `${base}\n${generated}\n`); }
function annex() { const rows = P.code.map((x) => `| \`${x}\` | current implementation anchor |`).join('\n'); return nfc(`# ${P.title} current-main acceptance / 当前主线验收

Generated by \`scripts/refresh-current-main-readme.mjs\`. 本附录记录当前 \`main\` 的数据—计算—图形—证据关系。

| Implementation path / 实现路径 | Contract |
|---|---|
${rows}

$$
H_accept = SHA256(code ∥ docs ∥ visuals ∥ tests ∥ environment)
$$

PASS is valid only for the immutable tested SHA. PASS 只对实际测试的不可变 SHA 有效。

- ${P.en.boundary}
- ${P.zh.boundary}
`); }
function audit(label, text, failures) { if (text !== text.normalize('NFC')) failures.push(`${label}: not NFC-normalized`); for (const b of BAD) if (text.includes(b)) failures.push(`${label}: probable mojibake ${JSON.stringify(b)}`); if (label.endsWith('.svg')) { if (!/<svg\b[^>]*viewBox="0 0 1600 900"[^>]*role="img"/u.test(text)) failures.push(`${label}: invalid root`); if (!/<title\b[^>]*>[^<]+<\/title>/u.test(text) || !/<desc\b[^>]*>[^<]+<\/desc>/u.test(text)) failures.push(`${label}: title/desc missing`); if (/<script\b|<foreignObject\b|\son[a-z]+\s*=|javascript:|(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/iu.test(text)) failures.push(`${label}: active/external content`); } }
const write = process.argv.includes('--write'); const failures = []; const out = new Map([[`docs/current-main/${P.slug}-current-main-zh.svg`, svg('zh')], [`docs/current-main/${P.slug}-current-main-en.svg`, svg('en')], ['docs/CURRENT_MAIN_ACCEPTANCE.md', annex()]]);
for (const p of P.code) if (!existsSync(join(ROOT, p))) failures.push(`missing code anchor: ${p}`); for (const r of P.readmes) { const p = join(ROOT, r.path); if (!existsSync(p)) failures.push(`missing README: ${r.path}`); else out.set(r.path, inject(readFileSync(p, 'utf8'), r.lang === 'bi' ? bilingualSection() : localizedSection(r.lang))); }
if (write && !failures.length) for (const [p, c] of out) { const a = join(ROOT, p); mkdirSync(dirname(a), { recursive: true }); writeFileSync(a, c, 'utf8'); }
for (const [p, e] of out) { const a = join(ROOT, p); if (!existsSync(a)) failures.push(`missing generated output: ${p}`); else { const c = readFileSync(a, 'utf8'); if (c !== e) failures.push(`stale generated output: ${p}`); audit(p, c, failures); } }
const report = { schemaVersion: 'current-main-readme-visual-audit-2.0.0', project: P.title, generatedFiles: [...out.keys()].sort(), codeAnchors: P.code, failures, acceptance: failures.length ? 'FAIL' : 'PASS' }; mkdirSync(join(ROOT, 'artifacts/current-main'), { recursive: true }); writeFileSync(join(ROOT, 'artifacts/current-main/readme-visual-audit.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8'); console.log(JSON.stringify(report, null, 2)); if (failures.length) process.exitCode = 1;
