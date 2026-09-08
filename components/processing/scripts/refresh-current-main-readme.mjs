#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const PROFILE = {
  slug: 'tsao-processing',
  title: 'TSAO Process Intelligence OS',
  readmes: [
    { path: 'README.md', language: 'en' },
    { path: 'README.zh-CN.md', language: 'zh' },
  ],
  taglineZh: '从机理、守恒与自适应积分到可发布工艺包证据',
  taglineEn: 'From mechanisms, conservation and adaptive integration to publishable process-package evidence',
  stagesZh: [
    ['工艺包对象', 'Schema、单位与证据谱系'],
    ['动力学网络', '基元反应、链矩与状态量'],
    ['数值积分', 'DOPRI5、事件与守恒'],
    ['辨识与 UQ', 'Fisher、灵敏度与适用域'],
    ['规范发布', 'Wheel、源码快照与责任边界'],
  ],
  stagesEn: [
    ['Process package', 'Schema, units and evidence lineage'],
    ['Kinetic network', 'Elementary steps, chain moments, states'],
    ['Numerical integration', 'DOPRI5, events and conservation'],
    ['Identification and UQ', 'Fisher, sensitivity, applicability'],
    ['Canonical publication', 'Wheel, source snapshot, authority'],
  ],
  formulas: [
    'dN/dt = F_in z − F_out x + V νᵀ r',
    'e = ‖y₅ − y₄‖ / (atol + rtol max(‖yₙ‖, ‖y₅‖))',
    'I(θ) = J(θ)ᵀ W J(θ)',
  ],
  codePaths: [
    'tsao/process_package.py',
    'skills/epdm/kinetics.py',
    'skills/poe/kinetics.py',
  ],
  boundaryZh: '当前交付是软件参考数值与工艺研发框架；科学、工程、HSE、客户与工业性能批准均保持 NOT_EVALUATED。',
  boundaryEn: 'The deliverable is a software-reference numerical and process-development framework; scientific, engineering, HSE, customer and industrial-performance approvals remain NOT_EVALUATED.',
};

const START = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:START -->';
const END = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:END -->';
const BAD = ['\uFFFD', 'Ã', 'Â', 'â€', '锟斤拷'];

