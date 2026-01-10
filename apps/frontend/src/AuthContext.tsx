import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';

export interface AuthenticatedUser {
  google_sub: string;
  email: string;
  display_name: string;
  last_login_at?: string;
  [key: string]: unknown;
}

/**
 * Google Identity Services が返す CredentialResponse.credential（ID トークン）を示す型エイリアス。
 * 文字列そのものだが、呼び出し側が用途を見失わないよう意味付けを明示する。
 */
export type GoogleIdToken = string;

export type AuthMode = 'authenticated' | 'guest' | 'anonymous';

interface StoredAuthPayload {
  authMode: 'authenticated' | 'guest';
  user?: AuthenticatedUser;
  // UI 用に保持したい追加情報を将来拡張できるように予約枠を残す。
  [key: string]: unknown;
}

interface AuthContextValue {
  user: AuthenticatedUser | null;
  authMode: AuthMode;
  isGuest: boolean;
  isAuthenticating: boolean;
  error: string | null;
  signIn: (idToken: GoogleIdToken) => Promise<void>;
  signOut: () => Promise<void>;
  enterGuestMode: () => void;
  clearError: () => void;
  authBypassActive: boolean;
  missingClientId: boolean;
  googleClientId: string;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'wordpack.auth.v1';

const PRIMARY_SESSION_COOKIE = (import.meta.env.VITE_SESSION_COOKIE_NAME || 'wp_session').trim() || 'wp_session';
const SESSION_COOKIE_NAMES = Array.from(new Set([PRIMARY_SESSION_COOKIE, '__session']));

const AUTH_BYPASS_USER: AuthenticatedUser = {
  google_sub: 'dev-bypass',
  email: 'dev@wordpack.local',
  display_name: 'WordPack Dev User',
};

/**
 * ローカルストレージから最後に成功した認証情報を読み取る。
 * 副作用: window が存在しない環境では何もしない。
 */
function readStoredAuth(): StoredAuthPayload | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<StoredAuthPayload> & { token?: unknown };
    if (!parsed || typeof parsed !== 'object') return null;
    if (parsed.authMode === 'guest') {
      return { authMode: 'guest' };
    }
    if (parsed.user && typeof parsed.user === 'object') {
      // 互換性確保のため、旧バージョンが保存した token フィールドは読み飛ばし
      // （破棄）し、UI 用のユーザー情報だけを復元する。
      return { authMode: 'authenticated', user: parsed.user as AuthenticatedUser };
    }
  } catch (error) {
    console.warn('Failed to parse stored auth payload', error);
  }
  return null;
}

/**
 * 現在の認証状態をローカルストレージへ保存する。
 * 副作用: 認証解除時は保存内容を破棄する。
 * 備考: ID トークンは XSS 時の二次被害を避けるため保存しない。HttpOnly Cookie を前提に
 *       セッションを維持し、ストレージには UI 表示に必要なユーザー情報のみを残す。
 */
