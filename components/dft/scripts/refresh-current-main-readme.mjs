#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const P = {
  slug: 'tsao-dft', title: 'TsaoDFT Skill',
  readmes: [{ path: 'README.md', lang: 'zh' }, { path: 'README_EN.md', lang: 'en' }],
  zh: {
    tagline: '从 Kohn–Sham 合同、周期几何与引擎身份到可证伪电子结构证据',
    stages: [['科学问题', '体系、可观测量与精度'], ['结构与周期性', '晶胞、PBC 与邻居表'], ['方法合同', '泛函、基组/截断与 SCF'], ['数值验收', '能量、力、应力与等价'], ['证据分级', 'L0–L3、哈希与责任边界']],
    boundary: '软件门禁只验证控制面、参考数值与证据合同；Gaussian、VASP、QE、CP2K 等外部引擎未在此自动执行，保持 EXTERNAL_HOLD。',
  },
  en: {
    tagline: 'From Kohn–Sham contracts, periodic geometry and engine identity to falsifiable electronic-structure evidence',
    stages: [['Scientific question', 'System, observables and accuracy'], ['Structure and periodicity', 'Cell, PBC and neighbour lists'], ['Method contract', 'Functional, basis/cutoff and SCF'], ['Numerical acceptance', 'Energy, forces, stress and parity'], ['Evidence grading', 'L0–L3, hashes and authority']],
    boundary: 'Software gates validate the control plane, reference numerics and evidence contracts only; external engines such as Gaussian, VASP, QE and CP2K are not executed here and remain EXTERNAL_HOLD.',
  },
  formulas: [
    '[-½∇² + V_eff[n]] ψᵢ = εᵢ ψᵢ',
    'n* = argminₙ ‖A(s − n)‖₂',
    '|ΔE| ≤ τ_E ∧ maxᵢ ‖ΔFᵢ‖₂ ≤ τ_F',
  ],
  code: ['skills/tsao-structure-prep/scripts/neighbor_list.py', 'scripts/build_release_acceptance.py', 'scripts/capture_compute_contract_evidence.py'],
};
const START = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:START -->';
const END = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:END -->';
const BAD = ['\uFFFD', 'Ã', 'Â', 'â€', '锟斤拷'];
const nfc = (v) => v.normalize('NFC');
const esc = (v) => v.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');

function svg(lang) {
  const t = P[lang];
  const zh = lang === 'zh';
  const cards = t.stages.map(([h, d], i) => {
    const x = 44 + 310 * i;
    return `<g><rect x="${x}" y="230" width="270" height="212" rx="28" fill="url(#card)" stroke="#60a5fa" stroke-width="2"/><text x="${x + 22}" y="280" class="stage">${esc(h)}</text><text x="${x + 22}" y="324" class="detail">${esc(d)}</text><text x="${x + 22}" y="394" class="index">0${i + 1}</text></g>`;
  });
  const arrows = t.stages.slice(0, -1).map((_, i) => `<path d="M ${44 + 310 * i + 275} 336 H ${44 + 310 * i + 304}" stroke="#38bdf8" stroke-width="5" marker-end="url(#arrow)"/>`);
  const eq = P.formulas.map((f, i) => `<g><rect x="${44 + 505 * i}" y="522" width="465" height="128" rx="22" fill="#091426" stroke="#c084fc" stroke-width="2"/><text x="${66 + 505 * i}" y="575" class="formula">${esc(f)}</text><text x="${66 + 505 * i}" y="619" class="micro">${zh ? '代码合同' : 'CODE CONTRACT'} 0${i + 1}</text></g>`);
  const badge = zh ? 'AI辅助概念设计 · 非科学数据 · 公式对应软件合同而非外部引擎结果' : 'AI-ASSISTED CONCEPTUAL DESIGN · NOT EXTERNAL-ENGINE DATA';
  return nfc(`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
<title id="title">${esc(P.title)} ${zh ? '当前主线验收架构' : 'current-main acceptance architecture'}</title><desc id="desc">${esc(t.tagline)}. ${esc(t.boundary)}</desc>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#020617"/><stop offset=".5" stop-color="#0b2452"/><stop offset="1" stop-color="#2e1065"/></linearGradient><linearGradient id="card"><stop offset="0" stop-color="#12345f"/><stop offset="1" stop-color="#20164c"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#38bdf8"/></marker><style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei","PingFang SC","Noto Sans",Arial,sans-serif;fill:#eff6ff}.title{font-size:54px;font-weight:800}.subtitle{font-size:24px;fill:#bae6fd}.stage{font-size:24px;font-weight:750}.detail{font-size:17px;fill:#c7d2fe}.index{font-size:58px;font-weight:800;fill:#1d4ed8}.formula{font-family:"STIX Two Math","Cambria Math","Noto Sans Math","Noto Sans CJK SC",sans-serif;font-size:19px;fill:#f3e8ff}.micro{font-size:14px;letter-spacing:2px;fill:#67e8f9}.boundary{font-size:18px;fill:#dbeafe}.badge{font-size:16px;fill:#93c5fd}</style></defs>
<rect width="1600" height="900" fill="url(#bg)"/><circle cx="1390" cy="92" r="125" fill="#3b82f6" opacity=".16"/><circle cx="210" cy="790" r="170" fill="#a855f7" opacity=".12"/><text x="48" y="88" class="title">${esc(P.title)}</text><text x="48" y="132" class="subtitle">${esc(t.tagline)}</text><text x="48" y="184" class="badge">${esc(badge)}</text>${arrows.join('')}${cards.join('')}${eq.join('')}<rect x="44" y="710" width="1512" height="104" rx="24" fill="#071124" stroke="#334155"/><text x="76" y="756" class="micro">${zh ? '资格边界' : 'QUALIFICATION BOUNDARY'}</text><text x="76" y="790" class="boundary">${esc(t.boundary)}</text><text x="48" y="866" class="micro">CURRENT MAIN · EXACT TREE · FINITE NUMERICS · L0–L3 EVIDENCE</text>
</svg>
`);
}

