import React, { useEffect, useRef, useState } from 'react';
import { CardPanel } from './components/CardPanel';
import { SentencePanel } from './components/SentencePanel';
import { AssistPanel } from './components/AssistPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { WordPackPanel } from './components/WordPackPanel';
import { WordPackListPanel } from './components/WordPackListPanel';
import { SettingsProvider } from './SettingsContext';
import { useSettings } from './SettingsContext';

type Tab = 'card' | 'sentence' | 'assist' | 'wordpack' | 'settings';

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('wordpack');
  const [selectedWordPackId, setSelectedWordPackId] = useState<string | null>(null);
  const focusRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.altKey) {
        if (e.key === '1') setTab('card');
        if (e.key === '2') setTab('sentence');
        if (e.key === '3') setTab('assist');
        if (e.key === '4') setTab('wordpack');
        if (e.key === '5') setTab('settings');
      } else if (e.key === '/') {
        e.preventDefault();
        if (tab === 'card') {
          const cardPanel = document.getElementById('card-panel');
          if (cardPanel) (cardPanel as HTMLElement).focus();
        } else {
          focusRef.current?.focus();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (tab === 'card') {
      const cardPanel = document.getElementById('card-panel');
      if (cardPanel) (cardPanel as HTMLElement).focus();
    }
  }, [tab]);

  return (
    <SettingsProvider>
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
          <h1>WordPack</h1>
        </header>
        <nav>
          <button onClick={() => setTab('card')} aria-selected={tab === 'card'}>カード</button>
          <button onClick={() => setTab('sentence')} aria-selected={tab === 'sentence'}>文</button>
          <button onClick={() => setTab('assist')} aria-selected={tab === 'assist'}>アシスト</button>
          <button onClick={() => setTab('wordpack')} aria-selected={tab === 'wordpack'}>WordPack</button>
          <button onClick={() => setTab('settings')} aria-selected={tab === 'settings'}>設定</button>
        </nav>
        <main>
          {tab === 'card' && <CardPanel focusRef={focusRef} />}
          {tab === 'sentence' && <SentencePanel focusRef={focusRef} />}
          {tab === 'assist' && <AssistPanel focusRef={focusRef} />}
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
        </main>
        <footer>
          <small>WordPack 英語学習</small>
        </footer>
      </div>
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
