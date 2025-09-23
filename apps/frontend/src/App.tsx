import React, { useCallback, useEffect, useRef, useState } from 'react';
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
const MAIN_SIDE_PADDING = 20;

const calculateMainShift = (viewportWidth: number, sidebarOpen: boolean) => {
  if (!sidebarOpen) {
    return 0;
  }

  const horizontalPadding = MAIN_SIDE_PADDING * 2;
  const contentWidthClosed = Math.max(viewportWidth - horizontalPadding, 0);
  const mainWidthClosed = Math.min(MAIN_MAX_WIDTH, contentWidthClosed);
  const leftClosed =
    MAIN_SIDE_PADDING + Math.max((contentWidthClosed - mainWidthClosed) / 2, 0);

  const mainColumnWidth = Math.max(viewportWidth - SIDEBAR_WIDTH, 0);
  const contentWidthOpen = Math.max(mainColumnWidth - horizontalPadding, 0);
  const mainWidthOpen = Math.min(MAIN_MAX_WIDTH, contentWidthOpen);
  const defaultLeftOpen =
    SIDEBAR_WIDTH +
    MAIN_SIDE_PADDING +
    Math.max((contentWidthOpen - mainWidthOpen) / 2, 0);

  const minimumLeft = SIDEBAR_WIDTH + MAIN_SIDE_PADDING;
  const targetLeft = Math.max(leftClosed, minimumLeft);

  return targetLeft - defaultLeftOpen;
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
  const [mainShift, setMainShift] = useState(0);
  const sidebarToggleRef = useRef<HTMLButtonElement>(null);
  const firstSidebarItemRef = useRef<HTMLButtonElement>(null);
  const hasSidebarOpened = useRef(false);
  const layoutUpdateTimeoutRef = useRef<number | null>(null);
  const isSidebarOpenRef = useRef(isSidebarOpen);

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
    setIsSidebarOpen((prev) => !prev);

  useEffect(() => {
    isSidebarOpenRef.current = isSidebarOpen;
  }, [isSidebarOpen]);

  const applyMainShift = useCallback(() => {
    if (typeof window === 'undefined') {
      setMainShift(0);
      return;
    }
    setMainShift(calculateMainShift(window.innerWidth, isSidebarOpenRef.current));
  }, []);

  const scheduleMainShiftUpdate = useCallback(
    (delayMs: number) => {
      if (layoutUpdateTimeoutRef.current !== null) {
        window.clearTimeout(layoutUpdateTimeoutRef.current);
        layoutUpdateTimeoutRef.current = null;
      }

      if (delayMs === 0) {
        applyMainShift();
        return;
      }

      layoutUpdateTimeoutRef.current = window.setTimeout(() => {
        applyMainShift();
        layoutUpdateTimeoutRef.current = null;
      }, delayMs);
    },
    [applyMainShift],
  );

  useEffect(() => {
    scheduleMainShiftUpdate(isSidebarOpen ? 100 : 0);

    return () => {
      if (layoutUpdateTimeoutRef.current !== null) {
        window.clearTimeout(layoutUpdateTimeoutRef.current);
        layoutUpdateTimeoutRef.current = null;
      }
    };
  }, [isSidebarOpen, scheduleMainShiftUpdate]);

  useEffect(() => {
    const handleResize = () => {
      scheduleMainShiftUpdate(isSidebarOpenRef.current ? 100 : 0);
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [scheduleMainShiftUpdate]);

  const handleSelectTab = (next: Tab) => {
    setTab(next);
  };

  return (
    <SettingsProvider>
      <ModalProvider>
        <ConfirmDialogProvider>
          <NotificationsProvider>
            <div
              className={`app-shell${isSidebarOpen ? ' sidebar-open' : ''}`}
              style={{
                ['--main-max-width' as any]: `${MAIN_MAX_WIDTH}px`,
                ['--main-shift' as any]: `${mainShift}px`,
              }}
            >
              <ThemeApplier />
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
            width: 100%;
          }
          .sidebar-nav {
            display: grid;
            gap: 1rem;
            align-content: flex-start;
            padding-top: 0.5rem;
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
            position: relative;
            left: var(--main-shift);
            transition: none;
          }
          header {
            padding-top: 1rem;
          }
          .header-bar {
            padding-left: 3.5rem;
          }
          .sidebar-nav-button {
            font-size: 1rem;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1rem;
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
                          aria-expanded={isSidebarOpen}
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
              <NotificationsOverlay />
            </div>
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
