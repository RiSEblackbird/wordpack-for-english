import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

// --- API types ---
interface Pronunciation {
  ipa_GA?: string | null;
  ipa_RP?: string | null;
  syllables?: number | null;
  stress_index?: number | null;
  linking_notes: string[];
}

interface Sense { id: string; gloss_ja: string; patterns: string[]; register?: string | null }

interface CollocationLists { verb_object: string[]; adj_noun: string[]; prep_noun: string[] }
interface Collocations { general: CollocationLists; academic: CollocationLists }

interface ContrastItem { with: string; diff_ja: string }

interface Examples { A1: string[]; B1: string[]; C1: string[]; tech: string[] }

interface Etymology { note: string; confidence: 'low' | 'medium' | 'high' }

interface Citation { text: string; meta?: Record<string, any> }

interface WordPack {
  lemma: string;
  pronunciation: Pronunciation;
  senses: Sense[];
  collocations: Collocations;
  contrast: ContrastItem[];
  examples: Examples;
  etymology: Etymology;
  study_card: string;
  citations: Citation[];
  confidence: 'low' | 'medium' | 'high';
}

export const WordPackPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [lemma, setLemma] = useState('');
  const [data, setData] = useState<WordPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [reveal, setReveal] = useState(false);
  const [count, setCount] = useState(3);
  const abortRef = useRef<AbortController | null>(null);

  const sectionIds = useMemo(
    () => [
      { id: 'overview', label: '概要' },
      { id: 'pronunciation', label: '発音' },
      { id: 'senses', label: '語義' },
      { id: 'collocations', label: '共起' },
      { id: 'contrast', label: '対比' },
      { id: 'examples', label: '例文' },
      { id: 'etymology', label: '語源' },
      { id: 'citations', label: '引用' },
      { id: 'confidence', label: '信頼度' },
      { id: 'srs', label: 'SRSメタ' },
    ],
    []
  );

  const generate = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setData(null);
    setReveal(false);
    setCount(3);
    try {
      const res = await fetchJson<WordPack>(`${settings.apiBase}/word/pack`, {
        method: 'POST',
        body: {
          lemma: lemma.trim(),
          pronunciation_enabled: settings.pronunciationEnabled,
          regenerate_scope: settings.regenerateScope,
        },
        signal: ctrl.signal,
      });
      setData(res);
      setMsg({ kind: 'status', text: 'WordPack を生成しました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPack の生成に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  // 3秒セルフチェック: カウントダウン後に自動解除（クリックで即解除）
  useEffect(() => {
    if (!data) return;
    if (reveal) return;
    setCount(3);
    const t1 = window.setTimeout(() => setCount(2), 1000);
    const t2 = window.setTimeout(() => setCount(1), 2000);
    const t3 = window.setTimeout(() => setReveal(true), 3000);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [data, reveal]);

  useEffect(() => () => abortRef.current?.abort(), []);

  return (
    <section>
      <style>{`
        .wp-container { display: grid; grid-template-columns: minmax(220px, 260px) 1fr; gap: 1rem; }
        .wp-nav { position: sticky; top: 0; align-self: start; display: flex; flex-direction: column; gap: 0.25rem; }
        .wp-nav a { text-decoration: none; color: #06c; }
        .wp-section { padding-block: 0.25rem; border-top: 1px solid #eee; }
        .blurred { filter: blur(6px); pointer-events: none; user-select: none; }
        .selfcheck { position: relative; border: 1px dashed #aaa; padding: 0.5rem; border-radius: 6px; }
        .selfcheck-overlay { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.6); cursor: pointer; font-weight: bold; }
        .kv { display: grid; grid-template-columns: 10rem 1fr; row-gap: 0.25rem; }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
        @media (max-width: 840px) { .wp-container { grid-template-columns: 1fr; } }
      `}</style>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <input
          ref={focusRef as React.RefObject<HTMLInputElement>}
          value={lemma}
          onChange={(e) => setLemma(e.target.value)}
          placeholder="見出し語を入力"
          disabled={loading}
        />
        <button onClick={generate} disabled={loading || !lemma.trim()}>生成</button>
      </div>

      {loading && <div role="status">読み込み中…</div>}
      {msg && <div role={msg.kind}>{msg.text}</div>}

      {data && (
        <div className="wp-container">
          <nav className="wp-nav" aria-label="セクション">
            {sectionIds.map((s) => (
              <a key={s.id} href={`#${s.id}`}>{s.label}</a>
            ))}
          </nav>

          <div>
            <section id="overview" className="wp-section">
              <h3>概要</h3>
              <div className="kv">
                <div>見出し語</div>
                <div><strong>{data.lemma}</strong></div>
              </div>
              <div className="selfcheck" style={{ marginTop: '0.5rem' }}>
                <div className={!reveal ? 'blurred' : ''}>
                  <div><strong>学習カード要点</strong></div>
                  <p>{data.study_card}</p>
                </div>
                {!reveal && (
                  <div className="selfcheck-overlay" onClick={() => setReveal(true)} aria-label="セルフチェック解除">
                    <span>セルフチェック中… {count}</span>
                  </div>
                )}
              </div>
            </section>

            <section id="pronunciation" className="wp-section">
              <h3>発音</h3>
              <div className="kv mono">
                <div>IPA (GA)</div><div>{data.pronunciation?.ipa_GA ?? '-'}</div>
                <div>IPA (RP)</div><div>{data.pronunciation?.ipa_RP ?? '-'}</div>
                <div>音節数</div><div>{data.pronunciation?.syllables ?? '-'}</div>
                <div>強勢インデックス</div><div>{data.pronunciation?.stress_index ?? '-'}</div>
                <div>リンキング</div><div>{data.pronunciation?.linking_notes?.join('、') || '-'}</div>
              </div>
            </section>

            <section id="senses" className="wp-section">
              <h3>語義</h3>
              {data.senses?.length ? (
                <ol>
                  {data.senses.map((s) => (
                    <li key={s.id}>
                      <div><strong>{s.gloss_ja}</strong></div>
                      {s.patterns?.length ? <div className="mono">{s.patterns.join(' | ')}</div> : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <p>なし</p>
              )}
            </section>

            <section id="collocations" className="wp-section">
              <h3>共起</h3>
              <div>
                <h4>一般</h4>
                <div className="mono">VO: {data.collocations?.general?.verb_object?.join(', ') || '-'}</div>
                <div className="mono">Adj+N: {data.collocations?.general?.adj_noun?.join(', ') || '-'}</div>
                <div className="mono">Prep+N: {data.collocations?.general?.prep_noun?.join(', ') || '-'}</div>
              </div>
              <div>
                <h4>アカデミック</h4>
                <div className="mono">VO: {data.collocations?.academic?.verb_object?.join(', ') || '-'}</div>
                <div className="mono">Adj+N: {data.collocations?.academic?.adj_noun?.join(', ') || '-'}</div>
                <div className="mono">Prep+N: {data.collocations?.academic?.prep_noun?.join(', ') || '-'}</div>
              </div>
            </section>

            <section id="contrast" className="wp-section">
              <h3>対比</h3>
              {data.contrast?.length ? (
                <ul>
                  {data.contrast.map((c, i) => (
                    <li key={i}>
                      <span className="mono">{c.with}</span> — {c.diff_ja}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>なし</p>
              )}
            </section>

            <section id="examples" className="wp-section">
              <h3>例文</h3>
              {(['A1','B1','C1','tech'] as const).map((k) => (
                <div key={k}>
                  <h4>{k}</h4>
                  {data.examples?.[k]?.length ? (
                    <ul>
                      {data.examples[k].map((ex, i) => <li key={i}>{ex}</li>)}
                    </ul>
                  ) : <p>なし</p>}
                </div>
              ))}
            </section>

            <section id="etymology" className="wp-section">
              <h3>語源</h3>
              <p>{data.etymology?.note || '-'}</p>
              <p>確度: {data.etymology?.confidence}</p>
            </section>

            <section id="citations" className="wp-section">
              <h3>引用</h3>
              {data.citations?.length ? (
                <ol>
                  {data.citations.map((c, i) => (
                    <li key={i}>
                      <div>{c.text}</div>
                      {c.meta ? <pre className="mono" style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(c.meta, null, 2)}</pre> : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <p>なし</p>
              )}
            </section>

            <section id="confidence" className="wp-section">
              <h3>信頼度</h3>
              <p>{data.confidence}</p>
            </section>

            <section id="srs" className="wp-section">
              <h3>SRSメタ</h3>
              <p>未登録（PR2で連携予定）</p>
              <div className="kv">
                <div>repetitions</div><div>-</div>
                <div>interval_days</div><div>-</div>
                <div>due_at</div><div>-</div>
              </div>
            </section>
          </div>
        </div>
      )}
    </section>
  );
};


