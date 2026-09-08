import path from 'node:path';

const SOURCE_FILE_PATTERN = /\.(?:ts|tsx)$/i;
const TEST_FILE_PATTERN = /\.(?:test|spec)\.(?:ts|tsx)$/i;
const NON_PRODUCTION_DIRECTORIES = new Set(['__tests__', '__mocks__']);

export function normalizeRepositoryPath(filePath) {
  return filePath.split(path.sep).join('/').replace(/\\/g, '/');
}

export function isProductionTypeScriptFile(filePath) {
  const normalized = normalizeRepositoryPath(filePath);
  const segments = normalized.split('/').filter(Boolean);
  const baseName = segments.at(-1) ?? '';

  if (!SOURCE_FILE_PATTERN.test(baseName)) return false;
  if (baseName.endsWith('.d.ts')) return false;
  if (TEST_FILE_PATTERN.test(baseName)) return false;
  if (segments.some((segment) => NON_PRODUCTION_DIRECTORIES.has(segment))) return false;
  return true;
}