function section(lang) {
  const zh = lang === 'zh'; const t = P[lang];
  const heading = zh ? '当前 `main`：代码—数学—证据闭环' : 'Current `main`: code–mathematics–evidence loop';
  const strategy = zh ? ['先冻结结构、晶胞、周期性和单位，再生成引擎输入。', 'SCF、能量、力和应力只有在有限、收敛且方法身份完整时才可验收。', '探测、模板与解析器结果不得升级为真实 DFT 计算证据。', '任何新提交都会使旧 SHA 的六小时软件证据失效。'] : ['Freeze structure, cell, periodicity and units before generating engine input.', 'Accept SCF, energy, forces and stress only when finite, converged and method identity is complete.', 'Discovery, templates and parser outputs must not be promoted to real DFT execution evidence.', 'Any new commit invalidates six-hour software evidence bound to an older SHA.'];
  return nfc([START, `## ${heading}`, '', `<p align="center"><img src="docs/current-main/${P.slug}-current-main-${lang}.svg" width="100%" alt="${heading}"></p>`, '', `> ${zh ? '该图由当前代码合同生成，是概念设计，不是电子结构运行数据。' : 'This figure is generated from current code contracts and is conceptual documentation, not electronic-structure run data.'}`, '', `### ${zh ? '核心数理合同' : 'Core mathematical contracts'}`, '', P.formulas.map((f) => `$$\n${f}\n$$`).join('\n\n'), '', `### ${zh ? '使用策略' : 'Usage strategy'}`, '', ...strategy.map((x, i) => `${i + 1}. ${x}`), '', `> **${zh ? '责任边界' : 'Responsibility boundary'}：** ${t.boundary}`, '', `${zh ? '执行提示词' : 'Execution prompt'}: [SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md](docs/SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md)`, END].join('\n'));
}

function inject(original, generated) {
  const q = (v) => v.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&');
  const re = new RegExp(`${q(START)}[\\s\\S]*?${q(END)}`, 'u'); const base = nfc(`${original.trimEnd()}\n`);
  return nfc(re.test(base) ? `${base.replace(re, () => generated).trimEnd()}\n` : `${base}\n${generated}\n`);
}
function annex() { const rows = P.code.map((x) => `| \`${x}\` | current implementation anchor |`).join('\n'); return nfc(`# ${P.title} current-main acceptance / 当前主线验收

Generated by \`scripts/refresh-current-main-readme.mjs\`. 本附录记录当前 \`main\` 的代码—数学—证据关系。

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
function audit(label, text, failures) {
  if (text !== text.normalize('NFC')) failures.push(`${label}: not NFC-normalized`);
  for (const b of BAD) if (text.includes(b)) failures.push(`${label}: probable mojibake ${JSON.stringify(b)}`);
  if (label.endsWith('.svg')) { if (!/<svg\b[^>]*viewBox="0 0 1600 900"[^>]*role="img"/u.test(text)) failures.push(`${label}: invalid root`); if (!/<title\b[^>]*>[^<]+<\/title>/u.test(text) || !/<desc\b[^>]*>[^<]+<\/desc>/u.test(text)) failures.push(`${label}: title/desc missing`); if (/<script\b|<foreignObject\b|\son[a-z]+\s*=|javascript:|(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/iu.test(text)) failures.push(`${label}: active/external content`); }
}
const write = process.argv.includes('--write'); const failures = [];
const out = new Map([[`docs/current-main/${P.slug}-current-main-zh.svg`, svg('zh')], [`docs/current-main/${P.slug}-current-main-en.svg`, svg('en')], ['docs/CURRENT_MAIN_ACCEPTANCE.md', annex()]]);
for (const p of P.code) if (!existsSync(join(ROOT, p))) failures.push(`missing code anchor: ${p}`);
for (const r of P.readmes) { const p = join(ROOT, r.path); if (!existsSync(p)) failures.push(`missing README: ${r.path}`); else out.set(r.path, inject(readFileSync(p, 'utf8'), section(r.lang))); }
if (write && !failures.length) for (const [p, c] of out) { const a = join(ROOT, p); mkdirSync(dirname(a), { recursive: true }); writeFileSync(a, c, 'utf8'); }
for (const [p, e] of out) { const a = join(ROOT, p); if (!existsSync(a)) failures.push(`missing generated output: ${p}`); else { const c = readFileSync(a, 'utf8'); if (c !== e) failures.push(`stale generated output: ${p}`); audit(p, c, failures); } }
const report = { schemaVersion: 'current-main-readme-visual-audit-2.0.0', project: P.title, generatedFiles: [...out.keys()].sort(), codeAnchors: P.code, failures, acceptance: failures.length ? 'FAIL' : 'PASS' };
mkdirSync(join(ROOT, 'artifacts/current-main'), { recursive: true }); writeFileSync(join(ROOT, 'artifacts/current-main/readme-visual-audit.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8'); console.log(JSON.stringify(report, null, 2)); if (failures.length) process.exitCode = 1;
