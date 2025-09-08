import React, { useEffect, useRef, useState } from 'react';
import { CardPanel } from './components/CardPanel';
import { SentencePanel } from './components/SentencePanel';
import { AssistPanel } from './components/AssistPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { WordPackPanel } from './components/WordPackPanel';
import { SettingsProvider } from './SettingsContext';

type Tab = 'card' | 'sentence' | 'assist' | 'wordpack' | 'settings';

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('card');
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
        <style>{`
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
          {tab === 'wordpack' && <WordPackPanel focusRef={focusRef} />}
          {tab === 'settings' && <SettingsPanel focusRef={focusRef} />}
        </main>
        <footer>
          <small>WordPack 英語学習</small>
        </footer>
      </div>
    </SettingsProvider>
  );
};
