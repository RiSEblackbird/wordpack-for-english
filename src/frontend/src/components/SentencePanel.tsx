import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SentencePanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [text, setText] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const abortRef = useRef<AbortController>();

  const checkSentence = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setResult('');
    try {
      const res = await fetch(`${settings.apiBase}/sentence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence: text }),
        signal: ctrl.signal,
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setResult(data.result || 'OK');
      setMsg({ kind: 'status', text: 'Checked' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setMsg({ kind: 'alert', text: 'Error checking sentence' });
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
        placeholder="Enter a sentence"
      />
      <button onClick={checkSentence}>Check</button>
      {loading && <div role="status">Loading…</div>}
      {result && <p>{result}</p>}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
