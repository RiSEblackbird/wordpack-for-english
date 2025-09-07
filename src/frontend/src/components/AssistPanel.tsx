import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const AssistPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [text, setText] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const assist = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setResult('');
    try {
      const data = await fetchJson<any>(`${settings.apiBase}/text/assist`, {
        method: 'POST',
        body: { paragraph: text },
        signal: ctrl.signal,
      });
      setResult(data.result || '');
      setMsg({ kind: 'status', text: 'アシストしました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const msg = e instanceof ApiError ? e.message : '段落のアシストに失敗しました';
      setMsg({ kind: 'alert', text: msg });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return (
    <section>
      <textarea
        ref={focusRef as React.RefObject<HTMLTextAreaElement>}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="段落を入力してください"
      />
      <button onClick={assist}>アシスト</button>
      {loading && <div role="status">読み込み中…</div>}
      {result && <p>{result}</p>}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
