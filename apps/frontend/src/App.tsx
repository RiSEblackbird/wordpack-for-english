import React, { useEffect, useRef, useState } from 'react';
import { useGoogleLogin, type TokenResponse, type NonOAuthError } from '@react-oauth/google';
import { flushSync } from 'react-dom';
import { SettingsPanel } from './components/SettingsPanel';
import { WordPackPanel } from './components/WordPackPanel';
import { WordPackListPanel } from './components/WordPackListPanel';
import { ExampleListPanel } from './components/ExampleListPanel';
import { ArticleImportPanel } from './components/ArticleImportPanel';
import { ArticleListPanel } from './components/ArticleListPanel';
import { SettingsProvider } from './SettingsContext';
import { ModalProvider } from './ModalContext';
import { ConfirmDialogProvider } from './ConfirmDialogContext';
import { NotificationsProvider } from './NotificationsContext';
import { NotificationsOverlay } from './components/NotificationsOverlay';
import { useSettings } from './SettingsContext';
import { SIDEBAR_PORTAL_CONTAINER_ID } from './components/SidebarPortal';
import { SidebarPlaybackRateControl } from './components/SidebarPlaybackRateControl';
import { useAuth } from './AuthContext';
import { LoadingIndicator } from './components/LoadingIndicator';

type Tab = 'wordpack' | 'article' | 'examples' | 'settings';

const NAV_ITEMS: Array<{ key: Tab; label: string }> = [
  { key: 'wordpack', label: 'WordPack' },
  { key: 'article', label: '文章インポート' },
  { key: 'examples', label: '例文一覧' },
  { key: 'settings', label: '設定' },
];

const SIDEBAR_ID = 'app-sidebar';
const MAIN_MAX_WIDTH = 1000;
const SIDEBAR_WIDTH = 280;
const OAUTH_TELEMETRY_ENDPOINT = '/api/diagnostics/oauth-telemetry';

const SENSITIVE_TOKEN_KEYS = new Set(['access_token', 'id_token', 'refresh_token', 'code']);

/**
 * トークンやメールアドレスなどの機微情報をマスクする。
 * なぜ: 認証トラブルのテレメトリ送信時に個人情報を不用意にログへ残さないため。
 */
const sanitizeSecretForTelemetry = (value: string): string => {
  if (!value) return '***';
  if (value.length <= 4) return '***';
  return `${value.slice(0, 2)}…${value.slice(-1)}`;
};

const sanitizeEmailForTelemetry = (value: string): string => {
  const [local, domain] = value.split('@');
  if (!domain) {
    return sanitizeSecretForTelemetry(value);
  }
  if (local.length <= 2) {
    return `${local.charAt(0) || '*'}***@${domain}`;
  }
  return `${local.charAt(0)}***${local.charAt(local.length - 1)}@${domain}`;
};

const sanitizeTokenResponseForTelemetry = (
  tokenResponse: TokenResponse & { id_token?: string },
): Record<string, unknown> => {
  return Object.entries(tokenResponse).reduce<Record<string, unknown>>((acc, [key, value]) => {
    if (typeof value === 'string') {
      if (SENSITIVE_TOKEN_KEYS.has(key)) {
        acc[key] = sanitizeSecretForTelemetry(value);
      } else if (value.includes('@')) {
        acc[key] = sanitizeEmailForTelemetry(value);
      } else {
        acc[key] = value;
      }
    } else {
      acc[key] = value as unknown;
    }
    return acc;
  }, {});
};

/**
 * ID トークンが欠落した Google ログイン試行をバックエンドへ通知する。
 * 副作用: fetch が利用可能な場合に限り構造化テレメトリを POST する。
 */
const sendMissingIdTokenTelemetry = async (
  googleClientId: string,
  tokenResponse: TokenResponse & { id_token?: string },
): Promise<void> => {
  if (typeof fetch !== 'function') {
    return;
  }
  try {
    await fetch(OAUTH_TELEMETRY_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'google_login_missing_id_token',
        googleClientId,
        errorCategory: 'missing_id_token',
        tokenResponse: sanitizeTokenResponseForTelemetry(tokenResponse),
      }),
    });
  } catch (error) {
    console.warn('Failed to send OAuth telemetry for missing ID token', error);
  }
};

