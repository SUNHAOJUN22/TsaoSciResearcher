import { useCallback, useRef } from 'react';
import { safeStorage } from '@/lib/utils';
import { useOptionalUI } from '@/contexts/UIContext';

let globalAudioContext: AudioContext | null = null;

function readStoredPreference(): boolean {
  try {
    const stored = safeStorage.local.getItem('resindb-click-feedback');
    return stored === null ? true : stored === 'true';
  } catch {
    return true;
  }
}

export function useClickFeedback() {
  const ui = useOptionalUI();
  const enabledRef = useRef(readStoredPreference());

  const isEnabled = useCallback(() => {
    if (ui) {
      enabledRef.current = ui.clickFeedbackEnabled;
    } else {
      enabledRef.current = readStoredPreference();
    }
    return enabledRef.current;
  }, [ui]);

  const triggerFeedback = useCallback(() => {
    if (!isEnabled() || typeof window === 'undefined') return;

    if (typeof window.navigator?.vibrate === 'function') {
      try {
        window.navigator.vibrate(15);
      } catch {
        // Vibration may be blocked by the browser or device policy.
      }
    }

    const AudioContextConstructor =
      window.AudioContext ??
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

    if (!AudioContextConstructor) return;

    try {
      globalAudioContext ??= new AudioContextConstructor();
      const context = globalAudioContext;

      if (context.state === 'suspended') {
        void context.resume().catch(() => undefined);
      }

      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const startTime = context.currentTime;

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(1400, startTime);
      oscillator.frequency.exponentialRampToValueAtTime(800, startTime + 0.04);
      gain.gain.setValueAtTime(0.04, startTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.04);

      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.addEventListener(
        'ended',
        () => {
          oscillator.disconnect();
          gain.disconnect();
        },
        { once: true },
      );
      oscillator.start(startTime);
      oscillator.stop(startTime + 0.05);
    } catch {
      // Audio feedback is optional and must never break the primary interaction.
    }
  }, [isEnabled]);

  return { triggerFeedback };
}
