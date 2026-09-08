import React, { useMemo, useState } from 'react';
import { Globe2, Moon, Palette, Sun } from 'lucide-react';
import { safeStorage } from '@/lib/utils';

const paletteOptions = [
  ['indigo', 'Indigo'],
  ['emerald', 'Emerald Bio'],
  ['rose', 'Rose'],
  ['blue', 'Blue'],
  ['amber', 'Amber'],
  ['violet', 'Violet'],
  ['high-contrast', 'Contrast'],
] as const;

export const PreferenceControls: React.FC = () => {
  const initialLanguage = safeStorage.local.getItem('resindb-language') === 'en' ? 'en' : 'zh';
  const [language, setLanguage] = useState<'zh' | 'en'>(initialLanguage);
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    safeStorage.local.getItem('resindb-theme') === 'dark' ? 'dark' : 'light',
  );
  const [paletteOpen, setPaletteOpen] = useState(false);
  const currentPalette = safeStorage.local.getItem('resindb-color-theme') || 'indigo';
  const labels = useMemo(
    () => ({
      language: language === 'zh' ? 'Switch to English / 切换至 English' : 'Switch to Chinese / 切换至中文',
      theme: theme === 'dark' ? '浅色日间模式 / Switch to Light Mode' : '深色夜间模式 / Switch to Dark Mode',
      palette: language === 'zh' ? '皮肤配色主题 / Color Theme Palette' : 'Color Theme Palette / 皮肤配色主题',
    }),
    [language, theme],
  );

  const switchLanguage = () => {
    const next = language === 'zh' ? 'en' : 'zh';
    safeStorage.local.setItem('resindb-language', next);
    document.documentElement.lang = next === 'zh' ? 'zh-CN' : 'en';
    window.dispatchEvent(new CustomEvent('resindb-language-change', { detail: next }));
    setLanguage(next);
  };

  const switchTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    safeStorage.local.setItem('resindb-theme', next);
    document.documentElement.classList.toggle('dark', next === 'dark');
    document.documentElement.style.colorScheme = next;
    window.dispatchEvent(new CustomEvent('resindb-theme-change', { detail: next }));
    setTheme(next);
  };

  const choosePalette = (palette: string) => {
    safeStorage.local.setItem('resindb-color-theme', palette);
    window.dispatchEvent(new CustomEvent('resindb-color-theme-change', { detail: palette }));
    setPaletteOpen(false);
  };

  return (
    <div className="fixed right-3 top-3 z-[160] flex items-center gap-1 rounded-xl border border-slate-200/80 bg-white/90 p-1 shadow-lg backdrop-blur dark:border-slate-700/80 dark:bg-slate-900/90">
      <button type="button" data-testid="language-control" onClick={switchLanguage} title={labels.language} className="flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800">
        <Globe2 size={15} /> {language === 'zh' ? '中/EN' : 'EN/中'}
      </button>
      <button type="button" data-testid="theme-control" onClick={switchTheme} title={labels.theme} className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800">
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>
      <div className="relative">
        <button type="button" data-testid="palette-control" onClick={() => setPaletteOpen((open) => !open)} title={labels.palette} className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800">
          <Palette size={16} />
        </button>
        {paletteOpen && (
          <div className="absolute right-0 top-10 w-40 rounded-xl border border-slate-200 bg-white p-1 shadow-xl dark:border-slate-700 dark:bg-slate-900">
            {paletteOptions.map(([id, name]) => (
              <button key={id} type="button" data-palette={id} onClick={() => choosePalette(id)} className={`block w-full rounded-lg px-3 py-2 text-left text-xs ${currentPalette === id ? 'bg-primary-50 font-semibold text-primary-700 dark:bg-primary-950/40 dark:text-primary-300' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}>
                {name}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
