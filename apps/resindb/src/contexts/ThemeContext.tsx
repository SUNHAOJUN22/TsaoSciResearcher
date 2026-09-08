
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { safeStorage } from '@/lib/utils';

type Theme = 'light' | 'dark';
export type ColorTheme = 'indigo' | 'emerald' | 'rose' | 'blue' | 'amber' | 'violet' | 'high-contrast';

interface ThemeContextType {
  theme: Theme;
  colorTheme: ColorTheme;
  toggleTheme: () => void;
  setColorTheme: (color: ColorTheme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Color Palettes Definition (Tailwind Colors 50-950)
const PALETTES: Record<ColorTheme, Record<string, string>> = {
  indigo: { // Default
    50: '#eef2ff', 100: '#e0e7ff', 200: '#c7d2fe', 300: '#a5b4fc', 400: '#818cf8', 
    500: '#6366f1', 600: '#4f46e5', 700: '#4338ca', 800: '#3730a3', 900: '#312e81', 950: '#1e1b4b',
    rgb: '99, 102, 241' // for 500
  },
  emerald: { // Green/Safe
    50: '#ecfdf5', 100: '#d1fae5', 200: '#a7f3d0', 300: '#6ee7b7', 400: '#34d399', 
    500: '#10b981', 600: '#059669', 700: '#047857', 800: '#065f46', 900: '#064e3b', 950: '#022c22',
    rgb: '16, 185, 129'
  },
  rose: { // Red/Warm
    50: '#fff1f2', 100: '#ffe4e6', 200: '#fecdd3', 300: '#fda4af', 400: '#fb7185', 
    500: '#f43f5e', 600: '#e11d48', 700: '#be123c', 800: '#9f1239', 900: '#881337', 950: '#4c0519',
    rgb: '244, 63, 94'
  },
  blue: { // Corporate/Tech
    50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd', 400: '#60a5fa', 
    500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 800: '#1e40af', 900: '#1e3a8a', 950: '#172554',
    rgb: '59, 130, 246'
  },
  amber: { // Energy/Warning
    50: '#fffbeb', 100: '#fef3c7', 200: '#fde68a', 300: '#fcd34d', 400: '#fbbf24', 
    500: '#f59e0b', 600: '#d97706', 700: '#b45309', 800: '#92400e', 900: '#78350f', 950: '#451a03',
    rgb: '245, 158, 11'
  },
  violet: { // Creative/Future
    50: '#f5f3ff', 100: '#ede9fe', 200: '#ddd6fe', 300: '#c4b5fd', 400: '#a78bfa', 
    500: '#8b5cf6', 600: '#7c3aed', 700: '#6d28d9', 800: '#5b21b6', 900: '#4c1d95', 950: '#2e1065',
    rgb: '139, 92, 246'
  },
  'high-contrast': { // Accessibility
    50: '#ffffff', 100: '#e5e5e5', 200: '#cccccc', 300: '#b2b2b2', 400: '#999999', 
    500: '#000000', 600: '#000000', 700: '#000000', 800: '#000000', 900: '#000000', 950: '#000000',
    rgb: '0, 0, 0'
  }
};

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Light/Dark Theme
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
        try {
          const saved = safeStorage.local.getItem('resindb-theme');
          if (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
          return (saved as Theme) || 'light';
        } catch {
          return 'light';
        }
    }
    return 'light';
  });

  // Color Theme
  const [colorTheme, setColorTheme] = useState<ColorTheme>(() => {
      if (typeof window !== 'undefined') {
          try {
              return (safeStorage.local.getItem('resindb-color-theme') as ColorTheme) || 'indigo';
          } catch {
              return 'indigo';
          }
      }
      return 'indigo';
  });

  // Apply Light/Dark
  useEffect(() => {
    const root = document.documentElement;
    try {
      safeStorage.local.setItem('resindb-theme', theme);
    } catch {
      // Ignore security error inside sandboxed iframe
    }
    if (theme === 'dark') {
      root.classList.add('dark');
      root.style.colorScheme = 'dark';
    } else {
      root.classList.remove('dark');
      root.style.colorScheme = 'light';
    }
  }, [theme]);

  // Apply Color Palette
  useEffect(() => {
      const root = document.documentElement;
      try {
        safeStorage.local.setItem('resindb-color-theme', colorTheme);
      } catch {
        // Ignore security error
      }
      const palette = PALETTES[colorTheme];
      
      // Update CSS Variables dynamically
      Object.entries(palette).forEach(([key, value]) => {
          const val = value as string; // Explicit Cast
          if (key === 'rgb') {
              root.style.setProperty('--color-primary-500-rgb', val);
          } else {
              root.style.setProperty(`--color-primary-${key}`, val);
              
              // Generate RGB version for all levels to support rgba(var(--color-primary-X-rgb), alpha)
              if (val.startsWith('#')) {
                  const r = parseInt(val.slice(1, 3), 16);
                  const g = parseInt(val.slice(3, 5), 16);
                  const b = parseInt(val.slice(5, 7), 16);
                  root.style.setProperty(`--color-primary-${key}-rgb`, `${r}, ${g}, ${b}`);
              }
          }
      });
  }, [colorTheme]);


  useEffect(() => {
    const handleThemeChange = (event: Event) => {
      const next = (event as CustomEvent<Theme>).detail;
      if (next === 'light' || next === 'dark') setTheme(next);
    };
    const handleColorThemeChange = (event: Event) => {
      const next = (event as CustomEvent<ColorTheme>).detail;
      if (next in PALETTES) setColorTheme(next);
    };
    window.addEventListener('resindb-theme-change', handleThemeChange);
    window.addEventListener('resindb-color-theme-change', handleColorThemeChange);
    return () => {
      window.removeEventListener('resindb-theme-change', handleThemeChange);
      window.removeEventListener('resindb-color-theme-change', handleColorThemeChange);
    };
  }, []);

  const toggleTheme = React.useCallback(() => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  }, []);

  const value = React.useMemo(() => ({ theme, colorTheme, toggleTheme, setColorTheme }), [theme, colorTheme, toggleTheme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