function esc(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function normalized(value) {
  return value.normalize('NFC');
}

function visual(language) {
  const zh = language === 'zh';
  const stages = zh ? PROFILE.stagesZh : PROFILE.stagesEn;
  const subtitle = zh ? PROFILE.taglineZh : PROFILE.taglineEn;
  const boundary = zh ? PROFILE.boundaryZh : PROFILE.boundaryEn;
  const badge = zh
    ? 'AI辅助概念设计 · 非科学数据 · 公式对应软件合同而非运行结果'
    : 'AI-ASSISTED CONCEPTUAL DESIGN · NOT SCIENTIFIC DATA';
  const cards = stages.map(([name, detail], index) => {
    const x = 44 + 310 * index;
    return `<g><rect x="${x}" y="230" width="270" height="212" rx="28" fill="url(#card)" stroke="#34d399" stroke-width="2"/>`
      + `<text x="${x + 24}" y="280" class="stage">${esc(name)}</text>`
      + `<text x="${x + 24}" y="324" class="detail">${esc(detail)}</text>`
      + `<text x="${x + 24}" y="394" class="index">0${index + 1}</text></g>`;
  });
  const arrows = stages.slice(0, -1).map((_, index) => {
    const x = 44 + 310 * index;
    return `<path d="M ${x + 275} 336 H ${x + 304}" stroke="#5eead4" stroke-width="5" marker-end="url(#arrow)"/>`;
  });
  const equations = PROFILE.formulas.map((formula, index) => {
    const x = 44 + 505 * index;
    return `<g><rect x="${x}" y="522" width="465" height="128" rx="22" fill="#071b25" stroke="#a78bfa" stroke-width="2"/>`
      + `<text x="${x + 22}" y="575" class="formula">${esc(formula)}</text>`
      + `<text x="${x + 22}" y="619" class="micro">${zh ? '代码合同' : 'CODE CONTRACT'} 0${index + 1}</text></g>`;
  });
  const title = `${PROFILE.title} ${zh ? '当前主线验收架构' : 'current-main acceptance architecture'}`;
  return normalized(`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
  <title id="title">${esc(title)}</title>
  <desc id="desc">${esc(subtitle)}. ${esc(boundary)}</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#020617"/><stop offset="0.48" stop-color="#052e2b"/><stop offset="1" stop-color="#24123f"/></linearGradient>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#064e3b"/><stop offset="1" stop-color="#172554"/></linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#5eead4"/></marker>
    <style>
      text{font-family:"Noto Sans CJK SC","Microsoft YaHei","PingFang SC","Noto Sans",Arial,sans-serif;fill:#ecfeff}
      .title{font-size:52px;font-weight:800}.subtitle{font-size:24px;fill:#99f6e4}.stage{font-size:25px;font-weight:750}.detail{font-size:17px;fill:#d1fae5}
      .index{font-size:58px;font-weight:800;fill:#0f766e}.formula{font-family:"STIX Two Math","Cambria Math","Noto Sans Math","Noto Sans CJK SC",sans-serif;font-size:19px;fill:#ede9fe}
      .micro{font-size:14px;letter-spacing:2px;fill:#67e8f9}.boundary{font-size:18px;fill:#dbeafe}.badge{font-size:16px;fill:#93c5fd}
    </style>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/><circle cx="1390" cy="90" r="124" fill="#10b981" opacity="0.14"/><circle cx="210" cy="792" r="170" fill="#8b5cf6" opacity="0.12"/>
  <text x="48" y="88" class="title">${esc(PROFILE.title)}</text><text x="48" y="132" class="subtitle">${esc(subtitle)}</text><text x="48" y="184" class="badge">${esc(badge)}</text>
  ${arrows.join('')}${cards.join('')}${equations.join('')}
  <rect x="44" y="710" width="1512" height="104" rx="24" fill="#06131d" stroke="#334155"/><text x="76" y="756" class="micro">${zh ? '资格边界' : 'QUALIFICATION BOUNDARY'}</text><text x="76" y="790" class="boundary">${esc(boundary)}</text>
  <text x="48" y="866" class="micro">CURRENT MAIN · EXACT TREE · FINITE NUMERICS · BILINGUAL EVIDENCE</text>
</svg>
`);
}

function block(language) {
  const zh = language === 'zh';
  const heading = zh ? '当前 `main`：代码—数学—证据闭环' : 'Current `main`: code–mathematics–evidence loop';
  const image = `docs/current-main/${PROFILE.slug}-current-main-${language}.svg`;
  const strategy = zh
    ? ['从 Schema、单位与证据等级开始，不从漂亮图表反推实现。', '动力学、链矩和积分器只接受有限且量纲一致的输入。', '先跑 canonical publication 和完整 CI，再执行精确 SHA 的六小时活动测试。', '新提交会使旧 SHA 的长期测试回执自动失效。']
    : ['Start from Schema, units and evidence classes rather than inferring implementation from visuals.', 'Kinetics, chain moments and integrators accept only finite dimensionally compatible inputs.', 'Run canonical publication and full CI before six-hour active testing of an exact SHA.', 'Any new commit invalidates long-duration evidence bound to an older SHA.'];
  const equations = PROFILE.formulas.map((formula) => `$$\n${formula}\n$$`).join('\n\n');
  return normalized([
    START,
    `## ${heading}`,
    '',
    `<p align="center"><img src="${image}" width="100%" alt="${heading}"></p>`,
    '',
    `> ${zh ? '该图由当前代码合同生成，是文档概念设计，不是实验、装置或工业性能数据。' : 'The figure is generated from current code contracts and is conceptual documentation, not experimental, plant or industrial-performance data.'}`,
    '',
    `### ${zh ? '核心数理合同' : 'Core mathematical contracts'}`,
    '',
    equations,
    '',
    `### ${zh ? '使用策略' : 'Usage strategy'}`,
    '',
    ...strategy.map((item, index) => `${index + 1}. ${item}`),
    '',
    `> **${zh ? '责任边界' : 'Responsibility boundary'}：** ${zh ? PROFILE.boundaryZh : PROFILE.boundaryEn}`,
    '',
    `${zh ? '执行提示词' : 'Execution prompt'}: [SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md](docs/SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md)`,
    END,
  ].join('\n'));
}

function inject(original, generated) {
  const quote = (value) => value.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&');
  const pattern = new RegExp(`${quote(START)}[\\s\\S]*?${quote(END)}`, 'u');
  const base = normalized(`${original.trimEnd()}\n`);
  return normalized(pattern.test(base) ? `${base.replace(pattern, () => generated).trimEnd()}\n` : `${base}\n${generated}\n`);
}

function annex() {
  const rows = PROFILE.codePaths.map((path) => `| \`${path}\` | current implementation anchor |`).join('\n');
  return normalized(`# ${PROFILE.title} current-main acceptance / 当前主线验收

Generated by \`scripts/refresh-current-main-readme.mjs\`. 本附录记录当前 \`main\` 的代码—数学—证据关系。

| Implementation path / 实现路径 | Contract |
|---|---|
${rows}

$$
H_accept = SHA256(code ∥ docs ∥ visuals ∥ tests ∥ environment)
$$

PASS is valid only for the immutable SHA tested by the workflow. PASS 只对工作流实际测试的不可变 SHA 有效。

- ${PROFILE.boundaryEn}
- ${PROFILE.boundaryZh}
`);
}

function validate(label, text, failures) {
  if (text !== text.normalize('NFC')) failures.push(`${label}: not NFC-normalized`);
  for (const token of BAD) if (text.includes(token)) failures.push(`${label}: probable mojibake ${JSON.stringify(token)}`);
  for (const character of text) {
    const code = character.codePointAt(0);
    if (code !== undefined && ((code < 32 && !['\n', '\r', '\t'].includes(character)) || code === 127)) {
      failures.push(`${label}: forbidden control U+${code.toString(16).padStart(4, '0')}`);
      break;
    }
  }
  if (label.endsWith('.svg')) {
    if (!/<svg\b[^>]*viewBox="0 0 1600 900"[^>]*role="img"/u.test(text)) failures.push(`${label}: invalid SVG root contract`);
    if (!/<title\b[^>]*>[^<]+<\/title>/u.test(text) || !/<desc\b[^>]*>[^<]+<\/desc>/u.test(text)) failures.push(`${label}: title/desc missing`);
    if (/<script\b|<foreignObject\b|\son[a-z]+\s*=|javascript:|(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/iu.test(text)) failures.push(`${label}: active or external SVG content`);
  }
}

const write = process.argv.includes('--write');
const failures = [];
const outputs = new Map([
  [`docs/current-main/${PROFILE.slug}-current-main-zh.svg`, visual('zh')],
  [`docs/current-main/${PROFILE.slug}-current-main-en.svg`, visual('en')],
  ['docs/CURRENT_MAIN_ACCEPTANCE.md', annex()],
]);
for (const path of PROFILE.codePaths) if (!existsSync(join(ROOT, path))) failures.push(`missing code anchor: ${path}`);
for (const spec of PROFILE.readmes) {
  const absolute = join(ROOT, spec.path);
  if (!existsSync(absolute)) failures.push(`missing README: ${spec.path}`);
  else outputs.set(spec.path, inject(readFileSync(absolute, 'utf8'), block(spec.language)));
}
if (write && failures.length === 0) {
  for (const [path, content] of outputs) {
    const absolute = join(ROOT, path);
    mkdirSync(dirname(absolute), { recursive: true });
    writeFileSync(absolute, content, 'utf8');
  }
}
for (const [path, expected] of outputs) {
  const absolute = join(ROOT, path);
  if (!existsSync(absolute)) failures.push(`missing generated output: ${path}`);
  else {
    const actual = readFileSync(absolute, 'utf8');
    if (actual !== expected) failures.push(`stale generated output: ${path}`);
    validate(path, actual, failures);
  }
}
const report = { schemaVersion: 'current-main-readme-visual-audit-2.0.0', project: PROFILE.title, generatedFiles: [...outputs.keys()].sort(), codeAnchors: PROFILE.codePaths, failures, acceptance: failures.length ? 'FAIL' : 'PASS' };
const artifact = join(ROOT, 'reports/runtime/CURRENT_MAIN_README_VISUAL_AUDIT.json');
mkdirSync(dirname(artifact), { recursive: true });
writeFileSync(artifact, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(report, null, 2));
if (failures.length) process.exitCode = 1;
