import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

let fallbackIdCounter = 0;

export function generateId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const values = new Uint32Array(2);
    crypto.getRandomValues(values);
    return `p-${values[0].toString(36)}${values[1].toString(36)}`;
  }
  fallbackIdCounter += 1;
  return `p-${Date.now().toString(36)}-${fallbackIdCounter.toString(36)}`;
}

export const safeStorage = {
  local: {
    getItem(key: string): string | null {
      try {
        return typeof window !== 'undefined' ? localStorage.getItem(key) : null;
      } catch {
        return null;
      }
    },
    setItem(key: string, value: string): void {
      try {
        if (typeof window !== 'undefined') localStorage.setItem(key, value);
      } catch {
        // Safe fail
      }
    },
    removeItem(key: string): void {
      try {
        if (typeof window !== 'undefined') localStorage.removeItem(key);
      } catch {
        // Safe fail
      }
    },
    clear(): void {
      try {
        if (typeof window !== 'undefined') localStorage.clear();
      } catch {
        // Safe fail
      }
    }
  },
  session: {
    getItem(key: string): string | null {
      try {
        return typeof window !== 'undefined' ? sessionStorage.getItem(key) : null;
      } catch {
        return null;
      }
    },
    setItem(key: string, value: string): void {
      try {
        if (typeof window !== 'undefined') sessionStorage.setItem(key, value);
      } catch {
        // Safe fail
      }
    },
    removeItem(key: string): void {
      try {
        if (typeof window !== 'undefined') sessionStorage.removeItem(key);
      } catch {
        // Safe fail
      }
    },
    clear(): void {
      try {
        if (typeof window !== 'undefined') sessionStorage.clear();
      } catch {
        // Safe fail
      }
    }
  }
};
