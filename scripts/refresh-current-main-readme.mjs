#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const P = {
  slug: 'tsao-researcher', title: 'TsaoSciResearcher',
  readmes: [{ path: 'README.md', lang: 'en' }, { path: 'README.zh-CN.md', lang: 'zh' }],
  zh: {
    tagline: '从科学问题、证据分级与量纲合同到可证伪的跨尺度研究路线',
    stages: [['问题结构化', '可观测量、条件与决策'], ['能力路由', '模型合同与外部执行边界'], ['证据控制', '来源、冲突与适用域'], ['尺度桥与 UQ', '可辨识性、传播与校准'], ['回执与验收', '哈希、责任主体与证伪']],
    boundary: '该仓库生成研究策略、合同、证据控制与外部执行回执；automatic_approval=false，不能替代专家、实验或第三方求解器资格。',
  },
  en: {
    tagline: 'From scientific questions, evidence grading and dimensional contracts to falsifiable multiscale research routes',
    stages: [['Question structuring', 'Observables, conditions and decisions'], ['Capability routing', 'Model contracts and execution boundaries'], ['Evidence control', 'Sources, conflicts and applicability'], ['Scale bridge and UQ', 'Identifiability, propagation, calibration'], ['Receipts and acceptance', 'Hashes, authority and falsification']],
    boundary: 'The repository generates research strategies, contracts, evidence controls and external-execution receipts; automatic_approval=false and it does not replace experts, experiments or third-party solver qualification.',
  },
  formulas: [
    'G = min(g_quantity, g_applicability, g_evidence, g_identifiability, g_bridge)',
    'Σ_y = J Σ_x Jᵀ + Σ_model + Σ_scale',
    'H_receipt = SHA256(contract ∥ input ∥ engine ∥ environment ∥ result)',
  ],
  code: ['tsao_researcher/mathematical_contracts.py', 'tsao_researcher/scientific_quality.py', 'tsao_researcher/receipts.py'],
};
const START = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:START -->';
const END = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:END -->';
const BAD = ['\uFFFD', 'Ã', 'Â', 'â€', '锟斤拷'];
const nfc = (v) => v.normalize('NFC');
const esc = (v) => v.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');

