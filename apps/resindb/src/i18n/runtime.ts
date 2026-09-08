import type { Language } from '@/types/index';

export const LANGUAGE_STORAGE_KEY = 'resindb-language';

const LANGUAGE_ALIASES: Readonly<Record<string, Language>> = {
  zh: 'zh',
  'zh-cn': 'zh',
  'zh-hans': 'zh',
  chinese: 'zh',
  中文: 'zh',
  en: 'en',
  'en-us': 'en',
  'en-gb': 'en',
  english: 'en',
};

const MOJIBAKE_PATTERN = /\uFFFD|\u00C3[\u0080-\u00BF]|\u00C2[\u0080-\u00BF]|\u00E2[\u0080-\u00BF]{1,2}|\u00F0\u0178|\u00EF\u00BB\u00BF|\u951F\u65A4\u62F7/u;

function hasForbiddenControlCharacter(value: string): boolean {
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

export function parseLanguage(value: unknown): Language | null {
  if (typeof value !== 'string') return null;
  const normalized = value.normalize('NFKC').trim().toLowerCase();
  return LANGUAGE_ALIASES[normalized] ?? null;
}

export function normalizeLanguage(value: unknown, fallback: Language = 'zh'): Language {
  return parseLanguage(value) ?? fallback;
}

export function languageTag(language: Language): 'zh-CN' | 'en' {
  return language === 'zh' ? 'zh-CN' : 'en';
}

export function hasCorruptedUnicode(value: string): boolean {
  return hasForbiddenControlCharacter(value) || MOJIBAKE_PATTERN.test(value);
}

export function normalizeUiText(value: unknown, fallback = ''): string {
  const candidate = typeof value === 'string' ? value.normalize('NFC') : '';
  if (!candidate.trim() || hasCorruptedUnicode(candidate)) {
    const safeFallback = fallback.normalize('NFC');
    return hasCorruptedUnicode(safeFallback) ? '' : safeFallback;
  }
  return candidate;
}

export function humanizeTranslationKey(key: string): string {
  const normalized = key
    .normalize('NFKC')
    .replace(/[._-]+/gu, ' ')
    .replace(/([a-z0-9])([A-Z])/gu, '$1 $2')
    .replace(/\s+/gu, ' ')
    .trim();
  if (!normalized) return '';
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}
