import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api/client';
import type { TokenResponse, UserPublic } from '../types';

const TOKEN_KEY = 'rezepte-auth-token';

type AuthContextValue = {
  token: string | null;
  user: UserPublic | null;
  isAuthenticated: boolean;
  mayManageUsers: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    typeof window === 'undefined' ? null : window.localStorage.getItem(TOKEN_KEY),
  );
  const [user, setUser] = useState<UserPublic | null>(null);

  useEffect(() => {
    if (token) {
      window.localStorage.setItem(TOKEN_KEY, token);
      void loadCurrentUser(token);
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    }
  }, [token]);

  async function loadCurrentUser(currentToken: string): Promise<void> {
    try {
      const currentUser = await apiFetch<UserPublic>('/auth/me', {}, currentToken);
      setUser(currentUser);
    } catch {
      setToken(null);
      setUser(null);
    }
  }

  async function login(username: string, password: string): Promise<void> {
    const response = await apiFetch<TokenResponse>(
      '/auth/login',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      },
      null,
    );

    setToken(response.access_token);
    setUser(response.user);
  }

  function logout(): void {
    setToken(null);
    setUser(null);
  }

  async function refreshUser(): Promise<void> {
    if (token) {
      await loadCurrentUser(token);
    }
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      mayManageUsers: Boolean(
        user?.is_super_admin || user?.groups.some((group) => group.role === 'admin'),
      ),
      login,
      logout,
      refreshUser,
    }),
    [token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }

  return context;
}
