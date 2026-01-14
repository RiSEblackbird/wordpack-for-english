import React, { useCallback, useEffect, useRef, useState } from 'react';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { flushSync } from 'react-dom';
import { SettingsPanel } from './components/SettingsPanel';
import { WordPackPanel } from './components/WordPackPanel';
import { WordPackListPanel } from './components/WordPackListPanel';
import { ExampleListPanel } from './components/ExampleListPanel';
import { ArticleImportPanel } from './components/ArticleImportPanel';
import { ArticleListPanel } from './components/ArticleListPanel';
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
const MAIN_HEADING_TEXT = 'WordPack';
const VISUALLY_HIDDEN_STYLE = `
  .visually-hidden {
    border: 0;
    clip: rect(0 0 0 0);
    clip-path: inset(50%);
    height: 1px;
    margin: -1px;
    overflow: hidden;
    padding: 0;
    position: absolute;
    white-space: nowrap;
    width: 1px;
  }
`;

const SENSITIVE_TELEMETRY_KEYS = new Set(['access_token', 'id_token', 'refresh_token', 'code', 'credential']);

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

const sanitizeTelemetryPayload = (payload: Record<string, unknown> | null | undefined): Record<string, unknown> => {
  if (!payload) {
    return {};
  }
  return Object.entries(payload).reduce<Record<string, unknown>>((acc, [key, value]) => {
    if (typeof value === 'string') {
      if (SENSITIVE_TELEMETRY_KEYS.has(key)) {
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
  credentialResponse: CredentialResponse | null | undefined,
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
        tokenResponse: sanitizeTelemetryPayload(credentialResponse as Record<string, unknown> | undefined),
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
  const [isOverlaySidebar, setIsOverlaySidebar] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const sidebarToggleRef = useRef<HTMLButtonElement>(null);
  const firstSidebarItemRef = useRef<HTMLButtonElement>(null);
  const hasSidebarOpened = useRef(false);
  /**
   * サイドバーを閉じる処理をまとめる。
   * なぜ: クリック・キーボード操作の共通導線を用意し、挙動の差分を防ぐため。
   */
  const closeSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isSidebarOpen) {
        e.preventDefault();
        closeSidebar();
        return;
      }
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
  }, [closeSidebar, isSidebarOpen]);

  useEffect(() => {
    if (isSidebarOpen) {
      hasSidebarOpened.current = true;
      firstSidebarItemRef.current?.focus();
    } else if (hasSidebarOpened.current) {
      sidebarToggleRef.current?.focus();
    }
  }, [isSidebarOpen]);

  useEffect(() => {
    /**
     * サイドバーが閉じている間は inert を付与し、aria-hidden とフォーカス可能要素の矛盾を防ぐ。
     * なぜ: 非表示の要素にフォーカスが残ると a11y 違反になるため。
     */
    const sidebar = sidebarRef.current;
    if (!sidebar) {
      return;
    }
    if (isSidebarOpen) {
      sidebar.removeAttribute('inert');
      return;
    }
    sidebar.setAttribute('inert', '');
  }, [isSidebarOpen]);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return undefined;
    }
    const mediaQuery = window.matchMedia('(max-width: 480px)');
    const updateOverlayState = () => {
      setIsOverlaySidebar(mediaQuery.matches);
    };
    updateOverlayState();
    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', updateOverlayState);
      return () => mediaQuery.removeEventListener('change', updateOverlayState);
    }
    mediaQuery.addListener(updateOverlayState);
    return () => mediaQuery.removeListener(updateOverlayState);
  }, []);

  const toggleSidebar = () =>
    flushSync(() => {
      setIsSidebarOpen((prev) => !prev);
    });

  const handleSelectTab = (next: Tab) => {
    setTab(next);
  };

  const { user, signOut, isAuthenticating, isGuest } = useAuth();
  /**
   * ノッチや角丸を持つすべての端末で固定UIが隠れないように、安全領域専用のクラスを常に付与する。
   * なぜ: env(safe-area-inset-*)は安全領域がない端末では自動的に0になるため、
   *       画面幅に依存せず全端末で適用しても問題なく、横向きやタブレット等の
   *       480px超でもノッチがある端末を確実に保護できる。
   */
  const fixedSafeAreaClass = ' safe-area-adjusted';

  /**
   * ヘッダーから即座にセッションを終了する操作を集約する。
   * なぜ: アプリ全体のどのタブにいても迷わずログアウトできる導線を提供し、
   *       共有端末での利用時に安全にセッションを閉じてもらうため。
   */
  const handleHeaderSignOut = useCallback(async () => {
    try {
      await signOut();
    } catch (error) {
      console.warn('[Header] signOut failed', error);
    }
  }, [signOut]);

  const appContent = user || isGuest ? (
    <main
      className={`app-shell${isSidebarOpen ? ' sidebar-open' : ''}`}
      style={{
        ['--main-max-width' as any]: `${MAIN_MAX_WIDTH}px`,
      }}
    >
      <style>{`
  /* テーマ変数 */
  ${VISUALLY_HIDDEN_STYLE}
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
  header, footer { padding: 0.5rem; }
  .header-bar {
    height: 50px;
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .header-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
  }
  .header-actions {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
  }
  .guest-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    border: 1px dashed rgba(37, 99, 235, 0.6);
    color: var(--color-text);
    font-weight: 700;
    font-size: 0.85rem;
    background: rgba(37, 99, 235, 0.12);
  }
  .guest-badge-fixed {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 1200;
  }
  .guest-badge-fixed.safe-area-adjusted {
    top: calc(12px + env(safe-area-inset-top));
    right: calc(12px + env(safe-area-inset-right));
  }
  body.theme-dark .guest-badge {
    border-color: rgba(147, 197, 253, 0.7);
    background: rgba(96, 165, 250, 0.18);
  }
  .logout-button {
    border: 1px solid rgba(37, 99, 235, 0.2);
    border-radius: 999px;
    padding: 0.45rem 1.1rem;
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(96, 165, 250, 0.18));
    color: var(--color-text);
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
  }
  .logout-button:hover:not(:disabled) {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.2), rgba(96, 165, 250, 0.25));
    box-shadow: 0 8px 18px -12px rgba(37, 99, 235, 0.45);
  }
  .logout-button:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  .logout-button:disabled {
    cursor: not-allowed;
    opacity: 0.65;
    box-shadow: none;
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
    top: env(safe-area-inset-top);
    left: env(safe-area-inset-left);
    z-index: 980;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    background: var(--color-surface);
    padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
  }
  .hamburger-toggle.safe-area-adjusted {
    padding: calc(0.25rem + env(safe-area-inset-top))
      calc(0.25rem + env(safe-area-inset-right))
      calc(0.25rem + env(safe-area-inset-bottom))
      calc(0.25rem + env(safe-area-inset-left));
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
    /* iPhone 15 Proのようなアドレスバー可変UIでも縦領域を確保するため、動的ビューポートを優先する。 */
    min-height: 100vh; /* 動的ビューポート未対応ブラウザのフォールバック */
    min-height: 100dvh;
  }
  .sidebar {
    width: 0;
    flex-shrink: 0;
    background: var(--color-surface);
    box-shadow: none;
    overflow: hidden;
    z-index: 1000;
  }
  .app-shell.sidebar-open .sidebar {
    box-shadow: 2px 0 20px rgba(0, 0, 0, 0.2);
    width: ${SIDEBAR_WIDTH}px;
  }
  .sidebar-content {
    /* モバイルSafariでの表示崩れを避けるため、サイドバーも動的ビューポートに合わせる。 */
    min-height: 100vh; /* 動的ビューポート未対応ブラウザのフォールバック */
    min-height: 100dvh;
    padding: 2rem 1.5rem;
    display: grid;
    width: 100%;
    box-sizing: border-box;
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
  .sidebar-backdrop {
    position: fixed;
    inset: 0;
    border: none;
    background: var(--color-inverse-overlay);
    cursor: pointer;
    z-index: 900;
  }
  .main-inner {
    display: flex;
    flex-direction: column;
    max-width: var(--main-max-width);
    width: min(100%, var(--main-max-width));
    margin: 0 auto;
    /* なぜ: サイドバーの左端を0に保ちつつ、本文だけに0.5remの余白を与えて既存の見た目を維持するため。 */
    padding: 0.5rem;
    transition: none;
  }
  header {
    padding-top: 1rem;
  }
  .header-bar {
    padding-left: 3.5rem;
  }
  @media (max-width: 430px) {
    /* モバイルでノッチ/狭幅に配慮し、ヘッダーと本文の余白を最小化する。 */
    body {
      padding-top: env(safe-area-inset-top);
      padding-bottom: env(safe-area-inset-bottom);
    }
    .header-bar {
      height: auto;
      min-height: 50px;
      flex-wrap: wrap;
      row-gap: 0.5rem;
      padding-left: calc(env(safe-area-inset-left) + 0.5rem);
    }
    /* iPhone 15 Proでヘッダーが詰まりすぎないように、タイトルサイズと行間を調整する。 */
    .header-title {
      font-size: 1.35rem;
      margin: 0;
    }
    .header-actions {
      width: 100%;
      margin-left: 0;
      flex-wrap: wrap;
      justify-content: flex-end;
      row-gap: 0.5rem;
    }
    .main-column {
      padding: 0 12px;
    }
  }
  @media (max-width: 480px) {
    .sidebar {
      position: fixed;
      top: 0;
      left: 0;
      height: 100vh; /* 動的ビューポート未対応ブラウザのフォールバック */
      height: 100dvh;
      width: min(85vw, 320px);
      transform: translateX(-100%);
      transition: transform 0.2s ease;
    }
    .app-shell.sidebar-open .sidebar {
      width: min(85vw, 320px);
      transform: translateX(0);
    }
    .main-column {
      /* 狭幅端末で左右が欠けないように、安全領域を含めて横余白を計算する。 */
      padding: 0 calc(8px + env(safe-area-inset-right));
      padding-left: calc(8px + env(safe-area-inset-left));
      width: 100%;
    }
    .sidebar-content {
      /* モバイルでは余白を縮め、内容が横にはみ出さないようにする。 */
      padding: 1rem;
    }
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
      {/* Axe の main/heading ルールを満たすため、h1 は main 直下に配置する。 */}
      <h1 className="visually-hidden">{MAIN_HEADING_TEXT}</h1>
      {isGuest ? (
        <span className={`guest-badge guest-badge-fixed${fixedSafeAreaClass}`}>ゲスト閲覧モード</span>
      ) : null}
      {isSidebarOpen && isOverlaySidebar ? (
        <>
          {/* 背面操作を遮断し、タップで閉じる導線を統一する。 */}
          <button
            type="button"
            className="sidebar-backdrop"
            aria-hidden="true"
            tabIndex={-1}
            onClick={closeSidebar}
          />
        </>
      ) : null}
      <div className="app-layout">
        <aside
          id={SIDEBAR_ID}
          className="sidebar"
          aria-label="アプリ内共通メニュー"
          aria-hidden={isSidebarOpen ? 'false' : 'true'}
          ref={sidebarRef}
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
                  className={`hamburger-button hamburger-toggle${fixedSafeAreaClass}`}
                  aria-label={isSidebarOpen ? 'メニューを閉じる' : 'メニューを開く'}
                  aria-expanded={isSidebarOpen ? 'true' : 'false'}
                  aria-controls={SIDEBAR_ID}
                  onClick={toggleSidebar}
                >
                  <HamburgerIcon />
                </button>
                <span className="header-title" aria-hidden="true">WordPack</span>
                <div className="header-actions">
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
                  {!isGuest ? (
                    <button
                      type="button"
                      className="logout-button"
                      onClick={handleHeaderSignOut}
                      disabled={isAuthenticating}
                    >
                      ログアウト
                    </button>
                  ) : null}
                </div>
              </div>
            </header>
            <section aria-label="アプリのメインコンテンツ">
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
            </section>
            <footer style={{ padding: '0.5rem', marginTop: '10rem' }}>
              <small>WordPack 英語学習</small>
            </footer>
          </div>
        </div>
      </div>
      <NotificationsOverlay />
    </main>
  ) : (
    <LoginScreen>
      <NotificationsOverlay />
    </LoginScreen>
  );

  return (
    <>
      <ThemeApplier />
      {appContent}
    </>
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
interface LoginScreenProps {
  children?: React.ReactNode;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ children }) => {
  const {
    signIn,
    isAuthenticating,
    error,
    clearError,
    missingClientId,
    authBypassActive,
    googleClientId,
    enterGuestMode,
  } = useAuth();
  const [localError, setLocalError] = useState<string | null>(null);
  const loginTitle = missingClientId ? 'Google ログインの設定が必要です' : 'WordPack にサインイン';
  const loginStyles = `
        ${VISUALLY_HIDDEN_STYLE}
        .login-shell {
          /* iPhone 15 Proのような動的ビューポートでも中央配置を維持する。 */
          min-height: 100vh; /* 動的ビューポート未対応ブラウザのフォールバック */
          min-height: 100dvh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: calc(2rem + env(safe-area-inset-top)) 2rem calc(2rem + env(safe-area-inset-bottom));
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
        .login-google-button {
          display: flex;
          justify-content: center;
        }
        .login-google-button > div {
          width: 100%;
          display: flex;
          justify-content: center;
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
        .login-guest-button {
          appearance: none;
          border-radius: 999px;
          padding: 0.75rem 1.4rem;
          font-size: 0.95rem;
          font-weight: 700;
          background: rgba(37, 99, 235, 0.12);
          color: var(--color-text);
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          border: 1px dashed rgba(37, 99, 235, 0.4);
          transition: background 0.15s ease, box-shadow 0.2s ease;
        }
        .login-guest-button:hover {
          background: rgba(37, 99, 235, 0.18);
          box-shadow: 0 10px 24px -18px rgba(37, 99, 235, 0.6);
        }
        .login-guest-button:focus-visible {
          outline: 3px solid rgba(96, 165, 250, 0.8);
          outline-offset: 3px;
        }
        body.theme-dark .login-guest-button {
          border-color: rgba(147, 197, 253, 0.55);
          background: rgba(96, 165, 250, 0.18);
        }
        body.theme-dark .login-guest-button:hover {
          background: rgba(96, 165, 250, 0.26);
        }
        @media (max-width: 430px) {
          /* iPhone 15 Proの狭幅でもカード内の情報が読みやすいように余白を調整する。 */
          .login-shell {
            padding: calc(1.5rem + env(safe-area-inset-top)) 1.25rem calc(1.5rem + env(safe-area-inset-bottom));
          }
          .login-card {
            padding: 2rem 1.5rem;
          }
          .login-title {
            font-size: 1.5rem;
          }
          .login-subtitle {
            font-size: 1rem;
          }
        }
      `;

  return (
    <main className="login-shell">
      <style>{loginStyles}</style>
      {/* Axe の main/heading ルールを満たすため、h1 は main 直下に配置する。 */}
      <h1 className="visually-hidden">{MAIN_HEADING_TEXT}</h1>
      {missingClientId ? (
        <>
          {/* クライアント ID が未設定の場合は Google の SDK を初期化できない。 */}
          <section className="login-card" role="alert" aria-live="polite">
            <h2 className="login-title">Google ログインの設定が必要です</h2>
            <p className="login-description">
              VITE_GOOGLE_CLIENT_ID が未設定のため Google のサインインを開始できません。README.md の「Google OAuth クライアントの準備」節を参照し、以下の手順で環境を整えてください。
            </p>
            <h3 className="login-subtitle">設定手順</h3>
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
            <button
              type="button"
              className="login-guest-button"
              onClick={() => {
                void enterGuestMode();
              }}
            >
              ゲスト閲覧モード
            </button>
          </section>
        </>
      ) : (
        <GoogleLoginCard
          title={loginTitle}
          isAuthenticating={isAuthenticating}
          clearError={clearError}
          error={error}
          localError={localError}
          setLocalError={setLocalError}
          signIn={signIn}
          googleClientId={googleClientId}
        />
      )}
      {children}
    </main>
  );
};

interface GoogleLoginCardProps {
  title: string;
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
  title,
  isAuthenticating,
  clearError,
  error,
  localError,
  setLocalError,
  signIn,
  googleClientId,
}) => {
  const { enterGuestMode } = useAuth();
  const handleCredentialSuccess = async (credentialResponse: CredentialResponse) => {
    /**
     * Google Identity Services から返却された credential（ID トークン）を検証に回す。
     * なぜ: credential の欠落はバックエンドでユーザーを識別できない致命的な状態だから。
     */
    const idToken = credentialResponse?.credential;
    if (!idToken) {
      console.warn('Google login succeeded without an ID token', credentialResponse);
      void sendMissingIdTokenTelemetry(googleClientId, credentialResponse);
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

  const handleCredentialError = () => {
    setLocalError('Google サインインでエラーが発生しました。時間を置いて再試行してください。');
  };

  const handleBeforeGoogleInteraction = () => {
    clearError();
    setLocalError(null);
  };

  const googleButtonTheme =
    typeof document !== 'undefined' && document.body.classList.contains('theme-dark')
      ? 'filled_black'
      : 'filled_blue';

  const combinedError = localError || error;

  return (
    <>
      <section className="login-card" role="dialog" aria-labelledby="login-title" aria-live="polite">
        <h2 id="login-title" className="login-title">{title}</h2>
        <p className="login-description">Google アカウントでログインして学習データと設定を同期します。</p>
        {combinedError ? (
          <div role="alert" className="login-error">
            {combinedError}
          </div>
        ) : null}
        <div
          className="login-google-button"
          onClickCapture={handleBeforeGoogleInteraction}
          style={{
            pointerEvents: isAuthenticating ? 'none' : 'auto',
            opacity: isAuthenticating ? 0.72 : 1,
          }}
        >
          <GoogleLogin
            onSuccess={handleCredentialSuccess}
            onError={handleCredentialError}
            useOneTap={false}
            theme={googleButtonTheme as 'filled_black' | 'filled_blue'}
            text="signin_with"
            shape="pill"
            width="320"
            locale="ja"
            context="signin"
          />
        </div>
        <p className="login-note">成功するとブラウザにセッションクッキーを保存します。</p>
        <button
          type="button"
          className="login-guest-button"
          onClick={() => {
            void enterGuestMode();
          }}
        >
          ゲスト閲覧モード
        </button>
        {isAuthenticating ? (
          <div className="login-progress">
            <LoadingIndicator label="認証処理中" subtext="Google の応答を検証しています" />
          </div>
        ) : null}
      </section>
    </>
  );
};