function persistAuth(payload: StoredAuthPayload | null): void {
  if (typeof window === 'undefined') return;
  if (payload === null) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  // ゲスト閲覧モードはログイン不要の入口として用いるため、再読み込み後も状態を維持する。
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

export const AuthProvider: React.FC<{ clientId: string; children: React.ReactNode }> = ({ clientId, children }) => {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>('anonymous');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authBypassActive, setAuthBypassActive] = useState(false);
  /**
   * /api/config の初期ロードが完了したかを記録する。
   * 新参メンバー向けに補足すると、このフラグが true になるまでは
   * Google クライアント ID の警告ログを抑制し、誤検知による混乱を避ける。
   */
  const [authConfigResolved, setAuthConfigResolved] = useState(false);
  const normalizedClientId = useMemo(() => clientId.trim(), [clientId]);
  const clientIdRef = useRef(normalizedClientId);
  const authModeRef = useRef<AuthMode>(authMode);
  const missingClientId = normalizedClientId.length === 0;

  useEffect(() => {
    clientIdRef.current = normalizedClientId;
    if (!authConfigResolved || normalizedClientId) {
      return;
    }
    const message = 'VITE_GOOGLE_CLIENT_ID is not set; Google login will not work.';
    if (authBypassActive) {
      console.warn(
        `${message} Authentication bypass is active; continuing with development fallback.`,
      );
      return;
    }
    console.error(message);
  }, [normalizedClientId, authConfigResolved, authBypassActive]);

  const updateAuthMode = useCallback((next: AuthMode) => {
    authModeRef.current = next;
    setAuthMode(next);
  }, []);

  useEffect(() => {
    const stored = readStoredAuth();
    if (stored) {
      if (stored.authMode === 'guest') {
        updateAuthMode('guest');
        setUser(null);
      } else if (stored.user) {
        updateAuthMode('authenticated');
        setUser(stored.user);
      }
    }
  }, [updateAuthMode]);

  useEffect(() => {
    if (authMode === 'guest') {
      persistAuth({ authMode: 'guest' });
      return;
    }
    if (authMode === 'authenticated' && user) {
      persistAuth({ authMode: 'authenticated', user });
      return;
    }
    persistAuth(null);
  }, [authMode, user]);

  useEffect(() => {
    let aborted = false;
    (async () => {
      try {
        const res = await fetch('/api/config', { method: 'GET' });
        if (!res.ok) return;
        const json = (await res
          .json()
          .catch(() => null)) as { session_auth_disabled?: boolean } | null;
        if (aborted) return;
        if (json?.session_auth_disabled) {
          setAuthBypassActive(true);
          setUser((prev) => (authModeRef.current === 'guest' ? prev : prev ?? AUTH_BYPASS_USER));
        }
      } catch (err) {
        console.warn('Failed to detect authentication bypass flag from /api/config', err);
      } finally {
        if (!aborted) {
          setAuthConfigResolved(true);
        }
      }
    })();
    return () => {
      aborted = true;
    };
  }, []);

  useEffect(() => {
    if (!authBypassActive || user || authMode !== 'anonymous') {
      return;
    }
    /**
     * バイパスフラグ有効時にユーザー情報を初期化する。
     * 新規参画者向け補足: 認証をスキップする開発専用ルートを確実に起動するため、
     * ここでモックユーザーを注入する。ID トークンは保持せず、Cookie によるセッションだけを信頼する。
     */
    setUser(AUTH_BYPASS_USER);
    updateAuthMode('authenticated');
  }, [authBypassActive, user, authMode, updateAuthMode]);

  /**
   * Google から取得した ID トークンをバックエンドへ送信し、セッションを確立する。
   * 副作用: セッション Cookie 設定、ユーザー状態の更新、エラー時は状態クリア。
   * 注意: XSS 耐性を高めるため、ID トークンはローカル状態へ保持せずスコープ終了とともに破棄する。
   */
  const signIn = useCallback(async (idToken: GoogleIdToken) => {
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
      updateAuthMode('authenticated');
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
  }, [updateAuthMode]);

  /**
   * セッションクッキーの破棄をブラウザへ指示する。
   * 副作用: document.cookie に Max-Age=0 の値を書き込み、後続リクエストを匿名化。
   * 備考: サーバー側が Cookie を削除できない異常時のみ利用するフォールバック手段。
   */
  const clearSessionCookie = useCallback(() => {
    if (typeof document === 'undefined') return;
    SESSION_COOKIE_NAMES.forEach((name) => {
      document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
    });
  }, []);

  /**
   * バックエンドへログアウトを通知し、クライアント側の認証情報を破棄する。
   * 副作用: ローカルストレージと Cookie を削除し、ユーザー状態を初期化。
   */
  const signOut = useCallback(async () => {
    setIsAuthenticating(true);
    setError(null);
    let fallbackRequired = false;
    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
      if (response.status !== 204 && response.status !== 200) {
        console.warn('Unexpected response when logging out', response.status);
        fallbackRequired = true;
      }
    } catch (err) {
      console.warn('Failed to notify backend about logout', err);
      fallbackRequired = true;
    } finally {
      setUser(null);
      updateAuthMode('anonymous');
      if (fallbackRequired) {
        clearSessionCookie();
      }
      setIsAuthenticating(false);
    }
  }, [clearSessionCookie, updateAuthMode]);

  const clearError = useCallback(() => setError(null), []);

  /**
   * ログイン不要で画面を閲覧するためのゲストモードへ切り替える。
   * なぜ: まず UI を体験したい利用者の入口を確保し、学習開始までのハードルを下げるため。
   */
  const enterGuestMode = useCallback(() => {
    setUser(null);
    updateAuthMode('guest');
    setError(null);
  }, [updateAuthMode]);

  /**
   * どのエンドポイントでも 401 が返った場合に、セッション切れとして扱う。
   * fetchJson は `auth:unauthorized` カスタムイベントを発火するため、ここで
   * それを監視してクライアント側状態を初期化する。
   */
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ status?: number }>).detail;
      if (detail && detail.status === 401) {
        if (authModeRef.current === 'guest') {
          return;
        }
        setUser(null);
        updateAuthMode('anonymous');
        setError('セッションの有効期限が切れました。もう一度ログインしてください。');
        // サーバ側で Cookie が既に無効なケースに備えて、クライアント側 Cookie も掃除する。
        clearSessionCookie();
      }
    };
    window.addEventListener('auth:unauthorized', handler as EventListener);
    return () => {
      window.removeEventListener('auth:unauthorized', handler as EventListener);
    };
  }, [clearSessionCookie, updateAuthMode]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      authMode,
      isGuest: authMode === 'guest',
      isAuthenticating,
      error,
      signIn,
      signOut,
      enterGuestMode,
      clearError,
      authBypassActive,
      missingClientId,
      googleClientId: clientIdRef.current,
    }),
    [
      user,
      authMode,
      isAuthenticating,
      error,
      signIn,
      signOut,
      enterGuestMode,
      clearError,
      authBypassActive,
      missingClientId,
      normalizedClientId,
    ],
  );

  const contextNode = <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;

  if (missingClientId) {
    /**
     * Google OAuth プロバイダーはクライアント ID が空のままでは初期化に失敗する。
     * 新規メンバーが遭遇しても認証 UI 自体は動作させたいので、ここでラップを省略する。
     */
    return contextNode;
  }

  return <GoogleOAuthProvider clientId={clientIdRef.current}>{contextNode}</GoogleOAuthProvider>;
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
