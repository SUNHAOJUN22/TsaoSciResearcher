import { expect, test, describe, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useClickFeedback } from '../../src/hooks/useClickFeedback';

const store = new Map<string, string>();

vi.mock('../../src/lib/utils', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../src/lib/utils')>();
  return {
    ...actual,
    safeStorage: {
      local: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => { store.set(key, value); },
        removeItem: (key: string) => { store.delete(key); },
        clear: () => { store.clear(); },
      },
      session: actual.safeStorage.session,
    }
  };
});

describe('useClickFeedback Hook', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        store.clear();
    });

    test('should initialize and return triggerFeedback function', () => {
        const { result } = renderHook(() => useClickFeedback());
        expect(result.current.triggerFeedback).toBeTypeOf('function');
    });

    test('should respect click haptic feedback toggle setting', () => {
        const vibrateMock = vi.fn();
        vi.stubGlobal('navigator', { vibrate: vibrateMock });

        // Set setting to false
        store.set("resindb-click-feedback", "false");
        
        const { result } = renderHook(() => useClickFeedback());
        act(() => {
            result.current.triggerFeedback();
        });
        
        expect(vibrateMock).not.toHaveBeenCalled();

        // Set setting to true
        store.set("resindb-click-feedback", "true");
        act(() => {
            result.current.triggerFeedback();
        });
        expect(vibrateMock).toHaveBeenCalledWith(15);
    });
});
