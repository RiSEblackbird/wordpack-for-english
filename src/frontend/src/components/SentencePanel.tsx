import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

interface Issue { what: string; why: string; fix: string }
interface Revision { style: string; text: string }
interface MiniExercise { q: string; a: string }
interface SentenceCheckResponse { issues: Issue[]; revisions: Revision[]; exercise?: MiniExercise }

export const SentencePanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [text, setText] = useState('');
  const [data, setData] = useState<SentenceCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const checkSentence = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setData(null);
    try {
      const res = await fetchJson<SentenceCheckResponse>(`${settings.apiBase}/sentence/check`, {
        method: 'POST',
        body: { sentence: text },
        signal: ctrl.signal,
      });
      setData(res);
      setMsg({ kind: 'status', text: 'チェックしました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '文のチェックに失敗しました';
      setMsg({ kind: 'alert', text: m });
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
        disabled={loading}
      />
      <button onClick={checkSentence} disabled={loading || !text.trim()}>チェック</button>
      {loading && <div role="status">読み込み中…</div>}
      {data && (
        <div>
          <h4>指摘</h4>
          {data.issues.length ? (
            <ul>
              {data.issues.map((it, i) => (
                <li key={i}>{it.what}: {it.why} → {it.fix}</li>
              ))}
            </ul>
          ) : (
            <p>指摘なし</p>
          )}

          <h4>書き換え案</h4>
          {data.revisions.length ? (
            <ul>
              {data.revisions.map((rv, i) => (
                <li key={i}>[{rv.style}] {rv.text}</li>
              ))}
            </ul>
          ) : (
            <p>書き換え案なし</p>
          )}

          <h4>ミニ演習</h4>
          {data.exercise ? (
            <p>{data.exercise.q}</p>
          ) : (
            <p>演習なし</p>
          )}
        </div>
      )}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
