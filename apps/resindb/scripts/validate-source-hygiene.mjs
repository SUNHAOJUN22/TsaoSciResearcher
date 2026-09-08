#!/usr/bin/env node

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { basename, dirname, extname, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SOURCE_ROOT = resolve(ROOT, 'src')
const SOURCE_SUFFIXES = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs'])
const WALK_EXCLUDES = new Set(['.git', 'node_modules', 'dist', 'coverage', 'artifacts'])
const RUNTIME_ARTIFACT_NAMES = new Set(['.coverage', 'coverage-final.json'])
const RUNTIME_ARTIFACT_SUFFIXES = new Set(['.pyc', '.pyo', '.tsbuildinfo'])
const RULES = [
  ['TypeScript suppression', /@ts-(?:ignore|nocheck)/],
  ['ESLint suppression', /eslint-disable/],
  ['dynamic HTML injection', /dangerouslySetInnerHTML/],
  ['eval execution', /(^|[^A-Za-z0-9_$])eval\s*\(/],
  ['Function constructor execution', /\bnew\s+Function\s*\(/],
  ['unfinished marker', /\b(?:TODO|FIXME|HACK)\b/],
  ['variadic array extrema', /Math\.(?:min|max)\(\s*\.\.\./],
  ['explicit any type', /(?:\:\s*any\b|<any>|\bas any\b)/],
]

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      if (entry.isDirectory() && WALK_EXCLUDES.has(entry.name)) return []
      const path = resolve(directory, entry.name)
      return entry.isDirectory() ? walk(path) : [path]
    })
    .sort()
}

function isRuntimeArtifact(path) {
  const relativePath = relative(ROOT, path)
  const segments = relativePath.split(sep)
  return (
    segments.includes('__pycache__')
    || RUNTIME_ARTIFACT_NAMES.has(basename(path))
    || RUNTIME_ARTIFACT_SUFFIXES.has(extname(path))
  )
}

if (!statSync(SOURCE_ROOT, { throwIfNoEntry: false })?.isDirectory()) {
  throw new Error(`production source directory is missing: ${SOURCE_ROOT}`)
}

const repositoryFiles = walk(ROOT)
const runtimeArtifacts = repositoryFiles.filter(isRuntimeArtifact).map((path) => relative(ROOT, path))
if (runtimeArtifacts.length) {
  throw new Error(`runtime/build artifacts must not be tracked or retained in the repository tree:\n${runtimeArtifacts.join('\n')}`)
}

const findings = []
let scannedFiles = 0
for (const path of repositoryFiles) {
  if (!path.startsWith(`${SOURCE_ROOT}${sep}`) || !SOURCE_SUFFIXES.has(extname(path))) continue
  scannedFiles += 1
  const lines = readFileSync(path, 'utf8').split(/\r?\n/)
  lines.forEach((line, index) => {
    for (const [name, pattern] of RULES) {
      if (pattern.test(line)) {
        findings.push(`${relative(ROOT, path)}:${index + 1}: ${name}: ${line.trim()}`)
      }
    }
  })
}

if (scannedFiles === 0) throw new Error('production source hygiene scanned zero source files')
if (findings.length) throw new Error(`production source hygiene failed:\n${findings.join('\n')}`)
console.log(`validated production source hygiene across ${scannedFiles} files; repository runtime artifacts are absent and negative security fixtures remain test-scoped`)
