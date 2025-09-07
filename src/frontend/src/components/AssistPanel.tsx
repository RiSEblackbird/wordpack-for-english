import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';

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
      const res = await fetch(`${settings.apiBase}/assist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paragraph: text }),
        signal: ctrl.signal,
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setResult(data.result || '');
      setMsg({ kind: 'status', text: 'アシストしました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setMsg({ kind: 'alert', text: '段落のアシストに失敗しました' });
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
