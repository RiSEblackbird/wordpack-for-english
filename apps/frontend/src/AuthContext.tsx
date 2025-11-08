import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';

export interface AuthenticatedUser {
  google_sub: string;
  email: string;
  display_name: string;
  last_login_at?: string;
  [key: string]: unknown;
}

interface StoredAuthPayload {
  user: AuthenticatedUser;
  token: string;
}

interface AuthContextValue {
  user: AuthenticatedUser | null;
  token: string | null;
  isAuthenticating: boolean;
  error: string | null;
  signIn: (idToken: string) => Promise<void>;
  signOut: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'wordpack.auth.v1';

const SESSION_COOKIE_NAME = import.meta.env.VITE_SESSION_COOKIE_NAME || 'wp_session';

/**
 * ローカルストレージから最後に成功した認証情報を読み取る。
 * 副作用: window が存在しない環境では何もしない。
 */
function readStoredAuth(): StoredAuthPayload | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredAuthPayload;
    if (parsed && parsed.user && parsed.token) {
      return parsed;
    }
  } catch (error) {
    console.warn('Failed to parse stored auth payload', error);
  }
  return null;
}

/**
 * 現在の認証状態をローカルストレージへ保存する。
 * 副作用: 認証解除時は保存内容を破棄する。
 */
function persistAuth(payload: StoredAuthPayload | null): void {
  if (typeof window === 'undefined') return;
  if (payload === null) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

export const AuthProvider: React.FC<{ clientId: string; children: React.ReactNode }> = ({ clientId, children }) => {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clientIdRef = useRef(clientId);

  useEffect(() => {
    clientIdRef.current = clientId;
    if (!clientId) {
      console.error('VITE_GOOGLE_CLIENT_ID is not set; Google login will not work.');
    }
  }, [clientId]);

  useEffect(() => {
    const stored = readStoredAuth();
    if (stored) {
      setUser(stored.user);
      setToken(stored.token);
    }
  }, []);

  useEffect(() => {
    if (user && token) {
      persistAuth({ user, token });
    } else {
      persistAuth(null);
    }
  }, [user, token]);

  /**
   * Google から取得した ID トークンをバックエンドへ送信し、セッションを確立する。
   * 副作用: セッション Cookie 設定、ユーザー状態の更新、エラー時は状態クリア。
   */
  const signIn = useCallback(async (idToken: string) => {
    setIsAuthenticating(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ id_token: idToken }),
      });
      const payload = (await response.json().catch(() => null)) as
        | { user?: AuthenticatedUser; detail?: string }
        | null;
      if (!response.ok || !payload || !payload.user) {
        const detail = payload?.detail || 'Unknown error';
        throw new Error(detail);
      }
      setUser(payload.user);
      setToken(idToken);
    } catch (err) {
      console.error('Google sign-in failed', err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Google sign-in failed');
      }
      throw err;
    } finally {
      setIsAuthenticating(false);
    }
  }, []);

  /**
   * セッションクッキーの破棄をブラウザへ指示する。
   * 副作用: document.cookie に Max-Age=0 の値を書き込み、後続リクエストを匿名化。
   */
  const clearSessionCookie = useCallback(() => {
    if (typeof document === 'undefined') return;
    document.cookie = `${SESSION_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax`;
  }, []);

  /**
   * バックエンドへログアウトを通知し、クライアント側の認証情報を破棄する。
   * 副作用: ローカルストレージと Cookie を削除し、ユーザー状態を初期化。
   */
  const signOut = useCallback(async () => {
    setIsAuthenticating(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
      if (!response.ok && response.status !== 404) {
        console.warn('Unexpected response when logging out', response.status);
      }
    } catch (err) {
      console.warn('Failed to notify backend about logout', err);
    } finally {
      setUser(null);
      setToken(null);
      clearSessionCookie();
      setIsAuthenticating(false);
    }
  }, [clearSessionCookie]);

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    isAuthenticating,
    error,
    signIn,
    signOut,
    clearError,
  }), [user, token, isAuthenticating, error, signIn, signOut, clearError]);

  return (
    <GoogleOAuthProvider clientId={clientIdRef.current}>
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    </GoogleOAuthProvider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
