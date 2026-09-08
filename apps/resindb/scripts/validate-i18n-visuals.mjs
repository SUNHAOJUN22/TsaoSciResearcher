#!/usr/bin/env node

import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from 'node:fs';
import { basename, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const ARTIFACT_ROOT = join(ROOT, 'artifacts');
const TEXT_EXTENSIONS = new Set([
  '.css',
  '.html',
  '.js',
  '.json',
  '.md',
  '.mjs',
  '.svg',
  '.ts',
  '.tsx',
  '.txt',
  '.yaml',
  '.yml',
]);
const SCAN_ROOTS = ['src', 'scripts', 'docs', 'data', 'schemas'];
const EXCLUDED_DIRECTORIES = new Set([
  '.git',
  'artifacts',
  'coverage',
  'dist',
  'node_modules',
]);
const MOJIBAKE_PATTERN = /\uFFFD|\u00C3[\u0080-\u00BF]|\u00C2[\u0080-\u00BF]|\u00E2[\u0080-\u00BF]{1,2}|\u00F0\u0178|\u00EF\u00BB\u00BF|\u951F\u65A4\u62F7/u;
const HAN_PATTERN = /\p{Script=Han}/u;
const CJK_FONT_PATTERN = /Noto Sans (?:SC|CJK)|Microsoft YaHei|PingFang SC|WenQuanYi Micro Hei/u;
const LOCALIZED_VISUAL_PATTERN = /(?:docs\/localized-vision\/|docs\/current-main\/).+-(?:zh|en)\.svg$/u;
const REQUIRED_LOCALIZED_KEYS = [
  'chart_feature_importance',
  'desc_feature_importance',
  'materialDurabilityForecast',
  'predictiveTrends',
  'resinCapacityForecast',
  'sysHealthNoEvents',
  'sysHealthSubtitle',
];
const README_PATHS = ['README.md', 'README.zh-CN.md', 'README.en.md'];
const fatalUtf8Decoder = new TextDecoder('utf-8', { fatal: true });

const failures = [];
const warnings = [];

function repositoryPath(path) {
  return relative(ROOT, path).split(sep).join('/');
}

function walk(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && EXCLUDED_DIRECTORIES.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(path));
    else files.push(path);
  }
  return files.sort();
}

function hasForbiddenControlCharacter(value) {
  for (const character of value) {
    const codePoint = character.codePointAt(0);
    if (codePoint === undefined) continue;
    if (
      (codePoint >= 0 && codePoint <= 8)
      || codePoint === 11
      || codePoint === 12
      || (codePoint >= 14 && codePoint <= 31)
      || codePoint === 127
    ) {
      return true;
    }
  }
  return false;
}

function readUtf8(path, options = {}) {
  const bytes = readFileSync(path);
  const label = repositoryPath(path);
  let text;
  try {
    text = fatalUtf8Decoder.decode(bytes);
  } catch (error) {
    failures.push(`${label}: invalid UTF-8 byte sequence (${String(error)})`);
    text = bytes.toString('utf8');
  }
  if (text.includes('\uFFFD')) failures.push(`${label}: invalid UTF-8 replacement character`);
  if (MOJIBAKE_PATTERN.test(text)) failures.push(`${label}: probable mojibake sequence`);
  if (hasForbiddenControlCharacter(text)) failures.push(`${label}: forbidden control character`);
  if (text.charCodeAt(0) === 0xfeff) warnings.push(`${label}: UTF-8 BOM present`);
  if (options.requireNfc && text !== text.normalize('NFC')) {
    failures.push(`${label}: user-facing text is not NFC-normalized`);
  }
  return text;
}

function propertyName(node) {
  if (ts.isIdentifier(node) || ts.isStringLiteralLike(node) || ts.isNumericLiteral(node)) {
    return node.text;
  }
  return null;
}

function exportedLocaleMap(path, variableName) {
  const sourceText = readUtf8(path);
  const source = ts.createSourceFile(
    repositoryPath(path),
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  );
  let rootObject = null;
  for (const statement of source.statements) {
    if (!ts.isVariableStatement(statement)) continue;
    for (const declaration of statement.declarationList.declarations) {
      if (
        ts.isIdentifier(declaration.name)
        && declaration.name.text === variableName
        && declaration.initializer
        && ts.isObjectLiteralExpression(declaration.initializer)
      ) {
        rootObject = declaration.initializer;
      }
    }
  }
  if (!rootObject) {
    failures.push(`${repositoryPath(path)}: ${variableName} object was not found`);
    return { zh: new Map(), en: new Map(), nfkcDifferences: 0 };
  }

  const output = { zh: new Map(), en: new Map(), nfkcDifferences: 0 };
  for (const localeProperty of rootObject.properties) {
    if (!ts.isPropertyAssignment(localeProperty)) continue;
    const locale = propertyName(localeProperty.name);
    if (
      (locale !== 'zh' && locale !== 'en')
      || !ts.isObjectLiteralExpression(localeProperty.initializer)
    ) {
      continue;
    }
    for (const entry of localeProperty.initializer.properties) {
      if (!ts.isPropertyAssignment(entry)) continue;
      const key = propertyName(entry.name);
      if (!key) continue;
      if (!ts.isStringLiteralLike(entry.initializer)) {
        failures.push(
          `${repositoryPath(path)}: ${variableName}.${locale}.${key} must be a string literal`,
        );
        continue;
      }
      const raw = entry.initializer.text;
      if (raw !== raw.normalize('NFC')) {
        failures.push(`${variableName}.${locale}.${key}: value is not NFC-normalized`);
      }
      if (raw !== raw.normalize('NFKC')) output.nfkcDifferences += 1;
      output[locale].set(key, raw.normalize('NFC'));
    }
  }
  return output;
}

