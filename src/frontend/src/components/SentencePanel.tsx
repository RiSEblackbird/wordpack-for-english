import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SentencePanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [text, setText] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const checkSentence = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setResult('');
    try {
      const data = await fetchJson<any>(`${settings.apiBase}/sentence/check`, {
        method: 'POST',
        body: { sentence: text },
        signal: ctrl.signal,
      });
      setResult(data.result || 'OK');
      setMsg({ kind: 'status', text: 'チェックしました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const msg = e instanceof ApiError ? e.message : '文のチェックに失敗しました';
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
      <input
        ref={focusRef as React.RefObject<HTMLInputElement>}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="英文を入力してください"
      />
      <button onClick={checkSentence}>チェック</button>
      {loading && <div role="status">読み込み中…</div>}
      {result && <p>{result}</p>}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
