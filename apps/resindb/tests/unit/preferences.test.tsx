import React from 'react';
import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, test } from 'vitest';
import { LanguageProvider, useLanguage } from '@/contexts/LanguageContext';
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext';

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.className = '';
  document.documentElement.removeAttribute('style');
  document.documentElement.removeAttribute('lang');
  document.documentElement.removeAttribute('dir');
});

describe('language and theme preferences', () => {
  test('persists language and updates the document language', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <LanguageProvider>{children}</LanguageProvider>
    );
    const { result } = renderHook(() => useLanguage(), { wrapper });

    act(() => result.current.toggleLanguage());

    expect(result.current.language).toBe('en');
    expect(window.localStorage.getItem('resindb-language')).toBe('en');
    expect(document.documentElement.lang).toBe('en');
    expect(document.documentElement.dir).toBe('ltr');
  });

  test('normalizes legacy locale aliases and accepts the governed language event', () => {
    window.localStorage.setItem('resindb-language', 'zh-CN');
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <LanguageProvider>{children}</LanguageProvider>
    );
    const { result } = renderHook(() => useLanguage(), { wrapper });

    expect(result.current.language).toBe('zh');
    expect(window.localStorage.getItem('resindb-language')).toBe('zh');
    expect(document.documentElement.lang).toBe('zh-CN');

    act(() => {
      window.dispatchEvent(new CustomEvent('resindb-language-change', { detail: 'en-US' }));
    });

    expect(result.current.language).toBe('en');
    expect(document.documentElement.lang).toBe('en');
  });

  test('persists dark mode and color palette', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <ThemeProvider>{children}</ThemeProvider>
    );
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => result.current.toggleTheme());
    act(() => result.current.setColorTheme('emerald'));

    expect(window.localStorage.getItem('resindb-theme')).toBe('dark');
    expect(window.localStorage.getItem('resindb-color-theme')).toBe('emerald');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
