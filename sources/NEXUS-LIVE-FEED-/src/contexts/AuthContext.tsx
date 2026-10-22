import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type AuthUser = {
  name: string;
  dateOfBirth: string;
  placeOfBirth: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  login: (credentials: AuthUser) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'nexus-auth-user';
export const DEFAULT_USER: AuthUser = {
  name: 'Gary Leckey',
  dateOfBirth: '1991-11-02',
  placeOfBirth: 'Belfast, Northern Ireland',
};

const readStoredUser = (): AuthUser | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const storedUser = localStorage.getItem(STORAGE_KEY);
    if (storedUser) {
      return JSON.parse(storedUser) as AuthUser;
    }
  } catch (error) {
    console.warn('Failed to restore Nexus login state:', error);
  }

  return null;
};

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser() ?? DEFAULT_USER);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      const storedUser = readStoredUser();
      if (storedUser) {
        setUser(storedUser);
      } else {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_USER));
      }
    } catch (error) {
      console.warn('Failed to restore Nexus login state:', error);
    }
  }, []);

  const login = useCallback((credentials: AuthUser) => {
    setUser(credentials);
    if (typeof window === 'undefined') {
      return;
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(credentials));
    } catch (error) {
      console.warn('Failed to persist Nexus login state:', error);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    if (typeof window === 'undefined') {
      return;
    }
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.warn('Failed to clear Nexus login state:', error);
    }
  }, []);

  const value = useMemo(() => ({ user, login, logout }), [login, logout, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
