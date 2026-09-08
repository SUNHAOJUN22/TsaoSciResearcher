import React, {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { propertyMap, translations } from '@/config/i18n';
import { scientificUiOverrides } from '@/config/scientificUiOverrides';
import {
  humanizeTranslationKey,
  LANGUAGE_STORAGE_KEY,
  languageTag,
  normalizeLanguage,
  normalizeUiText,
  parseLanguage,
} from '@/i18n/runtime';
import { safeStorage } from '@/lib/utils';
import type { Language } from '@/types/index';

interface LanguageContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  t: (key: string, fallback?: string) => string;
  tProp: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);
const HAN_PATTERN = /\p{Script=Han}/u;

function initialLanguage(): Language {
  return normalizeLanguage(safeStorage.local.getItem(LANGUAGE_STORAGE_KEY));
}

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(initialLanguage);

  const setLanguage = useCallback((nextLanguage: Language) => {
    setLanguageState(normalizeLanguage(nextLanguage));
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguageState((previous) => (previous === 'zh' ? 'en' : 'zh'));
  }, []);

  useEffect(() => {
    document.documentElement.lang = languageTag(language);
    document.documentElement.dir = 'ltr';
    safeStorage.local.setItem(LANGUAGE_STORAGE_KEY, language);
  }, [language]);

  useEffect(() => {
    const handleLanguageChange = (event: Event) => {
      const parsed = parseLanguage((event as CustomEvent<unknown>).detail);
      if (parsed) setLanguageState(parsed);
    };
    window.addEventListener('resindb-language-change', handleLanguageChange);
    return () => window.removeEventListener('resindb-language-change', handleLanguageChange);
  }, []);

  const t = useCallback((key: string, fallback?: string) => {
    const override = scientificUiOverrides[language][key];
    const map = translations[language];
    const translated = map[key as keyof typeof map];
    const readableFallback = fallback
      ?? (language === 'zh' && HAN_PATTERN.test(key) ? key : humanizeTranslationKey(key));
    return normalizeUiText(override ?? translated, readableFallback);
  }, [language]);

  const tProp = useCallback((key: string) => {
    const readableFallback = humanizeTranslationKey(key);
    const translated = language === 'zh' ? key : propertyMap[key] ?? readableFallback;
    return normalizeUiText(translated, readableFallback);
  }, [language]);

  const value = useMemo<LanguageContextType>(() => ({
    language,
    setLanguage,
    toggleLanguage,
    t,
    tProp,
  }), [language, setLanguage, t, tProp, toggleLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within a LanguageProvider');
  return context;
}
