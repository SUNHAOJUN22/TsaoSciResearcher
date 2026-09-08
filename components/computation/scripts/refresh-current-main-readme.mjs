#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const PROFILE = {
  slug: 'tsao-scicomputation',
  title: 'TsaoSciComputation',
  readmes: [
    { path: 'README.md', language: 'en' },
    { path: 'README.zh-CN.md', language: 'zh' },
  ],
  taglineZh: '从计算合同、执行身份与收敛门到可重复多尺度交付',
  taglineEn: 'From calculation contracts, execution identity and convergence gates to reproducible multiscale delivery',
  stagesZh: [
    ['问题与合同', '目标、方法、数据与容差'],
    ['执行身份', '求解器、输入与环境哈希'],
    ['资源准入', 'CPU/GPU/许可证与工作目录'],
    ['数值验收', '解析、收敛、守恒与等价'],
    ['证据交付', 'UQ、适用域与责任主体'],
  ],
  stagesEn: [
    ['Question and contract', 'Objective, method, data, tolerances'],
    ['Execution identity', 'Solver, input and environment hashes'],
    ['Resource admission', 'CPU/GPU/licence and working directory'],
    ['Numerical acceptance', 'Parsing, convergence, conservation, parity'],
    ['Evidence delivery', 'UQ, applicability and authority'],
  ],
  formulas: [
    'admit(C) = 1_schema · 1_identity · 1_inputs · 1_resources · 1_policy',
    'H_bundle = SHA256(B_solver ∥ B_inputs ∥ B_env ∥ B_contract ∥ B_reference)',
    'δ_rel = |y − y_ref| / max(|y_ref|, ε) ≤ τ_eq',
  ],
  codePaths: [
    'tsao_computation/adapters/base.py',
    'tsao_computation/execution/runner.py',
    'tsao_computation/validation/numerical.py',
  ],
  boundaryZh: '仓库是计算控制面与资格框架；第三方 DFT、MD、CFD、FEM 和流程求解器保持 EXTERNAL_HOLD。',
  boundaryEn: 'The repository is a computation control plane and qualification framework; third-party DFT, MD, CFD, FEM and process solvers remain EXTERNAL_HOLD.',
};

const START = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:START -->';
const END = '<!-- CURRENT_MAIN_ACCEPTANCE_V2:END -->';
const badTokens = ['\uFFFD', 'Ã', 'Â', 'â€', '锟斤拷'];

function escapeXml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function cleanText(label, text, failures) {
  if (text !== text.normalize('NFC')) failures.push(`${label}: text is not NFC-normalized`);
  for (const token of badTokens) {
    if (text.includes(token)) failures.push(`${label}: probable mojibake ${JSON.stringify(token)}`);
  }
  for (const character of text) {
    const code = character.codePointAt(0);
    if (code === undefined) continue;
    if ((code < 32 && !['\n', '\r', '\t'].includes(character)) || code === 127) {
      failures.push(`${label}: forbidden control U+${code.toString(16).padStart(4, '0')}`);
      break;
    }
  }
}

