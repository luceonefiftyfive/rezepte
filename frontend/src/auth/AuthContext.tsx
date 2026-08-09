import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api/client';
import { startAuthentication, startRegistration } from '@simplewebauthn/browser';
import type {
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
} from '@simplewebauthn/browser';
import type { TokenResponse, UserPublic } from '../types';

const TOKEN_KEY = 'rezepte-auth-token';

type AuthContextValue = {
  token: string | null;
  user: UserPublic | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  mayManageUsers: boolean;
  mayManageGroups: boolean;
  mayEditRecipes: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginWithPasskey: (username: string) => Promise<void>;
  registerPasskey: (credentialName?: string) => Promise<void>;
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

  async function loginWithPasskey(username: string): Promise<void> {
    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      throw new Error('Bitte Benutzernamen eingeben');
    }

    const optionsResponse = await apiFetch<{ options: PublicKeyCredentialRequestOptionsJSON }>(
      '/auth/passkey/login/options',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: trimmedUsername }),
      },
      null,
    );
    const credential = await startAuthentication({
      optionsJSON: optionsResponse.options,
    });

    const response = await apiFetch<TokenResponse>(
      '/auth/passkey/login/verify',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: trimmedUsername, credential }),
      },
      null,
    );
    setToken(response.access_token);
    setUser(response.user);
  }

  async function registerPasskey(credentialName?: string): Promise<void> {
    if (!token) {
      throw new Error('Nicht angemeldet');
    }

    const optionsResponse = await apiFetch<{ options: PublicKeyCredentialCreationOptionsJSON }>(
      '/auth/passkey/register/options',
      { method: 'POST' },
      token,
    );
    const credential = await startRegistration({
      optionsJSON: optionsResponse.options,
    });

    const updatedUser = await apiFetch<UserPublic>(
      '/auth/passkey/register/verify',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credential,
          credential_name: credentialName,
        }),
      },
      token,
    );
    setUser(updatedUser);
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
      isAdmin: Boolean(
        user?.is_super_admin || user?.groups.some((group) => group.role === 'admin'),
      ),
      mayManageUsers: Boolean(
        user?.is_super_admin || user?.groups.some((group) => group.role === 'admin'),
      ),
      mayManageGroups: Boolean(user?.is_super_admin),
      mayEditRecipes: Boolean(
        user?.is_super_admin ||
        user?.groups.some((group) => group.role === 'admin' || group.role === 'author'),
      ),
      login,
      loginWithPasskey,
      registerPasskey,
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