function svg(lang) {
  const t = P[lang]; const zh = lang === 'zh';
  const cards = t.stages.map(([h, d], i) => { const x = 44 + 310 * i; return `<g><rect x="${x}" y="230" width="270" height="212" rx="28" fill="url(#card)" stroke="#f59e0b" stroke-width="2"/><text x="${x + 22}" y="280" class="stage">${esc(h)}</text><text x="${x + 22}" y="324" class="detail">${esc(d)}</text><text x="${x + 22}" y="394" class="index">0${i + 1}</text></g>`; });
  const arrows = t.stages.slice(0, -1).map((_, i) => `<path d="M ${319 + 310 * i} 336 H ${348 + 310 * i}" stroke="#fbbf24" stroke-width="5" marker-end="url(#arrow)"/>`);
  const eq = P.formulas.map((f, i) => `<g><rect x="${44 + 505 * i}" y="522" width="465" height="128" rx="22" fill="#1b1320" stroke="#c084fc" stroke-width="2"/><text x="${66 + 505 * i}" y="575" class="formula">${esc(f)}</text><text x="${66 + 505 * i}" y="619" class="micro">${zh ? '决策合同' : 'DECISION CONTRACT'} 0${i + 1}</text></g>`);
  const badge = zh ? 'AI辅助概念设计 · 非科学数据 · 不构成自动科学批准' : 'AI-ASSISTED CONCEPTUAL DESIGN · NOT AUTOMATIC SCIENTIFIC APPROVAL';
  return nfc(`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc"><title id="title">${esc(P.title)} ${zh ? '当前主线验收架构' : 'current-main acceptance architecture'}</title><desc id="desc">${esc(t.tagline)}. ${esc(t.boundary)}</desc><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#09090b"/><stop offset=".5" stop-color="#3b1d0b"/><stop offset="1" stop-color="#2e1065"/></linearGradient><linearGradient id="card"><stop offset="0" stop-color="#4a2507"/><stop offset="1" stop-color="#28164d"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#fbbf24"/></marker><style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei","PingFang SC","Noto Sans",Arial,sans-serif;fill:#fff7ed}.title{font-size:54px;font-weight:800}.subtitle{font-size:24px;fill:#fde68a}.stage{font-size:24px;font-weight:750}.detail{font-size:17px;fill:#ffedd5}.index{font-size:58px;font-weight:800;fill:#92400e}.formula{font-family:"STIX Two Math","Cambria Math","Noto Sans Math","Noto Sans CJK SC",sans-serif;font-size:18px;fill:#f3e8ff}.micro{font-size:14px;letter-spacing:2px;fill:#fcd34d}.boundary{font-size:18px;fill:#e9d5ff}.badge{font-size:16px;fill:#fdba74}</style></defs><rect width="1600" height="900" fill="url(#bg)"/><circle cx="1390" cy="92" r="125" fill="#f59e0b" opacity=".14"/><circle cx="210" cy="790" r="170" fill="#a855f7" opacity=".12"/><text x="48" y="88" class="title">${esc(P.title)}</text><text x="48" y="132" class="subtitle">${esc(t.tagline)}</text><text x="48" y="184" class="badge">${esc(badge)}</text>${arrows.join('')}${cards.join('')}${eq.join('')}<rect x="44" y="710" width="1512" height="104" rx="24" fill="#140e18" stroke="#57534e"/><text x="76" y="756" class="micro">${zh ? '资格边界' : 'QUALIFICATION BOUNDARY'}</text><text x="76" y="790" class="boundary">${esc(t.boundary)}</text><text x="48" y="866" class="micro">CURRENT MAIN · EVIDENCE FIRST · DIMENSIONAL CONTRACTS · AUTOMATIC APPROVAL FALSE</text></svg>
`);
}
function section(lang) {
  const zh = lang === 'zh'; const t = P[lang]; const heading = zh ? '当前 `main`：问题—合同—证据—回执闭环' : 'Current `main`: question–contract–evidence–receipt loop';
  const strategy = zh ? ['先定义决策、可观测量、条件与量纲，再选择模型或工具。', '将声明分为来源证据、计算证据和推断；冲突不得静默合并。', '尺度桥必须显式报告可辨识性、传播假设和不确定度预算。', '外部执行只有在回执身份完整时才可进入验收；新提交使旧 SHA 证据失效。'] : ['Define the decision, observables, conditions and dimensions before selecting models or tools.', 'Separate sourced, computed and inferred claims; evidence conflicts must not be silently merged.', 'Scale bridges must report identifiability, propagation assumptions and uncertainty budgets.', 'External execution enters acceptance only with a complete receipt identity; new commits invalidate old-SHA evidence.'];
  return nfc([START, `## ${heading}`, '', `<p align="center"><img src="docs/current-main/${P.slug}-current-main-${lang}.svg" width="100%" alt="${heading}"></p>`, '', `> ${zh ? '该图由当前代码合同生成，是研究控制架构概念图，不是论文、实验或自动批准结果。' : 'This figure is generated from current code contracts and is a research-control concept, not a paper, experiment or automatic approval result.'}`, '', `### ${zh ? '核心数理合同' : 'Core mathematical contracts'}`, '', P.formulas.map((f) => `$$\n${f}\n$$`).join('\n\n'), '', `### ${zh ? '使用策略' : 'Usage strategy'}`, '', ...strategy.map((x, i) => `${i + 1}. ${x}`), '', `> **${zh ? '责任边界' : 'Responsibility boundary'}：** ${t.boundary}`, '', `${zh ? '执行提示词' : 'Execution prompt'}: [SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md](docs/SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md)`, END].join('\n'));
}
function inject(original, generated) { const q = (v) => v.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&'); const re = new RegExp(`${q(START)}[\\s\\S]*?${q(END)}`, 'u'); const base = nfc(`${original.trimEnd()}\n`); return nfc(re.test(base) ? `${base.replace(re, () => generated).trimEnd()}\n` : `${base}\n${generated}\n`); }
function annex() { const rows = P.code.map((x) => `| \`${x}\` | current implementation anchor |`).join('\n'); return nfc(`# ${P.title} current-main acceptance / 当前主线验收

Generated by \`scripts/refresh-current-main-readme.mjs\`. 本附录记录当前 \`main\` 的问题—合同—证据—回执关系。

| Implementation path / 实现路径 | Contract |
|---|---|
${rows}

$$
H_accept = SHA256(code ∥ docs ∥ visuals ∥ tests ∥ environment)
$$

PASS is valid only for the immutable tested SHA; automatic scientific approval remains false.
PASS 只对实际测试的不可变 SHA 有效；自动科学批准始终为 false。

- ${P.en.boundary}
- ${P.zh.boundary}
`); }
function audit(label, text, failures) { if (text !== text.normalize('NFC')) failures.push(`${label}: not NFC-normalized`); for (const b of BAD) if (text.includes(b)) failures.push(`${label}: probable mojibake ${JSON.stringify(b)}`); if (label.endsWith('.svg')) { if (!/<svg\b[^>]*viewBox="0 0 1600 900"[^>]*role="img"/u.test(text)) failures.push(`${label}: invalid root`); if (!/<title\b[^>]*>[^<]+<\/title>/u.test(text) || !/<desc\b[^>]*>[^<]+<\/desc>/u.test(text)) failures.push(`${label}: title/desc missing`); if (/<script\b|<foreignObject\b|\son[a-z]+\s*=|javascript:|(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/iu.test(text)) failures.push(`${label}: active/external content`); } }
const write = process.argv.includes('--write'); const failures = []; const out = new Map([[`docs/current-main/${P.slug}-current-main-zh.svg`, svg('zh')], [`docs/current-main/${P.slug}-current-main-en.svg`, svg('en')], ['docs/CURRENT_MAIN_ACCEPTANCE.md', annex()]]);
for (const p of P.code) if (!existsSync(join(ROOT, p))) failures.push(`missing code anchor: ${p}`); for (const r of P.readmes) { const p = join(ROOT, r.path); if (!existsSync(p)) failures.push(`missing README: ${r.path}`); else out.set(r.path, inject(readFileSync(p, 'utf8'), section(r.lang))); }
if (write && !failures.length) for (const [p, c] of out) { const a = join(ROOT, p); mkdirSync(dirname(a), { recursive: true }); writeFileSync(a, c, 'utf8'); }
for (const [p, e] of out) { const a = join(ROOT, p); if (!existsSync(a)) failures.push(`missing generated output: ${p}`); else { const c = readFileSync(a, 'utf8'); if (c !== e) failures.push(`stale generated output: ${p}`); audit(p, c, failures); } }
const report = { schemaVersion: 'current-main-readme-visual-audit-2.0.0', project: P.title, generatedFiles: [...out.keys()].sort(), codeAnchors: P.code, failures, acceptance: failures.length ? 'FAIL' : 'PASS' }; mkdirSync(join(ROOT, 'artifacts/current-main'), { recursive: true }); writeFileSync(join(ROOT, 'artifacts/current-main/readme-visual-audit.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8'); console.log(JSON.stringify(report, null, 2)); if (failures.length) process.exitCode = 1;
