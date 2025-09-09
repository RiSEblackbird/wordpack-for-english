import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
  selectedWordPackId?: string | null;
  onWordPackGenerated?: (wordPackId: string) => void;
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

interface ExampleItem { en: string; ja: string; grammar_ja?: string }
interface Examples { A1: ExampleItem[]; B1: ExampleItem[]; C1: ExampleItem[]; tech: ExampleItem[] }

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

interface GradeResponse { ok: boolean; next_due: string }

interface ReviewStatsResponse {
  due_now: number;
  reviewed_today: number;
  recent: { id: string; front: string; back: string }[];
}

type PopularCard = { id: string; front: string; back: string };

interface CardMeta { repetitions: number; interval_days: number; due_at: string }

export const WordPackPanel: React.FC<Props> = ({ focusRef, selectedWordPackId, onWordPackGenerated }) => {
  const { settings } = useSettings();
  const [lemma, setLemma] = useState('');
  const [data, setData] = useState<WordPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [reveal, setReveal] = useState(false);
  const [count, setCount] = useState(3);
  const abortRef = useRef<AbortController | null>(null);
  const [stats, setStats] = useState<ReviewStatsResponse | null>(null);
  const [sessionStartAt] = useState<Date>(new Date());
  const [sessionReviewed, setSessionReviewed] = useState<number>(0);
  const [popular, setPopular] = useState<PopularCard[] | null>(null);
  const [cardMeta, setCardMeta] = useState<CardMeta | null>(null);
  const [currentWordPackId, setCurrentWordPackId] = useState<string | null>(null);

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
      setCurrentWordPackId(null); // 新規生成なのでIDはnull
      // SRSメタの取得
      try {
        const m = await fetchJson<CardMeta>(`${settings.apiBase}/review/card_by_lemma?lemma=${encodeURIComponent(res.lemma)}`);
        setCardMeta(m);
      } catch {
        setCardMeta(null); // 未登録
      }
      setMsg({ kind: 'status', text: 'WordPack を生成しました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPack の生成に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const grade = async (g: 0 | 1 | 2) => {
    if (!data?.lemma) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetchJson<GradeResponse>(`${settings.apiBase}/review/grade_by_lemma`, {
        method: 'POST',
        body: { lemma: data.lemma, grade: g },
        signal: ctrl.signal,
      });
      const due = new Date(res.next_due);
      setMsg({ kind: 'status', text: `採点しました（次回: ${due.toLocaleString()}）` });
      // 採点後に進捗を再取得
      await refreshStats();
      await refreshPopular();
      // 採点後のSRSメタも再取得
      try {
        const m = await fetchJson<CardMeta>(`${settings.apiBase}/review/card_by_lemma?lemma=${encodeURIComponent(data.lemma)}`);
        setCardMeta(m);
      } catch {
        setCardMeta(null);
      }
      setSessionReviewed((v) => v + 1);
      if (settings.autoAdvanceAfterGrade) {
        setData(null);
        setLemma('');
      }
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '採点に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const refreshStats = async () => {
    try {
      const res = await fetchJson<ReviewStatsResponse>(`${settings.apiBase}/review/stats`);
      setStats(res);
    } catch (e) {
      // 進捗はUX補助なので黙ってスキップ
    }
  };

  const refreshPopular = async () => {
    try {
      const res = await fetchJson<PopularCard[]>(`${settings.apiBase}/review/popular?limit=10`);
      setPopular(res);
    } catch (e) {
      // 補助情報なので黙ってスキップ
    }
  };

  const loadWordPack = async (wordPackId: string) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setData(null);
    setReveal(false);
    setCount(3);
    try {
      const res = await fetchJson<WordPack>(`${settings.apiBase}/word/packs/${wordPackId}`, {
        signal: ctrl.signal,
      });
      setData(res);
      setCurrentWordPackId(wordPackId);
      // SRSメタの取得
      try {
        const m = await fetchJson<CardMeta>(`${settings.apiBase}/review/card_by_lemma?lemma=${encodeURIComponent(res.lemma)}`);
        setCardMeta(m);
      } catch {
        setCardMeta(null); // 未登録
      }
      setMsg({ kind: 'status', text: '保存済みWordPackを読み込みました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPackの読み込みに失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const regenerateWordPack = async (wordPackId: string) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setData(null);
    setReveal(false);
    setCount(3);
    try {
      const res = await fetchJson<WordPack>(`${settings.apiBase}/word/packs/${wordPackId}/regenerate`, {
        method: 'POST',
        body: {
          pronunciation_enabled: settings.pronunciationEnabled,
          regenerate_scope: settings.regenerateScope,
        },
        signal: ctrl.signal,
      });
      setData(res);
      setCurrentWordPackId(wordPackId);
      // SRSメタの取得
      try {
        const m = await fetchJson<CardMeta>(`${settings.apiBase}/review/card_by_lemma?lemma=${encodeURIComponent(res.lemma)}`);
        setCardMeta(m);
      } catch {
        setCardMeta(null); // 未登録
      }
      setMsg({ kind: 'status', text: 'WordPackを再生成しました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPackの再生成に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshStats();
    refreshPopular();
  }, []);

  // 選択されたWordPackIDが変更された場合の処理
  useEffect(() => {
    if (selectedWordPackId && selectedWordPackId !== currentWordPackId) {
      loadWordPack(selectedWordPackId);
    }
  }, [selectedWordPackId]);

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

  // キーボードショートカット: 1/2/3 または J/K/L で ×/△/○
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!data) return;
      if (e.target && (e.target as HTMLElement).tagName === 'INPUT') return;
      if (e.target && (e.target as HTMLElement).tagName === 'TEXTAREA') return;
      const key = e.key.toLowerCase();
      if (key === '1' || key === 'j') {
        e.preventDefault();
        grade(0);
      } else if (key === '2' || key === 'k') {
        e.preventDefault();
        grade(1);
      } else if (key === '3' || key === 'l') {
        e.preventDefault();
        grade(2);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [data]);

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

      {/* 進捗ヘッダー */}
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'baseline', marginBottom: '0.5rem' }}>
        <div>
          <strong>今日</strong>:
          <span style={{ marginLeft: 6 }}>レビュー済 {stats?.reviewed_today ?? '-'} 件</span>
          <span style={{ marginLeft: 6 }}>残り {stats ? Math.max(stats.due_now, 0) : '-'} 件</span>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <details>
            <summary>ショートカット</summary>
            <small>1/J: ×, 2/K: △, 3/L: ○</small>
          </details>
          <small>
            本セッション: {sessionReviewed} 件 / 経過 {(() => {
              const ms = Date.now() - sessionStartAt.getTime();
              const m = Math.floor(ms / 60000);
              const s = Math.floor((ms % 60000) / 1000);
              return `${m}:${String(s).padStart(2, '0')}`;
            })()}
          </small>
        </div>
        <button onClick={refreshStats} disabled={loading}>進捗更新</button>
      </div>
      {stats?.recent?.length ? (
        <div style={{ marginBottom: '0.5rem' }}>
          <small>最近見た語:</small>
          <ul style={{ display: 'inline-flex', listStyle: 'none', gap: '0.75rem', padding: 0, marginLeft: 8 }}>
            {stats.recent.slice(0, 5).map((c) => (
              <li key={c.id}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(c.front); }} title={c.back}>{c.front}</a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {stats && stats.due_now === 0 && (
        <div role="status" style={{ marginBottom: '0.5rem' }}>
          セッション完了。お疲れさまでした！ 本セッション {sessionReviewed} 件 / 所要時間 {(() => {
            const ms = Date.now() - sessionStartAt.getTime();
            const m = Math.floor(ms / 60000);
            const s = Math.floor((ms % 60000) / 1000);
            return `${m}分${s}秒`;
          })()}
        </div>
      )}

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
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button onClick={() => grade(0)} disabled={loading}>× わからない (1)</button>
                <button onClick={() => grade(1)} disabled={loading}>△ あいまい (2)</button>
                <button onClick={() => grade(2)} disabled={loading}>○ できた (3)</button>
                {currentWordPackId && (
                  <button 
                    onClick={() => regenerateWordPack(currentWordPackId)} 
                    disabled={loading}
                    style={{ marginLeft: 'auto', backgroundColor: '#f0f0f0' }}
                  >
                    再生成
                  </button>
                )}
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
                <div className="mono">VO: {data.collocations?.general?.verb_object?.length ? data.collocations.general.verb_object.map((t,i) => (
                  <React.Fragment key={i}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data.collocations.general.verb_object.length - 1 ? ', ' : ''}
                  </React.Fragment>
                )) : '-'}</div>
                <div className="mono">Adj+N: {data.collocations?.general?.adj_noun?.length ? data.collocations.general.adj_noun.map((t,i) => (
                  <React.Fragment key={i}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data.collocations.general.adj_noun.length - 1 ? ', ' : ''}
                  </React.Fragment>
                )) : '-'}</div>
                <div className="mono">Prep+N: {data.collocations?.general?.prep_noun?.length ? data.collocations.general.prep_noun.map((t,i) => (
                  <React.Fragment key={i}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data.collocations.general.prep_noun.length - 1 ? ', ' : ''}
                  </React.Fragment>
                )) : '-'}</div>
              </div>
              <div>
                <h4>アカデミック</h4>
                <div className="mono">VO: {data.collocations?.academic?.verb_object?.length ? data.collocations.academic.verb_object.map((t,i) => (
                  <React.Fragment key={i}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data.collocations.academic.verb_object.length - 1 ? ', ' : ''}
                  </React.Fragment>
                )) : '-'}</div>
                <div className="mono">Adj+N: {data.collocations?.academic?.adj_noun?.length ? data.collocations.academic.adj_noun.map((t,i) => (
                  <React.Fragment key={i}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data.collocations.academic.adj_noun.length - 1 ? ', ' : ''}
                  </React.Fragment>
                )) : '-'}</div>
                <div className="mono">Prep+N: {data.collocations?.academic?.prep_noun?.length ? data.collocations.academic.prep_noun.map((t,i) => (
                  <React.Fragment key={i}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data.collocations.academic.prep_noun.length - 1 ? ', ' : ''}
                  </React.Fragment>
                )) : '-'}</div>
              </div>
            </section>

            <section id="contrast" className="wp-section">
              <h3>対比</h3>
              {data.contrast?.length ? (
                <ul>
                  {data.contrast.map((c, i) => (
                    <li key={i}>
                      <a href="#" onClick={(e) => { e.preventDefault(); setLemma(c.with); }} className="mono">{c.with}</a> — {c.diff_ja}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>なし</p>
              )}
            </section>

            {/* 簡易インデックス（最近/よく見る順） */}
            <section className="wp-section">
              <h3>インデックス</h3>
              <div>
                <h4>最近</h4>
                {stats?.recent?.length ? (
                  <ul style={{ display: 'inline-flex', listStyle: 'none', gap: '0.75rem', padding: 0 }}>
                    {stats.recent.map((c) => (
                      <li key={c.id}><a href="#" onClick={(e) => { e.preventDefault(); setLemma(c.front); }}>{c.front}</a></li>
                    ))}
                  </ul>
                ) : <p>なし</p>}
              </div>
              <div>
                <h4>よく見る</h4>
                {popular?.length ? (
                  <ul style={{ display: 'inline-flex', listStyle: 'none', gap: '0.75rem', padding: 0 }}>
                    {popular.map((c) => (
                      <li key={c.id}><a href="#" onClick={(e) => { e.preventDefault(); setLemma(c.front); }}>{c.front}</a></li>
                    ))}
                  </ul>
                ) : <p>なし</p>}
              </div>
            </section>

            <section id="examples" className="wp-section">
              <h3>例文</h3>
              {(['A1','B1','C1','tech'] as const).map((k) => (
                <div key={k}>
                  <h4>{k}</h4>
                  {data.examples?.[k]?.length ? (
                    <ul>
                      {(data.examples[k] as ExampleItem[]).map((ex: ExampleItem, i: number) => (
                        <li key={i}>
                          <div>{ex.en}</div>
                          <div style={{ color: '#555' }}>{ex.ja}</div>
                          {ex.grammar_ja ? (
                            <div style={{ color: '#6b6b6b', fontSize: '90%' }}>文法: {ex.grammar_ja}</div>
                          ) : null}
                        </li>
                      ))}
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
              {cardMeta ? (
                <div className="kv">
                  <div>repetitions</div><div>{cardMeta.repetitions}</div>
                  <div>interval_days</div><div>{cardMeta.interval_days}</div>
                  <div>due_at</div><div>{new Date(cardMeta.due_at).toLocaleString()}</div>
                </div>
              ) : (
                <>
                  <p>未登録</p>
                  <div className="kv">
                    <div>repetitions</div><div>-</div>
                    <div>interval_days</div><div>-</div>
                    <div>due_at</div><div>-</div>
                  </div>
                </>
              )}
            </section>
          </div>
        </div>
      )}
    </section>
  );
};