const HamburgerIcon: React.FC = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <line x1="4" y1="6" x2="20" y2="6" />
    <line x1="4" y1="12" x2="20" y2="12" />
    <line x1="4" y1="18" x2="20" y2="18" />
  </svg>
);

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('wordpack');
  const [selectedWordPackId, setSelectedWordPackId] = useState<string | null>(null);
  const focusRef = useRef<HTMLElement>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const sidebarToggleRef = useRef<HTMLButtonElement>(null);
  const firstSidebarItemRef = useRef<HTMLButtonElement>(null);
  const hasSidebarOpened = useRef(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.altKey) {
        if (e.key === '1') setTab('wordpack');
        if (e.key === '2') setTab('settings');
      } else if (e.key === '/') {
        e.preventDefault();
        focusRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (isSidebarOpen) {
      hasSidebarOpened.current = true;
      firstSidebarItemRef.current?.focus();
    } else if (hasSidebarOpened.current) {
      sidebarToggleRef.current?.focus();
    }
  }, [isSidebarOpen]);

  const toggleSidebar = () =>
    flushSync(() => {
      setIsSidebarOpen((prev) => !prev);
    });

  const handleSelectTab = (next: Tab) => {
    setTab(next);
  };

  const { user } = useAuth();

  const appContent = user ? (
    <div
      className={`app-shell${isSidebarOpen ? ' sidebar-open' : ''}`}
      style={{
        ['--main-max-width' as any]: `${MAIN_MAX_WIDTH}px`,
      }}
    >
      <style>{`
  /* テーマ変数 */
  body.theme-light {
    --color-bg: #ffffff;
    --color-text: #111827;
    --color-muted: #555555;
    --color-subtle: #6b7280;
    --color-border: #e5e7eb;
    --color-link: #0066cc;
    --color-surface: #ffffff;
    --color-overlay-bg: rgba(255,255,255,0.6);
    --color-inverse-overlay: rgba(0,0,0,0.5);
    --color-accent: #2563eb;
    --color-spinner-border: #cbd5e1;
    --color-spinner-top: #2563eb;
    --color-level: #2a5bd7;
    --color-neutral-surface: #f0f0f0;
  }
  body.theme-dark {
    --color-bg: #0b1220;
    --color-text: #e5e7eb;
    --color-muted: #a3a3a3;
    --color-subtle: #9ca3af;
    --color-border: #1f2937;
    --color-link: #93c5fd;
    --color-surface: #111827;
    --color-overlay-bg: rgba(0,0,0,0.5);
    --color-inverse-overlay: rgba(0,0,0,0.6);
    --color-accent: #60a5fa;
    --color-spinner-border: #374151;
    --color-spinner-top: #93c5fd;
    --color-level: #93c5fd;
    --color-neutral-surface: #374151;
  }
  body { margin: 0; background: var(--color-bg); color: var(--color-text); }
  a { color: var(--color-link); }
  main, header, footer { padding: 0.5rem; }
  .header-bar {
    height: 50px;
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .hamburger-button {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: transparent;
    color: var(--color-text);
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }
  .hamburger-toggle {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 980;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    background: var(--color-surface);
  }
  .hamburger-toggle[aria-expanded='true'] {
    box-shadow: none;
  }
  .hamburger-button:hover {
    background: var(--color-neutral-surface);
  }
  .hamburger-button:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  .app-shell {
    margin: 0 auto;
    box-sizing: border-box;
    width: 100%;
  }
  .app-layout {
    display: flex;
    min-height: 100vh;
  }
  .sidebar {
    width: 0;
    flex-shrink: 0;
    background: var(--color-surface);
    box-shadow: none;
    overflow: hidden;
  }
  .app-shell.sidebar-open .sidebar {
    box-shadow: 2px 0 20px rgba(0, 0, 0, 0.2);
  }
  .sidebar-content {
    min-height: 100vh;
    padding: 2rem 1.5rem;
    display: grid;
    width: 85%;
    gap: 1.5rem;
    /* グリッドの余白を上部に詰め、要素間を均等配置しない */
    align-content: flex-start;
  }
  .sidebar-nav {
    display: grid;
    gap: 0.2rem;
    align-content: flex-start;
    padding-top: 0.5rem;
  }
  .sidebar-controls {
    display: grid;
    gap: 1.5rem;
    align-content: flex-start;
  }
  .sidebar-section {
    display: grid;
    gap: 0.75rem;
  }
  .sidebar-section h2 {
    margin: 0;
    font-size: 1.05rem;
  }
  .sidebar-field {
    display: grid;
    gap: 0.35rem;
  }
  .sidebar-field label {
    font-size: 0.85rem;
    color: var(--color-subtle);
  }
  .sidebar-actions {
    display: grid;
    gap: 0.5rem;
  }
  .sidebar-inline {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
  }
  .main-column {
    flex: 1;
    min-width: 0;
    display: flex;
    justify-content: flex-start;
    box-sizing: border-box;
    padding: 0 20px;
  }
  .main-inner {
    display: flex;
    flex-direction: column;
    max-width: var(--main-max-width);
    width: min(100%, var(--main-max-width));
    margin: 0 auto;
    transition: none;
  }
  header {
    padding-top: 1rem;
  }
  .header-bar {
    padding-left: 3.5rem;
  }
  .sidebar-nav-button {
    font-size: 1.2rem;
    border: none;
    border-radius: 4px;
    padding: 0.3rem 0.5rem;
    text-align: left;
    background: transparent;
    color: var(--color-text);
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }
  .sidebar-nav-button:hover {
    background: var(--color-neutral-surface);
  }
  .sidebar-nav-button[aria-pressed='true'] {
    background: var(--color-accent);
    color: #ffffff;
  }
  .sidebar-nav-button:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
`}</style>
      <div className="app-layout">
        <aside
          id={SIDEBAR_ID}
          className="sidebar"
          aria-label="アプリ内共通メニュー"
          aria-hidden={isSidebarOpen ? 'false' : 'true'}
          style={{ width: isSidebarOpen ? `${SIDEBAR_WIDTH}px` : '0px' }}
        >
          <div className="sidebar-content">
            <nav className="sidebar-nav" aria-label="主要メニュー">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className="sidebar-nav-button"
                  aria-pressed={tab === item.key}
                  aria-current={tab === item.key ? 'page' : undefined}
                  onClick={() => handleSelectTab(item.key)}
                  tabIndex={isSidebarOpen ? 0 : -1}
                  ref={item.key === NAV_ITEMS[0].key ? firstSidebarItemRef : undefined}
                >
                  {item.label}
                </button>
              ))}
            </nav>
            {/* サイドバーに常時配置する音声スピード制御。UIの探索性を高めるため設定タブから移設。 */}
            <SidebarPlaybackRateControl isSidebarOpen={isSidebarOpen} />
            <div
              id={SIDEBAR_PORTAL_CONTAINER_ID}
              className="sidebar-controls"
              role="region"
              aria-label="ページ固有の操作"
            />
          </div>
        </aside>
        <div className="main-column">
          <div className="main-inner">
            <header>
              <div className="header-bar">
                <button
                  ref={sidebarToggleRef}
                  type="button"
                  className="hamburger-button hamburger-toggle"
                  aria-label={isSidebarOpen ? 'メニューを閉じる' : 'メニューを開く'}
                  aria-expanded={isSidebarOpen ? 'true' : 'false'}
                  aria-controls={SIDEBAR_ID}
                  onClick={toggleSidebar}
                >
                  <HamburgerIcon />
                </button>
                <h1>WordPack</h1>
                <a
                  href="https://github.com/RiSEblackbird/wordpack-for-english"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="GitHubリポジトリを開く"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    color: 'var(--color-text)',
                    textDecoration: 'none',
                    transition: 'opacity 0.2s ease'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.7')}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                </a>
              </div>
            </header>
            <main>
              {tab === 'wordpack' && (
                <>
                <WordPackPanel
                  focusRef={focusRef}
                  selectedWordPackId={selectedWordPackId}
                  onWordPackGenerated={(wordPackId) => setSelectedWordPackId(wordPackId)}
                />
                <hr />
                <section aria-label="保存済みWordPack一覧 セクション">
                  <WordPackListPanel />
                </section>
              </>
              )}
              {tab === 'settings' && <SettingsPanel focusRef={focusRef} />}
              {tab === 'article' && (
                <>
                <ArticleImportPanel />
                <hr />
                <ArticleListPanel />
              </>
              )}
              {tab === 'examples' && (
                <>
                <ExampleListPanel />
              </>
              )}
            </main>
            <footer style={{ padding: '0.5rem', marginTop: '10rem' }}>
              <small>WordPack 英語学習</small>
            </footer>
          </div>
        </div>
      </div>
    </div>
  ) : (
    <LoginScreen />
  );

  return (
    <SettingsProvider>
      <ModalProvider>
        <ConfirmDialogProvider>
          <NotificationsProvider>
            <ThemeApplier />
            {appContent}
            <NotificationsOverlay />
          </NotificationsProvider>
        </ConfirmDialogProvider>
      </ModalProvider>
    </SettingsProvider>
  );
};