function validateLocaleMaps() {
  const translations = exportedLocaleMap(join(ROOT, 'src/config/i18n.ts'), 'translations');
  const overrides = exportedLocaleMap(
    join(ROOT, 'src/config/scientificUiOverrides.ts'),
    'scientificUiOverrides',
  );
  const zhKeys = [...translations.zh.keys()].sort();
  const enKeys = [...translations.en.keys()].sort();
  const missingEnglish = zhKeys.filter((key) => !translations.en.has(key));
  const missingChinese = enKeys.filter((key) => !translations.zh.has(key));
  if (missingEnglish.length) {
    failures.push(`translations.en missing keys: ${JSON.stringify(missingEnglish)}`);
  }
  if (missingChinese.length) {
    failures.push(`translations.zh missing keys: ${JSON.stringify(missingChinese)}`);
  }

  const overrideZhKeys = [...overrides.zh.keys()].sort();
  const overrideEnKeys = [...overrides.en.keys()].sort();
  if (JSON.stringify(overrideZhKeys) !== JSON.stringify(overrideEnKeys)) {
    failures.push('scientificUiOverrides zh/en key sets differ');
  }

  const effectiveZh = new Map([...translations.zh, ...overrides.zh]);
  const effectiveEn = new Map([...translations.en, ...overrides.en]);
  for (const key of REQUIRED_LOCALIZED_KEYS) {
    const zh = effectiveZh.get(key) ?? '';
    const en = effectiveEn.get(key) ?? '';
    if (!HAN_PATTERN.test(zh)) failures.push(`${key}: Chinese UI value lacks Chinese text`);
    if (HAN_PATTERN.test(en)) failures.push(`${key}: English UI value leaks Chinese text`);
    if (MOJIBAKE_PATTERN.test(zh) || MOJIBAKE_PATTERN.test(en)) {
      failures.push(`${key}: localized UI value contains mojibake`);
    }
  }

  return {
    translationKeys: zhKeys.length,
    overrideKeys: overrideZhKeys.length,
    requiredLocalizedKeys: REQUIRED_LOCALIZED_KEYS.length,
    nfkcCompatibilityDifferences:
      translations.nfkcDifferences + overrides.nfkcDifferences,
  };
}

