import React, { useCallback, useContext, useEffect, useState } from 'react';

export interface Settings {
  apiBase: string;
  pronunciationEnabled: boolean;
  regenerateScope: 'all' | 'examples' | 'collocations';
  autoAdvanceAfterGrade: boolean;
  requestTimeoutMs: number;
  // 選択中のLLMモデル（UI全体で共有）。未設定時はサーバの既定を同期。
  model?: string;
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

type SettingsStatus = 'loading' | 'ready' | 'error';

interface SettingsErrorInfo {
  message: string;
  detail?: string;
}

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<Settings>(() => {
    const savedTheme = (() => {
      try { return localStorage.getItem('wp.theme') || undefined; } catch { return undefined; }
    })();
    const savedModel = (() => {
      try { return localStorage.getItem('wp.model') || undefined; } catch { return undefined; }
    })();
    return {
      apiBase: '/api',
      pronunciationEnabled: true,
      regenerateScope: 'all',
      autoAdvanceAfterGrade: false,
      // 初期描画直後のズレを避けるため、保守的に長めの既定値。実値は /api/config で即同期。
      requestTimeoutMs: 360000,
      model: savedModel,
      temperature: 0.6,
      reasoningEffort: 'minimal',
      textVerbosity: 'medium',
      theme: savedTheme === 'light' ? 'light' : 'dark',
    };
  });
  const [status, setStatus] = useState<SettingsStatus>('loading');
  const [errorInfo, setErrorInfo] = useState<SettingsErrorInfo | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const retrySync = useCallback(() => {
    setStatus('loading');
    setErrorInfo(null);
    setReloadToken((prev) => prev + 1);
  }, []);

  // 起動時にバックエンドの実行時設定でタイムアウトを同期
  useEffect(() => {
    let aborted = false;
    (async () => {
      try {
        const res = await fetch('/api/config', { method: 'GET' });
        if (!res.ok) {
          const bodyText = await res.text().catch(() => '');
          const hint = bodyText ? ` body=${bodyText}` : '';
          throw new Error(`Failed to load /api/config: ${res.status}${hint}`);
        }
        const json = (await res.json()) as { request_timeout_ms?: number; llm_model?: string };
        const ms = json.request_timeout_ms;
        if (!aborted && typeof ms === 'number' && Number.isFinite(ms)) {
          setSettings((prev) => ({ ...prev, requestTimeoutMs: ms }));
        }
        const m = (json as any).llm_model;
        if (!aborted && typeof m === 'string' && m) {
          setSettings((prev) => ({ ...prev, model: prev.model || m }));
        }
        if (!aborted) {
          setStatus('ready');
          setErrorInfo(null);
        }
      } catch (err) {
        if (aborted) return;
        const message = err instanceof Error ? err.message : String(err);
        const detail = err instanceof Error && err.stack ? err.stack : undefined;
        setErrorInfo({ message, detail });
        setStatus('error');
        // eslint-disable-next-line no-console
        console.error('[Settings] /api/config の取得に失敗しました。envと同期できていません。', err);
      }
    })();
    return () => {
      aborted = true;
    };
  }, [reloadToken]);
  // テーマの永続化
  useEffect(() => {
    try { localStorage.setItem('wp.theme', settings.theme); } catch { /* ignore */ }
  }, [settings.theme]);
  // モデルの永続化
  useEffect(() => {
    if (settings.model) {
      try { localStorage.setItem('wp.model', settings.model); } catch { /* ignore */ }
    }
  }, [settings.model]);
  return (
    <SettingsContext.Provider value={{ settings, setSettings }}>
      {status === 'ready' ? (
        children
      ) : (
        <div
          role={status === 'error' ? 'alert' : 'status'}
          aria-live={status === 'error' ? 'assertive' : 'polite'}
          style={{
            padding: '1.5rem',
            maxWidth: '520px',
            margin: '2rem auto',
            borderRadius: '0.75rem',
            border: status === 'error' ? '1px solid #f87171' : '1px solid #cbd5e1',
            background: status === 'error' ? '#fef2f2' : '#f8fafc',
            color: '#111827',
            lineHeight: 1.6,
            boxShadow: '0 10px 30px rgba(15, 23, 42, 0.08)'
          }}
        >
          <h2 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.2rem' }}>バックエンド設定を同期中</h2>
          {status === 'loading' && !errorInfo ? (
            <p style={{ marginBottom: 0 }}>バックエンドの `/api/config` に接続して設定を取得しています…</p>
          ) : null}
          {status === 'error' && errorInfo ? (
            <div>
              <p style={{ marginTop: 0 }}>`/api/config` から設定を取得できませんでした。バックエンドが起動しているか、ネットワーク経路をご確認ください。</p>
              <p style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace', fontSize: '0.85rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#fee2e2', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #fecaca' }}>
                エラー: {errorInfo.message}
                {errorInfo.detail ? `\n${errorInfo.detail}` : ''}
              </p>
              <button
                type="button"
                onClick={retrySync}
                style={{
                  marginTop: '1rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.45rem 1.1rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #ef4444',
                  background: '#fee2e2',
                  color: '#b91c1c',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                再試行
              </button>
            </div>
          ) : null}
        </div>
      )}
    </SettingsContext.Provider>
  );
};

export function useSettings(): SettingsValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('Settings context missing');
  return ctx;
}
