import React, { useContext, useEffect, useState } from 'react';

export interface Settings {
  apiBase: string;
  pronunciationEnabled: boolean;
  regenerateScope: 'all' | 'examples' | 'collocations';
  autoAdvanceAfterGrade: boolean;
  requestTimeoutMs: number;
  temperature: number;
  reasoningEffort?: 'minimal' | 'low' | 'medium' | 'high';
  textVerbosity?: 'low' | 'medium' | 'high';
  theme: 'light' | 'dark';
}

interface SettingsValue {
  settings: Settings;
  setSettings: React.Dispatch<React.SetStateAction<Settings>>;
}

const SettingsContext = React.createContext<SettingsValue | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<Settings>(() => {
    const savedTheme = (() => {
      try { return localStorage.getItem('wp.theme') || undefined; } catch { return undefined; }
    })();
    return {
      apiBase: '/api',
      pronunciationEnabled: true,
      regenerateScope: 'all',
      autoAdvanceAfterGrade: false,
      // 初期描画直後のズレを避けるため、保守的に長めの既定値。実値は /api/config で即同期。
      requestTimeoutMs: 360000,
      temperature: 0.6,
      reasoningEffort: 'minimal',
      textVerbosity: 'medium',
      theme: savedTheme === 'light' ? 'light' : 'dark',
    };
  });
  const [ready, setReady] = useState<boolean>(false);

  // 起動時にバックエンドの実行時設定でタイムアウトを同期
  useEffect(() => {
    let aborted = false;
    (async () => {
      try {
        const res = await fetch('/api/config', { method: 'GET' });
        if (!res.ok) {
          throw new Error(`Failed to load /api/config: ${res.status}`);
        }
        const json = (await res.json()) as { request_timeout_ms?: number };
        const ms = json.request_timeout_ms;
        if (!aborted && typeof ms === 'number' && Number.isFinite(ms)) {
          setSettings((prev) => ({ ...prev, requestTimeoutMs: ms }));
        }
      } catch (err) {
        // 画面に明示せず、コンソールに詳細を出す（ユーザーの運用で把握可能）
        // 要件によりここで致命として扱う場合は、エラーUI提示に変更してください。
        // eslint-disable-next-line no-console
        console.error('[Settings] /api/config の取得に失敗しました。envと同期できていません。', err);
      }
    })().finally(() => { if (!aborted) setReady(true); });
    return () => {
      aborted = true;
    };
  }, []);
  // テーマの永続化
  useEffect(() => {
    try { localStorage.setItem('wp.theme', settings.theme); } catch { /* ignore */ }
  }, [settings.theme]);
  if (!ready) {
    return (
      <SettingsContext.Provider value={{ settings, setSettings }}>
        <div style={{ padding: '0.5rem', opacity: 0.8 }}>Loading settings...</div>
      </SettingsContext.Provider>
    );
  }
  return (
    <SettingsContext.Provider value={{ settings, setSettings }}>
      {children}
    </SettingsContext.Provider>
  );
};

export function useSettings(): SettingsValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('Settings context missing');
  return ctx;
}