function readmeImageRecords() {
  return README_PATHS.flatMap((relativePath) => {
    const readme = readUtf8(join(ROOT, relativePath), { requireNfc: true });
    const records = [];
    for (const match of readme.matchAll(/!\[([^\n]*?)\]\(([^)\n]+)\)/gu)) {
      records.push({
        readme: relativePath,
        kind: 'markdown',
        alt: match[1].trim(),
        target: match[2].trim().split(/[?#]/u, 1)[0],
      });
    }
    for (const match of readme.matchAll(/<img\b([^>]*)>/giu)) {
      const attributes = match[1];
      const src = attributes.match(/\bsrc=["']([^"']+)["']/iu)?.[1] ?? '';
      const alt = attributes.match(/\balt=["']([^"']*)["']/iu)?.[1] ?? '';
      records.push({
        readme: relativePath,
        kind: 'html',
        alt: alt.trim(),
        target: src.trim().split(/[?#]/u, 1)[0],
      });
    }
    return records.filter((record) => record.target);
  });
}

function validateLocalizedReadmeSeparation(records) {
  let localizedReferences = 0;
  for (const record of records) {
    if (!record.alt) {
      failures.push(`${record.readme}: ${record.kind} image has empty alt text`);
    }
    if (!LOCALIZED_VISUAL_PATTERN.test(record.target)) continue;
    localizedReferences += 1;
    if (record.readme === 'README.zh-CN.md' && /-en\.svg$/u.test(record.target)) {
      failures.push(`${record.readme}: English localized visual referenced: ${record.target}`);
    }
    if (record.readme === 'README.en.md' && /-zh\.svg$/u.test(record.target)) {
      failures.push(`${record.readme}: Chinese localized visual referenced: ${record.target}`);
    }
  }
  const zhLocalized = records.filter(
    (record) => record.readme === 'README.zh-CN.md' && /-zh\.svg$/u.test(record.target),
  );
  const enLocalized = records.filter(
    (record) => record.readme === 'README.en.md' && /-en\.svg$/u.test(record.target),
  );
  if (!zhLocalized.length) failures.push('README.zh-CN.md: Chinese localized visual is missing');
  if (!enLocalized.length) failures.push('README.en.md: English localized visual is missing');
  return { localizedReferences };
}

function svgAttribute(attributes, name) {
  const match = attributes.match(new RegExp(`\\b${name}=["']([^"']+)["']`, 'iu'));
  return match?.[1] ?? '';
}

function validateSvg(path) {
  const text = readUtf8(path, { requireNfc: true });
  const label = repositoryPath(path);
  const rootMatch = text.match(/<svg\b([^>]*)>/iu);
  if (!rootMatch) {
    failures.push(`${label}: SVG root is missing`);
    return;
  }
  const attributes = rootMatch[1];
  const viewBox = svgAttribute(attributes, 'viewBox');
  const role = svgAttribute(attributes, 'role');
  const ariaLabelledBy = svgAttribute(attributes, 'aria-labelledby');
  const localized = label.includes('/localized-vision/') || label.includes('/current-main/');
  if (!viewBox) failures.push(`${label}: SVG viewBox is missing`);
  if (localized && viewBox !== '0 0 1600 900') {
    failures.push(`${label}: localized SVG viewBox must be 0 0 1600 900`);
  }
  if (localized && role !== 'img') failures.push(`${label}: localized SVG requires role="img"`);
  if (localized && !ariaLabelledBy) {
    failures.push(`${label}: localized SVG requires aria-labelledby`);
  }
  const title = text.match(/<title(?:\s[^>]*)?>([\s\S]*?)<\/title>/iu)?.[1].trim() ?? '';
  const desc = text.match(/<desc(?:\s[^>]*)?>([\s\S]*?)<\/desc>/iu)?.[1].trim() ?? '';
  if (!title) failures.push(`${label}: accessible title is missing or empty`);
  if (!desc) failures.push(`${label}: accessible description is missing or empty`);
  if (HAN_PATTERN.test(text) && !CJK_FONT_PATTERN.test(text)) {
    failures.push(`${label}: CJK text lacks an explicit CJK font fallback`);
  }
  if (/<script\b|<foreignObject\b|javascript:/iu.test(text)) {
    failures.push(`${label}: active or foreign content is forbidden`);
  }
  if (/\son[a-z]+\s*=/iu.test(text)) failures.push(`${label}: event handler is forbidden`);
  if (/(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/iu.test(text)) {
    failures.push(`${label}: external or data URI resource is forbidden`);
  }
  if (/@import\b|url\(\s*["']?(?:https?:|\/\/|data:)/iu.test(text)) {
    failures.push(`${label}: external stylesheet or resource is forbidden`);
  }
  const name = basename(path);
  if (/-zh\.svg$/u.test(name) && !HAN_PATTERN.test(text)) {
    failures.push(`${label}: Chinese localized SVG lacks Chinese text`);
  }
  if (/-en\.svg$/u.test(name) && HAN_PATTERN.test(text)) {
    failures.push(`${label}: English localized SVG leaks Chinese text`);
  }
}

function validateVisualAssets() {
  const records = readmeImageRecords();
  const localRecords = records.filter(
    (record) => record.target && !/^(?:https?:|data:)/u.test(record.target),
  );
  const separationMetrics = validateLocalizedReadmeSeparation(records);
  const unique = [...new Set(localRecords.map((record) => record.target))].sort();
  for (const target of unique) {
    const path = resolve(ROOT, target);
    if (!path.startsWith(ROOT + sep) || !existsSync(path)) {
      failures.push(`README image target missing or unsafe: ${target}`);
      continue;
    }
    if (extname(path).toLowerCase() === '.svg') validateSvg(path);
  }
  return {
    readmeImages: records.length,
    localReadmeImages: localRecords.length,
    uniqueReadmeLocalImages: unique.length,
    readmeSvgImages: unique.filter((target) => extname(target).toLowerCase() === '.svg').length,
    ...separationMetrics,
  };
}

const textFiles = [
  ...SCAN_ROOTS.flatMap((directory) => walk(join(ROOT, directory))),
  ...README_PATHS.map((path) => join(ROOT, path)),
  join(ROOT, 'package.json'),
].filter((path) => TEXT_EXTENSIONS.has(extname(path).toLowerCase()));
for (const path of [...new Set(textFiles)].sort()) readUtf8(path);

const localeMetrics = validateLocaleMaps();
const visualMetrics = validateVisualAssets();
const report = {
  schemaVersion: 'resindb-i18n-visual-audit-2.0.0',
  scannedTextFiles: [...new Set(textFiles)].length,
  ...localeMetrics,
  ...visualMetrics,
  warnings,
  failures,
  acceptance: failures.length ? 'FAIL' : 'PASS',
};
mkdirSync(ARTIFACT_ROOT, { recursive: true });
writeFileSync(
  join(ARTIFACT_ROOT, 'i18n-visual-audit.json'),
  `${JSON.stringify(report, null, 2)}\n`,
);
console.log(JSON.stringify(report, null, 2));
if (failures.length) {
  throw new Error(`i18n and visual integrity audit failed:\n${failures.join('\n')}`);
}