function svg(language) {
  const zh = language === 'zh';
  const subtitle = zh ? PROFILE.taglineZh : PROFILE.taglineEn;
  const stages = zh ? PROFILE.stagesZh : PROFILE.stagesEn;
  const boundary = zh ? PROFILE.boundaryZh : PROFILE.boundaryEn;
  const badge = zh
    ? 'AI辅助概念设计 · 非科学数据 · 公式对应软件合同而非运行结果'
    : 'AI-ASSISTED CONCEPTUAL DESIGN · NOT SCIENTIFIC DATA';
  const cards = [];
  const arrows = [];
  stages.forEach(([heading, detail], index) => {
    const x = 45 + index * 310;
    cards.push(
      `<g><rect x="${x}" y="228" width="270" height="214" rx="28" `
      + 'fill="url(#card)" stroke="#22d3ee" stroke-width="2"/>'
      + `<text x="${x + 24}" y="278" class="stage">${escapeXml(heading)}</text>`
      + `<text x="${x + 24}" y="322" class="detail">${escapeXml(detail)}</text>`
      + `<text x="${x + 24}" y="392" class="index">0${index + 1}</text></g>`,
    );
    if (index < stages.length - 1) {
      arrows.push(
        `<path d="M ${x + 274} 335 H ${x + 304}" stroke="#38bdf8" `
        + 'stroke-width="5" marker-end="url(#arrow)"/>',
      );
    }
  });
  const formulaCards = PROFILE.formulas.map((formula, index) => {
    const x = 45 + index * 505;
    const label = zh ? '代码合同' : 'CODE CONTRACT';
    return `<g><rect x="${x}" y="520" width="465" height="130" rx="22" `
      + 'fill="#08152f" stroke="#a78bfa" stroke-width="2"/>'
      + `<text x="${x + 24}" y="574" class="formula">${escapeXml(formula)}</text>`
      + `<text x="${x + 24}" y="620" class="micro">${label} 0${index + 1}</text></g>`;
  });
  const title = `${PROFILE.title} ${zh ? '当前主线验收架构' : 'current-main acceptance architecture'}`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
  <title id="title">${escapeXml(title)}</title>
  <desc id="desc">${escapeXml(subtitle)}. ${escapeXml(boundary)}</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#020617"/><stop offset="0.5" stop-color="#082f49"/><stop offset="1" stop-color="#1e1b4b"/>
    </linearGradient>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0c4a6e"/><stop offset="1" stop-color="#172554"/>
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/>
    </marker>
    <style>
      text{font-family:"Noto Sans CJK SC","Microsoft YaHei","PingFang SC","Noto Sans",Arial,sans-serif;fill:#e5f2ff}
      .title{font-size:54px;font-weight:800}.subtitle{font-size:24px;fill:#a5f3fc}.stage{font-size:25px;font-weight:750}
      .detail{font-size:17px;fill:#c7d2fe}.index{font-size:58px;font-weight:800;fill:#155e75}
      .formula{font-family:"STIX Two Math","Cambria Math","Noto Sans Math","Noto Sans CJK SC",sans-serif;font-size:19px;fill:#ede9fe}
      .micro{font-size:14px;letter-spacing:2px;fill:#67e8f9}.boundary{font-size:18px;fill:#dbeafe}.badge{font-size:16px;fill:#93c5fd}
    </style>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <circle cx="1390" cy="90" r="122" fill="#0ea5e9" opacity="0.16"/>
  <circle cx="220" cy="790" r="170" fill="#7c3aed" opacity="0.12"/>
  <text x="48" y="88" class="title">${escapeXml(PROFILE.title)}</text>
  <text x="48" y="132" class="subtitle">${escapeXml(subtitle)}</text>
  <text x="48" y="184" class="badge">${escapeXml(badge)}</text>
  ${arrows.join('')}
  ${cards.join('')}
  ${formulaCards.join('')}
  <rect x="45" y="710" width="1510" height="104" rx="24" fill="#071124" stroke="#334155"/>
  <text x="76" y="756" class="micro">${zh ? '资格边界' : 'QUALIFICATION BOUNDARY'}</text>
  <text x="76" y="790" class="boundary">${escapeXml(boundary)}</text>
  <text x="48" y="866" class="micro">CURRENT MAIN · EXACT TREE · FINITE NUMERICS · BILINGUAL EVIDENCE</text>
</svg>
`;
}

function readmeBlock(language) {
  const zh = language === 'zh';
  const image = `docs/current-main/${PROFILE.slug}-current-main-${language}.svg`;
  const heading = zh
    ? '当前 `main`：代码—数学—证据闭环'
    : 'Current `main`: code–mathematics–evidence loop';
  const intro = zh
    ? '本节由仓库脚本根据当前代码合同生成；图像是文档概念设计，不是求解器或实验结果。'
    : 'This section is generated from current code contracts; the visual is conceptual documentation, not solver or experimental output.';
  const strategy = zh
    ? [
        '先运行永久 CI，再运行 current-main 精确树验收。',
        '数值、容差和不确定度入口必须是有限实数，Boolean 不得充当 0/1。',
        '执行身份、输入、环境、参考与合同共同进入证据哈希。',
        '任何新提交都会使旧 SHA 的六小时证据失效。',
      ]
    : [
        'Run permanent CI before exact-tree current-main qualification.',
        'Scientific values, tolerances and uncertainties must be finite reals; Boolean is not 0/1 evidence.',
        'Execution identity, inputs, environment, references and contracts enter the evidence hash.',
        'Any new commit invalidates six-hour evidence bound to an older SHA.',
      ];
  const formulas = PROFILE.formulas.map((formula) => `$$\n${formula}\n$$`).join('\n\n');
  return [
    START,
    `## ${heading}`,
    '',
    `<p align="center"><img src="${image}" width="100%" alt="${heading}"></p>`,
    '',
    `> ${intro}`,
    '',
    `### ${zh ? '核心数理合同' : 'Core mathematical contracts'}`,
    '',
    formulas,
    '',
    `### ${zh ? '使用策略' : 'Usage strategy'}`,
    '',
    ...strategy.map((item, index) => `${index + 1}. ${item}`),
    '',
    `> **${zh ? '责任边界' : 'Responsibility boundary'}：** ${zh ? PROFILE.boundaryZh : PROFILE.boundaryEn}`,
    '',
    `${zh ? '执行提示词' : 'Execution prompt'}：[`
      + 'SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md]('
      + 'docs/SIX_REPOSITORY_PARALLEL_6H_ACCEPTANCE_PROMPT_V2.md)',
    END,
  ].join('\n');
}

function inject(original, block) {
  const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&');
  const pattern = new RegExp(`${escapeRegex(START)}[\\s\\S]*?${escapeRegex(END)}`, 'u');
  const normalized = `${original.trimEnd()}\n`;
  if (pattern.test(normalized)) {
    return `${normalized.replace(pattern, () => block).trimEnd()}\n`;
  }
  return `${normalized}\n${block}\n`;
}

function annex() {
  const rows = PROFILE.codePaths
    .map((path) => `| \`${path}\` | current implementation anchor |`)
    .join('\n');
  return `# ${PROFILE.title} current-main acceptance / 当前主线验收

This annex is generated by \`scripts/refresh-current-main-readme.mjs\`.
本附录由仓库脚本生成，记录当前 \`main\` 的代码—数学—证据关系。

## Formula-to-code anchors / 公式到代码锚点

| Implementation path / 实现路径 | Contract |
|---|---|
${rows}

## Acceptance identity / 验收身份

$$
H_accept = SHA256(code ∥ docs ∥ visuals ∥ tests ∥ environment)
$$

PASS is valid only for the immutable SHA tested by the workflow. Any later commit requires a new run.
PASS 只对工作流实际测试的不可变 SHA 有效；任何后续提交都必须重新运行。

## Boundary / 边界

- ${PROFILE.boundaryEn}
- ${PROFILE.boundaryZh}
`;
}

function validateSvg(label, text, failures) {
  const root = text.match(/<svg\b([^>]*)>/u)?.[1] ?? '';
  if (!root) failures.push(`${label}: missing SVG root`);
  if (!/\bviewBox="0 0 1600 900"/u.test(root)) failures.push(`${label}: invalid viewBox`);
  if (!/\brole="img"/u.test(root)) failures.push(`${label}: role=img is required`);
  if (!/<title\b[^>]*>[^<]+<\/title>/u.test(text)) failures.push(`${label}: title is required`);
  if (!/<desc\b[^>]*>[^<]+<\/desc>/u.test(text)) failures.push(`${label}: desc is required`);
  if (/<script\b|<foreignObject\b|\son[a-z]+\s*=|javascript:/iu.test(text)) {
    failures.push(`${label}: active SVG content is forbidden`);
  }
  if (/(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/iu.test(text)) {
    failures.push(`${label}: external SVG resource is forbidden`);
  }
}

function main() {
  const write = process.argv.includes('--write');
  const check = process.argv.includes('--check') || !write;
  const failures = [];
  const outputs = new Map([
    [`docs/current-main/${PROFILE.slug}-current-main-zh.svg`, svg('zh')],
    [`docs/current-main/${PROFILE.slug}-current-main-en.svg`, svg('en')],
    ['docs/CURRENT_MAIN_ACCEPTANCE.md', annex()],
  ]);

  for (const path of PROFILE.codePaths) {
    if (!existsSync(join(ROOT, path))) failures.push(`missing code anchor: ${path}`);
  }
  for (const spec of PROFILE.readmes) {
    const absolute = join(ROOT, spec.path);
    if (!existsSync(absolute)) {
      failures.push(`missing README: ${spec.path}`);
      continue;
    }
    const original = readFileSync(absolute, 'utf8');
    outputs.set(spec.path, inject(original, readmeBlock(spec.language)));
  }

  if (write && failures.length === 0) {
    for (const [relativePath, content] of outputs) {
      const absolute = join(ROOT, relativePath);
      mkdirSync(dirname(absolute), { recursive: true });
      writeFileSync(absolute, content, 'utf8');
    }
  }

  if (check || write) {
    for (const [relativePath, expected] of outputs) {
      const absolute = join(ROOT, relativePath);
      if (!existsSync(absolute)) {
        failures.push(`missing generated output: ${relativePath}`);
        continue;
      }
      const actual = readFileSync(absolute, 'utf8');
      if (actual !== expected) failures.push(`stale generated output: ${relativePath}`);
      cleanText(relativePath, actual, failures);
      if (relativePath.endsWith('.svg')) validateSvg(relativePath, actual, failures);
    }
  }

  const report = {
    schemaVersion: 'current-main-readme-visual-audit-2.0.0',
    project: PROFILE.title,
    generatedFiles: [...outputs.keys()].sort(),
    codeAnchors: PROFILE.codePaths,
    failures,
    acceptance: failures.length ? 'FAIL' : 'PASS',
  };
  const artifact = join(ROOT, 'artifacts/current-main/readme-visual-audit.json');
  mkdirSync(dirname(artifact), { recursive: true });
  writeFileSync(artifact, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(report, null, 2));
  if (failures.length) process.exitCode = 1;
}

main();