const ThemeApplier: React.FC = () => {
  const { settings } = useSettings();
  useEffect(() => {
    const clsLight = 'theme-light';
    const clsDark = 'theme-dark';
    const body = document.body;
    body.classList.remove(clsLight, clsDark);
    body.classList.add(settings.theme === 'light' ? clsLight : clsDark);
  }, [settings.theme]);
  return null;
};

/**
 * Google ID プロバイダーでログインを誘導する初期画面。
 * 副作用: ボタンクリックで Google の認証ポップアップを開き、ID トークンを送信する。
 */
const LoginScreen: React.FC = () => {
  const {
    signIn,
    isAuthenticating,
    error,
    clearError,
    missingClientId,
    authBypassActive,
    googleClientId,
  } = useAuth();
  const [localError, setLocalError] = useState<string | null>(null);
  const loginStyles = `
        .login-shell {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          background: var(--color-bg);
          color: var(--color-text);
        }
        .login-card {
          width: min(100%, 420px);
          background: var(--color-surface);
          padding: 2.5rem 2rem;
          border-radius: 16px;
          box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
          display: grid;
          gap: 1.25rem;
          position: relative;
        }
        .login-title {
          margin: 0;
          font-size: 1.75rem;
        }
        .login-subtitle {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 700;
        }
        .login-description {
          margin: 0;
          color: var(--color-subtle);
          line-height: 1.6;
        }
        .login-guide-list {
          padding-left: 1.25rem;
          margin: 0;
          display: grid;
          gap: 0.75rem;
        }
        .login-guide-hint {
          margin: 0;
          padding: 0.75rem 1rem;
          border-radius: 8px;
          background: rgba(37, 99, 235, 0.12);
          color: var(--color-text);
          line-height: 1.5;
        }
        .login-error {
          padding: 0.75rem 1rem;
          border-radius: 8px;
          background: rgba(220, 38, 38, 0.12);
          color: #b91c1c;
          font-weight: 600;
        }
        .login-button {
          appearance: none;
          border-radius: 999px;
          padding: 0.85rem 1.6rem;
          font-size: 1rem;
          font-weight: 600;
          background: linear-gradient(135deg, rgba(37, 99, 235, 0.95), var(--color-accent, #2563eb));
          color: #ffffff;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          border: 1px solid rgba(15, 23, 42, 0.18);
          box-shadow: 0 14px 30px -18px rgba(37, 99, 235, 0.9);
          transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease;
        }
        .login-button:hover {
          filter: brightness(1.08);
          box-shadow: 0 16px 34px -18px rgba(37, 99, 235, 0.95);
        }
        .login-button:focus-visible {
          outline: 3px solid rgba(96, 165, 250, 0.8);
          outline-offset: 3px;
        }
        .login-button:disabled {
          cursor: not-allowed;
          opacity: 0.78;
          box-shadow: none;
        }
        body.theme-dark .login-button {
          background: linear-gradient(135deg, rgba(96, 165, 250, 0.95), var(--color-accent, #60a5fa));
          border-color: rgba(148, 163, 184, 0.45);
          box-shadow: 0 16px 36px -20px rgba(59, 130, 246, 0.75);
        }
        body.theme-dark .login-button:hover {
          box-shadow: 0 18px 40px -20px rgba(56, 189, 248, 0.8);
        }
        .login-button__icon {
          display: inline-flex;
          width: 2rem;
          height: 2rem;
          border-radius: 50%;
          align-items: center;
          justify-content: center;
          background: #ffffff;
          box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
        }
        body.theme-dark .login-button__icon {
          background: #ffffff;
          box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.32);
        }
        .login-button__label {
          display: inline-flex;
          align-items: center;
          font-weight: 700;
          letter-spacing: 0.01em;
        }
        .login-note {
          margin: 0;
          color: var(--color-muted);
          font-size: 0.9rem;
        }
        .login-progress {
          display: flex;
          justify-content: center;
        }
      `;

  if (missingClientId) {
    /**
     * クライアント ID が未設定の場合は Google の SDK を初期化できない。
     * この分岐ではトラブルシューティング手順を案内し、新規メンバーの迷子を防ぐ。
     */
    return (
      <div className="login-shell">
        <style>{loginStyles}</style>
        <section className="login-card" role="alert" aria-live="polite">
          <h1 className="login-title">Google ログインの設定が必要です</h1>
          <p className="login-description">
            VITE_GOOGLE_CLIENT_ID が未設定のため Google のサインインを開始できません。README.md の「Google OAuth クライアントの準備」節を参照し、以下の手順で環境を整えてください。
          </p>
          <h2 className="login-subtitle">設定手順</h2>
          <ol className="login-guide-list">
            <li>`apps/frontend/.env` に VITE_GOOGLE_CLIENT_ID=（Google Cloud Console で発行したクライアント ID）を記載する。</li>
            <li>`apps/backend/.env` や `.env` も同じクライアント ID を設定し、バックエンドと整合させる。</li>
            <li>設定後にフロントエンド開発サーバーを再起動し、ブラウザのキャッシュを削除して再読み込みする。</li>
          </ol>
          <p className="login-guide-hint">
            {authBypassActive
              ? '開発用の認証バイパスが有効なため、このままでもダミーアカウントで利用可能です。正式な OAuth を確認したい場合のみ上記手順を実施してください。'
              : '開発用の認証バイパスが無効な環境では、上記手順を完了するまでアプリへサインインできません。環境変数を設定後に再度アクセスしてください。'}
          </p>
        </section>
      </div>
    );
  }

  return (
    <GoogleLoginCard
      loginStyles={loginStyles}
      isAuthenticating={isAuthenticating}
      clearError={clearError}
      error={error}
      localError={localError}
      setLocalError={setLocalError}
      signIn={signIn}
      googleClientId={googleClientId}
    />
  );
};

