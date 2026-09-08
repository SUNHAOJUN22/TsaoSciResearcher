import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { User } from '@/types/index';
import { isSafeAvatarDataUrl } from '@/components/ui/UserAvatar';
import { safeStorage } from '@/lib/utils';

const SESSION_KEY = 'resindb-session';

interface AuthContextType {
  currentUser: User | null;
  login: (user: User) => void;
  logout: () => void;
  isAuthenticated: boolean;
  updateUserProfile: (data: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function sanitizeUser(input: unknown): User | null {
  if (!input || typeof input !== 'object') return null;
  const candidate = input as Partial<User> & Record<string, unknown>;
  if (
    typeof candidate.id !== 'string' ||
    typeof candidate.name !== 'string' ||
    typeof candidate.email !== 'string' ||
    !['admin', 'editor', 'viewer'].includes(String(candidate.role))
  ) {
    return null;
  }

  return {
    id: candidate.id,
    name: candidate.name.trim().slice(0, 120),
    email: candidate.email.trim().slice(0, 254),
    role: candidate.role as User['role'],
    avatar: isSafeAvatarDataUrl(candidate.avatar) ? candidate.avatar : undefined,
  };
}

function readSession(): User | null {
  // Remove the legacy persistent demo session, which could contain stale profile data.
  safeStorage.local.removeItem(SESSION_KEY);
  const saved = safeStorage.session.getItem(SESSION_KEY);
  if (!saved) return null;

  try {
    return sanitizeUser(JSON.parse(saved));
  } catch {
    safeStorage.session.removeItem(SESSION_KEY);
    return null;
  }
}

function writeSession(user: User | null): void {
  if (user) {
    safeStorage.session.setItem(SESSION_KEY, JSON.stringify(user));
  } else {
    safeStorage.session.removeItem(SESSION_KEY);
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(readSession);

  const login = useCallback((user: User) => {
    const sanitized = sanitizeUser(user);
    if (!sanitized) return;
    setCurrentUser(sanitized);
    writeSession(sanitized);
  }, []);

  const logout = useCallback(() => {
    setCurrentUser(null);
    writeSession(null);
  }, []);

  const updateUserProfile = useCallback((updatedData: Partial<User>) => {
    setCurrentUser((previous) => {
      if (!previous) return null;
      const sanitized = sanitizeUser({ ...previous, ...updatedData, id: previous.id, role: previous.role });
      if (!sanitized) return previous;
      writeSession(sanitized);
      return sanitized;
    });
  }, []);

  const value = useMemo<AuthContextType>(() => ({
    currentUser,
    login,
    logout,
    isAuthenticated: Boolean(currentUser),
    updateUserProfile,
  }), [currentUser, login, logout, updateUserProfile]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
