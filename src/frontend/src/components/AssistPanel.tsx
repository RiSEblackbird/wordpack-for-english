import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

interface SyntaxInfo { subject?: string | null; predicate?: string | null; mods: string[] }
interface TermInfo { lemma: string; gloss_ja?: string | null; ipa?: string | null; collocation?: string | null }
interface AssistedSentence { raw: string; syntax: SyntaxInfo; terms: TermInfo[]; paraphrase?: string | null }
interface TextAssistResponse { sentences: AssistedSentence[]; summary?: string | null; citations: Record<string, any>[] }

export const AssistPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [text, setText] = useState('');
  const [data, setData] = useState<TextAssistResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const assist = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setData(null);
    try {
      const res = await fetchJson<TextAssistResponse>(`${settings.apiBase}/text/assist`, {
        method: 'POST',
        body: { paragraph: text },
        signal: ctrl.signal,
      });
      setData(res);
      setMsg({ kind: 'status', text: 'アシストしました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '段落のアシストに失敗しました';
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
      <textarea
        ref={focusRef as React.RefObject<HTMLTextAreaElement>}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="段落を入力してください"
        disabled={loading}
      />
      <button onClick={assist} disabled={loading || !text.trim()}>アシスト</button>
      {loading && <div role="status">読み込み中…</div>}
      {data && (
        <div>
          <h4>文一覧</h4>
          {data.sentences.length ? (
            <ol>
              {data.sentences.map((s, i) => (
                <li key={i}>
                  <div><strong>{s.raw}</strong></div>
                  {s.paraphrase && <div>⇄ {s.paraphrase}</div>}
                  {s.terms?.length ? (
                    <ul>
                      {s.terms.map((t, j) => (
                        <li key={j}>{t.lemma}{t.gloss_ja ? `（${t.gloss_ja}）` : ''}</li>
                      ))}
                    </ul>
                  ) : (
                    <div>用語注なし</div>
                  )}
                </li>
              ))}
            </ol>
          ) : (
            <p>文が検出されませんでした</p>
          )}

          {data.summary && (
            <>
              <h4>要約</h4>
              <p>{data.summary}</p>
            </>
          )}
        </div>
      )}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
