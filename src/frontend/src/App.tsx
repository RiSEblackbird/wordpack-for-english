import React, { useEffect, useRef, useState } from 'react';
import { SettingsPanel } from './components/SettingsPanel';
import { WordPackPanel } from './components/WordPackPanel';
import { WordPackListPanel } from './components/WordPackListPanel';
import { ArticleImportPanel } from './components/ArticleImportPanel';
import { ArticleListPanel } from './components/ArticleListPanel';
import { SettingsProvider } from './SettingsContext';
import { ModalProvider } from './ModalContext';
import { NotificationsProvider } from './NotificationsContext';
import { NotificationsOverlay } from './components/NotificationsOverlay';
import { useSettings } from './SettingsContext';

type Tab = 'wordpack' | 'article' | 'settings';

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('wordpack');
  const [selectedWordPackId, setSelectedWordPackId] = useState<string | null>(null);
  const focusRef = useRef<HTMLElement>(null);

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

  useEffect(() => {}, [tab]);

  return (
    <SettingsProvider>
      <ModalProvider>
        <NotificationsProvider>
        <div>
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
          body { background: var(--color-bg); color: var(--color-text); }
          a { color: var(--color-link); }
          nav { display: flex; gap: 0.5rem; }
          nav button[aria-selected='true'] { font-weight: bold; }
          main, header, footer, nav { padding: 0.5rem; }
        `}</style>
        <header>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
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
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
            >
              <svg 
                width="24" 
                height="24" 
                viewBox="0 0 24 24" 
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            </a>
          </div>
        </header>
        <nav>
          <button onClick={() => setTab('wordpack')} aria-selected={tab === 'wordpack'}>WordPack</button>
          <button onClick={() => setTab('article')} aria-selected={tab === 'article'}>文章インポート</button>
          <button onClick={() => setTab('settings')} aria-selected={tab === 'settings'}>設定</button>
        </nav>
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
        </main>
        <footer>
          <small>WordPack 英語学習</small>
        </footer>
          <NotificationsOverlay />
        </div>
        </NotificationsProvider>
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
