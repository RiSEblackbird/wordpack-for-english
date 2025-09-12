import React, { useContext, useEffect, useState } from 'react';

export interface Settings {
  apiBase: string;
  pronunciationEnabled: boolean;
  regenerateScope: 'all' | 'examples' | 'collocations';
  autoAdvanceAfterGrade: boolean;
  requestTimeoutMs: number;
}

interface SettingsValue {
  settings: Settings;
  setSettings: React.Dispatch<React.SetStateAction<Settings>>;
}

const SettingsContext = React.createContext<SettingsValue | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<Settings>({ apiBase: '/api', pronunciationEnabled: true, regenerateScope: 'all', autoAdvanceAfterGrade: false, requestTimeoutMs: 60000 });

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
        if (!aborted && typeof json.request_timeout_ms === 'number' && Number.isFinite(json.request_timeout_ms)) {
          setSettings((prev) => ({ ...prev, requestTimeoutMs: json.request_timeout_ms }));
        }
      } catch (err) {
        // 画面に明示せず、コンソールに詳細を出す（ユーザーの運用で把握可能）
        // 要件によりここで致命として扱う場合は、エラーUI提示に変更してください。
        // eslint-disable-next-line no-console
        console.error('[Settings] /api/config の取得に失敗しました。envと同期できていません。', err);
      }
    })();
    return () => {
      aborted = true;
    };
  }, []);
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
