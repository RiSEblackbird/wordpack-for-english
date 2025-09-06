import React, { useEffect, useRef, useState } from 'react';
import { CardPanel } from './components/CardPanel';
import { SentencePanel } from './components/SentencePanel';
import { AssistPanel } from './components/AssistPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { SettingsProvider } from './SettingsContext';

type Tab = 'card' | 'sentence' | 'assist' | 'settings';

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>('card');
  const focusRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.altKey) {
        if (e.key === '1') setTab('card');
        if (e.key === '2') setTab('sentence');
        if (e.key === '3') setTab('assist');
        if (e.key === '4') setTab('settings');
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
          <button onClick={() => setTab('card')} aria-selected={tab === 'card'}>Cards</button>
          <button onClick={() => setTab('sentence')} aria-selected={tab === 'sentence'}>Sentence</button>
          <button onClick={() => setTab('assist')} aria-selected={tab === 'assist'}>Assist</button>
          <button onClick={() => setTab('settings')} aria-selected={tab === 'settings'}>Settings</button>
        </nav>
        <main>
          {tab === 'card' && <CardPanel focusRef={focusRef} />}
          {tab === 'sentence' && <SentencePanel focusRef={focusRef} />}
          {tab === 'assist' && <AssistPanel focusRef={focusRef} />}
          {tab === 'settings' && <SettingsPanel focusRef={focusRef} />}
        </main>
        <footer>
          <small>WordPack for English</small>
        </footer>
      </div>
    </SettingsProvider>
  );
};