interface GoogleLoginCardProps {
  loginStyles: string;
  isAuthenticating: boolean;
  clearError: () => void;
  error: string | null;
  localError: string | null;
  setLocalError: React.Dispatch<React.SetStateAction<string | null>>;
  signIn: (idToken: string) => Promise<void>;
  googleClientId: string;
}

/**
 * Google OAuth フローを扱うログインカード。
 * なぜ: 認証フローの副作用（ID トークン検証やエラーメッセージ表示）を一箇所に閉じ込め、新規メンバーが挙動を追いやすくする。
 */
const GoogleLoginCard: React.FC<GoogleLoginCardProps> = ({
  loginStyles,
  isAuthenticating,
  clearError,
  error,
  localError,
  setLocalError,
  signIn,
  googleClientId,
}) => {
  const handleTokenSuccess = async (tokenResponse: TokenResponse & { id_token?: string }) => {
    /**
     * Google Identity Services の OAuth フローで得られたトークンレスポンスを精査する。
     * なぜ: access_token のみではバックエンドがユーザーを特定できないため、必須の ID トークンを確認する。
     */
    const idToken = tokenResponse.id_token;
    if (!idToken) {
      console.warn('Google login succeeded without an ID token', tokenResponse);
      void sendMissingIdTokenTelemetry(googleClientId, tokenResponse);
      setLocalError('ID トークンを取得できませんでした。ブラウザを更新して再試行してください。');
      return;
    }
    try {
      await signIn(idToken);
      setLocalError(null);
    } catch (err) {
      console.warn('Sign-in request rejected', err);
    }
  };

  const handleOAuthError = () => {
    setLocalError('Google サインインでエラーが発生しました。時間を置いて再試行してください。');
  };

  const handleNonOAuthError = (nonOAuthError: NonOAuthError) => {
    console.error('Failed to initiate Google login flow due to a non-OAuth error', nonOAuthError);
    setLocalError('Google サインインを開始できませんでした。ブラウザのポップアップ設定を確認してください。');
  };

  /**
   * Google の OAuth ログインフローを開始するための関数を初期化する。
   * 副作用: 認証スコープとエラーハンドリングを一元化し、保守メンバーが仕様差異を見落とさないようにする。
   */
  const startGoogleLogin = useGoogleLogin({
    flow: 'implicit',
    scope: 'openid email profile',
    /**
     * GIS から ID トークンを必ず受け取るよう明示する。
     * なぜ: access_token のみではバックエンドがユーザーを識別できないため、implicit flow でも id_token を必須化する。
     */
    responseType: 'id_token token',
    /**
     * 共有端末などで前回のアカウントが保持されないようにする。
     * なぜ: 誤ったアカウントでのログインを防ぎ、手動でのアカウント切替手順を簡素化する。
     */
    prompt: 'select_account',
    onSuccess: handleTokenSuccess,
    onError: handleOAuthError,
    onNonOAuthError: handleNonOAuthError,
  });

  /**
   * ログインボタン押下時に Google のポップアップを開く。
   * 副作用: 直前のエラー表示をクリアし、新しいログインフローを開始する。
   */
  const handleLoginClick = () => {
    clearError();
    setLocalError(null);
    try {
      startGoogleLogin();
    } catch (err) {
      console.error('Failed to start Google login flow', err);
      setLocalError('Google サインインを開始できませんでした。ブラウザのポップアップ設定を確認してください。');
    }
  };

  const combinedError = localError || error;

  return (
    <div className="login-shell">
      <style>{loginStyles}</style>
      <section className="login-card" role="dialog" aria-labelledby="login-title" aria-live="polite">
        <h1 id="login-title" className="login-title">WordPack にサインイン</h1>
        <p className="login-description">Google アカウントでログインして学習データと設定を同期します。</p>
        {combinedError ? (
          <div role="alert" className="login-error">
            {combinedError}
          </div>
        ) : null}
        {/* Googleのブランドカラーを示すアイコンを表示して、ボタンを視認しやすくする */}
        <button
          type="button"
          className="login-button"
          onClick={handleLoginClick}
          disabled={isAuthenticating}
        >
          <span className="login-button__icon" aria-hidden="true">
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path d="M18.64 10.2045C18.64 9.56636 18.5827 8.95272 18.4764 8.36363H10V11.8454H14.92C14.7082 12.9704 14.0927 13.9236 13.1395 14.5636V16.9545H15.9564C17.6582 15.3636 18.64 12.9909 18.64 10.2045Z" fill="#4285F4" />
              <path d="M10 19C12.43 19 14.4673 18.1945 15.9564 16.9545L13.1395 14.5636C12.3286 15.1064 11.2714 15.4318 10 15.4318C7.65547 15.4318 5.67184 13.8236 4.96475 11.6982H2.04285V14.1728C3.52284 17.1818 6.52284 19 10 19Z" fill="#34A853" />
              <path d="M4.96474 11.6982C4.78474 11.1554 4.68293 10.5727 4.68293 9.97726C4.68293 9.38182 4.78474 8.79999 4.96474 8.25726V5.78272H2.04284C1.47556 6.90908 1.14284 8.20453 1.14284 9.57725C1.14284 10.95 1.47556 12.2454 2.04284 13.3718L4.96474 11.6982Z" fill="#FBBC05" />
              <path d="M10 4.56818C11.3854 4.56818 12.6218 5.04545 13.5882 5.95909L16.0264 3.52091C14.4645 2.04545 12.4273 1.13636 10 1.13636C6.52284 1.13636 3.52284 2.95455 2.04285 5.78273L4.96475 8.25727C5.67184 6.13182 7.65547 4.56818 10 4.56818Z" fill="#EA4335" />
            </svg>
          </span>
          <span className="login-button__label">Googleでログイン</span>
        </button>
        <p className="login-note">成功するとブラウザにセッションクッキーを保存します。</p>
        {isAuthenticating ? (
          <div className="login-progress">
            <LoadingIndicator label="認証処理中" subtext="Google の応答を検証しています" />
          </div>
        ) : null}
      </section>
    </div>
  );
};
