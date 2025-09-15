import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { regenerateWordPackRequest } from '../lib/wordpack';
import { LoadingIndicator } from './LoadingIndicator';
import { useNotifications } from '../NotificationsContext';
import { Modal } from './Modal';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
  selectedWordPackId?: string | null;
  onWordPackGenerated?: (wordPackId: string | null) => void;
  selectedMeta?: { created_at: string; updated_at: string } | null;
}

// --- API types ---
interface Pronunciation {
  ipa_GA?: string | null;
  ipa_RP?: string | null;
  syllables?: number | null;
  stress_index?: number | null;
  linking_notes: string[];
}

interface Sense {
  id: string;
  gloss_ja: string;
  definition_ja?: string | null;
  nuances_ja?: string | null;
  term_overview_ja?: string | null;
  term_core_ja?: string | null;
  patterns: string[];
  synonyms?: string[];
  antonyms?: string[];
  register?: string | null;
  notes_ja?: string | null;
}

interface CollocationLists { verb_object: string[]; adj_noun: string[]; prep_noun: string[] }
interface Collocations { general: CollocationLists; academic: CollocationLists }

interface ContrastItem { with: string; diff_ja: string }

interface ExampleItem { en: string; ja: string; grammar_ja?: string }
interface Examples { Dev: ExampleItem[]; CS: ExampleItem[]; LLM: ExampleItem[]; Business: ExampleItem[]; Common: ExampleItem[] }

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


export const WordPackPanel: React.FC<Props> = ({ focusRef, selectedWordPackId, onWordPackGenerated, selectedMeta }) => {
  const { settings, setSettings } = useSettings();
  const { isModalOpen, setModalOpen } = useModal();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const [lemma, setLemma] = useState('');
  const [data, setData] = useState<WordPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingInfo, setLoadingInfo] = useState<{ label: string; subtext?: string } | null>(null);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [reveal, setReveal] = useState(false);
  const [count, setCount] = useState(3);
  const abortRef = useRef<AbortController | null>(null);
  const [sessionStartAt] = useState<Date>(new Date());
  const [currentWordPackId, setCurrentWordPackId] = useState<string | null>(null);
  const [model, setModel] = useState<string>('gpt-5-mini');
  const [detailOpen, setDetailOpen] = useState(false);

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '-';
    try {
      const hasTZ = /[Zz]|[+-]\d{2}:?\d{2}$/.test(dateStr);
      const s = hasTZ ? dateStr : `${dateStr}Z`;
      return new Date(s).toLocaleString('ja-JP', {
        timeZone: 'Asia/Tokyo',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      } as Intl.DateTimeFormatOptions);
    } catch {
      return dateStr;
    }
  };

  const sectionIds = useMemo(
    () => [
      { id: 'overview', label: '概要' },
      { id: 'pronunciation', label: '発音' },
      { id: 'senses', label: '語義' },
      { id: 'etymology', label: '語源' },
      { id: 'examples', label: '例文' },
      { id: 'collocations', label: '共起' },
      { id: 'contrast', label: '対比' },
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
    const l = lemma.trim();
    const notifId = addNotification({ title: `【${l}】の生成処理中...`, message: '新規のWordPackを生成しています（LLM応答の受信と解析を待機中）', status: 'progress' });
    setMsg(null);
    setData(null);
    setReveal(false);
    setCount(3);
    try {
      const res = await fetchJson<WordPack>(`${settings.apiBase}/word/pack`, {
        method: 'POST',
        body: (() => {
          const base: any = {
            lemma: lemma.trim(),
            pronunciation_enabled: settings.pronunciationEnabled,
            regenerate_scope: settings.regenerateScope,
            model,
          };
          if ((model || '').toLowerCase() === 'gpt-5-mini') {
            base.reasoning = { effort: settings.reasoningEffort || 'minimal' };
            base.text = { verbosity: settings.textVerbosity || 'medium' };
          } else {
            base.temperature = settings.temperature;
          }
          return base;
        })(),
        signal: ctrl.signal,
        timeoutMs: Math.max(settings.requestTimeoutMs, 300000),
      });
      setData(res);
      setCurrentWordPackId(null); // 新規生成なのでIDはnull
      setMsg({ kind: 'status', text: 'WordPack を生成しました' });
      updateNotification(notifId, { title: `【${res.lemma}】の生成完了！`, status: 'success', message: '新規生成が完了しました' });
      try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
      // 生成完了後に詳細モーダルを自動表示
      setDetailOpen(true);
      try { setModalOpen(true); } catch {}
      try { onWordPackGenerated?.(null); } catch {}
    } catch (e) {
      if (ctrl.signal.aborted) return;
      let m = e instanceof ApiError ? e.message : 'WordPack の生成に失敗しました';
      if (e instanceof ApiError && e.status === 0 && /aborted|timed out/i.test(e.message)) {
        m = 'タイムアウトしました（サーバ側で処理継続の可能性があります）。時間をおいて更新または保存済みを開いてください。';
      }
      setMsg({ kind: 'alert', text: m });
      updateNotification(notifId, { title: `【${l}】の生成失敗`, status: 'error', message: `新規生成に失敗しました（${m}）` });
    } finally {
      setLoading(false);
      setLoadingInfo(null);
    }
  };

  const createEmpty = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    const l2 = lemma.trim();
    const notifId = addNotification({ title: `【${l2}】の生成処理中...`, message: '空のWordPackを作成しています', status: 'progress' });
    setMsg(null);
    try {
      const res = await fetchJson<{ id: string }>(`${settings.apiBase}/word/packs`, {
        method: 'POST',
        body: { lemma: lemma.trim() },
        signal: ctrl.signal,
        timeoutMs: Math.max(settings.requestTimeoutMs, 300000),
      });
      setCurrentWordPackId(res.id);
      // 直後に保存済みWordPack詳細を読み込んで表示
      await loadWordPack(res.id);
      try { onWordPackGenerated?.(res.id); } catch {}
      try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
      // 詳細の読み込みまで完了したことを通知
      updateNotification(notifId, { title: `【${l2}】の生成完了！`, status: 'success', message: '詳細読み込み完了' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '空のWordPack作成に失敗しました';
      setMsg({ kind: 'alert', text: m });
      updateNotification(notifId, { title: `【${l2}】の生成失敗`, status: 'error', message: `空のWordPackの作成に失敗しました（${m}）` });
    } finally {
      setLoading(false);
      setLoadingInfo(null);
    }
  };

  const refreshStats = async () => {};
  const refreshPopular = async () => {};

  const loadWordPack = async (wordPackId: string) => {
    // ここでは同時に例文生成などが進行している可能性がある。
    // 保存済み詳細を閲覧するだけなので、進行中のバックグラウンド処理は中断せずに並行実行させる。
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
      setMsg({ kind: 'status', text: '保存済みWordPackを読み込みました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      let m = e instanceof ApiError ? e.message : 'WordPackの読み込みに失敗しました';
      if (e instanceof ApiError && e.status === 0 && /aborted|timed out/i.test(e.message)) {
        m = '読み込みがタイムアウトしました。時間をおいて再試行してください。';
      }
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
      setLoadingInfo(null);
    }
  };

  const regenerateWordPack = async (wordPackId: string) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    const lemma3 = data?.lemma || 'WordPack';
    setMsg(null);
    setData(null);
    setReveal(false);
    setCount(3);
    try {
      await regenerateWordPackRequest({
        apiBase: settings.apiBase,
        wordPackId,
        settings: {
          pronunciationEnabled: settings.pronunciationEnabled,
          regenerateScope: settings.regenerateScope,
          requestTimeoutMs: settings.requestTimeoutMs,
          temperature: settings.temperature,
          reasoningEffort: settings.reasoningEffort,
          textVerbosity: settings.textVerbosity,
        },
        model,
        lemma: lemma3,
        notify: { add: addNotification, update: updateNotification },
        abortSignal: ctrl.signal,
        messages: {
          progress: 'WordPackを再生成しています',
          success: '再生成が完了しました',
          failure: 'WordPackの再生成に失敗しました',
        },
      });
      // 再生成後に最新詳細を取得して反映
      const refreshed = await fetchJson<WordPack>(`${settings.apiBase}/word/packs/${wordPackId}`, {
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      setData(refreshed);
      setCurrentWordPackId(wordPackId);
      setMsg({ kind: 'status', text: 'WordPackを再生成しました' });
      try { onWordPackGenerated?.(wordPackId); } catch {}
    } catch (e) {
      if (ctrl.signal.aborted) return;
      let m = e instanceof ApiError ? e.message : 'WordPackの再生成に失敗しました';
      if (e instanceof ApiError && e.status === 0 && /aborted|timed out/i.test(e.message)) {
        m = '再生成がタイムアウトしました（サーバ側で処理継続の可能性）。時間をおいて再試行してください。';
      }
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
      setLoadingInfo(null);
    }
  };

  const deleteExample = async (category: 'Dev'|'CS'|'LLM'|'Business'|'Common', index: number) => {
    if (!currentWordPackId) return;
    if (!confirm('この例文を削除しますか？')) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      await fetchJson(`${settings.apiBase}/word/packs/${currentWordPackId}/examples/${category}/${index}`, {
        method: 'DELETE',
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      setMsg({ kind: 'status', text: '例文を削除しました' });
      // 最新状態を再取得
      await loadWordPack(currentWordPackId);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '例文の削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
      setLoadingInfo(null);
    }
  };

  const generateExamples = async (category: 'Dev'|'CS'|'LLM'|'Business'|'Common') => {
    if (!currentWordPackId) return;
    // 例文追加生成はバックグラウンド取得を許可し、モーダル閉鎖でも継続させるため
    // abortRef には紐付けずローカルで管理する
    const ctrl = new AbortController();
    setLoading(true);
    const lemma4 = data?.lemma || '(unknown)';
    const notifId = addNotification({ title: `【${lemma4}】の生成処理中...`, message: `例文（${category}）を2件追加生成しています`, status: 'progress' });
    setMsg(null);
    try {
      await fetchJson(`${settings.apiBase}/word/packs/${currentWordPackId}/examples/${category}/generate`, {
        method: 'POST',
        body: (() => {
          const base: any = { model };
          if ((model || '').toLowerCase() === 'gpt-5-mini') {
            base.reasoning = { effort: settings.reasoningEffort || 'minimal' };
            base.text = { verbosity: settings.textVerbosity || 'medium' };
          } else {
            base.temperature = settings.temperature;
          }
          return base;
        })(),
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      setMsg({ kind: 'status', text: `${category} に例文を2件追加しました` });
      updateNotification(notifId, { title: `【${lemma4}】の生成完了！`, status: 'success', message: `${category} に例文を2件追加しました` });
      await loadWordPack(currentWordPackId);
      try { onWordPackGenerated?.(currentWordPackId); } catch {}
    } catch (e) {
      if (ctrl.signal.aborted) { updateNotification(notifId, { title: `【${lemma4}】の生成失敗`, status: 'error', message: '処理を中断しました' }); return; }
      const m = e instanceof ApiError ? e.message : '例文の追加生成に失敗しました';
      setMsg({ kind: 'alert', text: m });
      updateNotification(notifId, { title: `【${lemma4}】の生成失敗`, status: 'error', message: `${category} の例文追加生成に失敗しました（${m}）` });
    } finally {
      setLoading(false);
      setLoadingInfo(null);
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


  const renderDetails = () => (
    <div className="wp-container">
      <nav className="wp-nav" aria-label="セクション">
        {sectionIds.map((s) => (
          <a key={s.id} href={`#${s.id}`}>{s.label}</a>
        ))}
        {/* 例文カテゴリへのショートカット */}
        <a
          href="#examples-Dev"
          onClick={(e) => { e.preventDefault(); document.getElementById('examples-Dev')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
        >例文: Dev</a>
        <a
          href="#examples-CS"
          onClick={(e) => { e.preventDefault(); document.getElementById('examples-CS')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
        >例文: CS</a>
        <a
          href="#examples-LLM"
          onClick={(e) => { e.preventDefault(); document.getElementById('examples-LLM')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
        >例文: LLM</a>
        <a
          href="#examples-Business"
          onClick={(e) => { e.preventDefault(); document.getElementById('examples-Business')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
        >例文: Business</a>
        <a
          href="#examples-Common"
          onClick={(e) => { e.preventDefault(); document.getElementById('examples-Common')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
        >例文: Common</a>
      </nav>

      <div>
        <section id="overview" className="wp-section">
          <h3>概要</h3>
          {selectedMeta ? (
            <div className="kv" style={{ marginBottom: '0.5rem' }}>
              <div>作成</div><div>{formatDate(selectedMeta.created_at)}</div>
              <div>更新</div><div>{formatDate(selectedMeta.updated_at)}</div>
            </div>
          ) : null}
          <div className="kv">
            <div>見出し語</div>
            <div><strong>{data!.lemma}</strong></div>
          </div>
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <strong style={{ color: 'var(--color-accent)' }}>📊 例文統計</strong>
              <span style={{ fontSize: '1.1em', fontWeight: 'bold' }}>
                総数 {(() => {
                  const total = (data!.examples?.Dev?.length || 0) + 
                               (data!.examples?.CS?.length || 0) + 
                               (data!.examples?.LLM?.length || 0) + 
                               (data!.examples?.Business?.length || 0) + 
                               (data!.examples?.Common?.length || 0);
                  return total;
                })()}件
              </span>
            </div>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.9em' }}>
              {(['Dev','CS','LLM','Business','Common'] as const).map(cat => {
                const count = data!.examples?.[cat]?.length || 0;
                return (
                  <span key={cat} style={{ 
                    display: 'inline-flex', 
                    alignItems: 'center', 
                    gap: '0.25rem',
                    padding: '0.25rem 0.5rem',
                    backgroundColor: count > 0 ? 'var(--color-accent-bg)' : 'var(--color-neutral-surface)',
                    color: count > 0 ? 'var(--color-accent)' : 'var(--color-subtle)',
                    borderRadius: '4px',
                    border: `1px solid ${count > 0 ? 'var(--color-accent)' : 'var(--color-border)'}`
                  }}>
                    <span style={{ fontWeight: 'bold' }}>{cat}</span>
                    <span style={{ fontSize: '0.85em' }}>{count}件</span>
                  </span>
                );
              })}
            </div>
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {currentWordPackId && (
              <button 
                onClick={() => regenerateWordPack(currentWordPackId)} 
                disabled={loading}
                style={{ marginLeft: 'auto', backgroundColor: 'var(--color-neutral-surface)' }}
              >
                再生成
              </button>
            )}
          </div>
          <div className="selfcheck" style={{ marginTop: '0.5rem' }}>
            <div className={!reveal ? 'blurred' : ''}>
              <div><strong>学習カード要点</strong></div>
              <p>{data!.study_card}</p>
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
            <div>IPA (GA)</div><div>{data!.pronunciation?.ipa_GA ?? '-'}</div>
            <div>IPA (RP)</div><div>{data!.pronunciation?.ipa_RP ?? '-'}</div>
            <div>音節数</div><div>{data!.pronunciation?.syllables ?? '-'}</div>
            <div>強勢インデックス</div><div>{data!.pronunciation?.stress_index ?? '-'}</div>
            <div>リンキング</div><div>{data!.pronunciation?.linking_notes?.join('、') || '-'}</div>
          </div>
        </section>

        <section id="senses" className="wp-section">
          <h3>語義</h3>
          {data!.senses?.length ? (
            <ol>
              {data!.senses.map((s) => (
                <li key={s.id}>
                  <div><strong>{s.gloss_ja}</strong></div>
                  {s.term_core_ja ? (
                    <div style={{ marginTop: 4, fontWeight: 600 }}>{s.term_core_ja}</div>
                  ) : null}
                  {s.term_overview_ja ? (
                    <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{s.term_overview_ja}</div>
                  ) : null}
                  {s.definition_ja ? (
                    <div style={{ marginTop: 4 }}>{s.definition_ja}</div>
                  ) : null}
                  {s.nuances_ja ? (
                    <div style={{ marginTop: 4, color: '#555' }}>{s.nuances_ja}</div>
                  ) : null}
                  {s.patterns?.length ? (
                    <div className="mono" style={{ marginTop: 4 }}>{s.patterns.join(' | ')}</div>
                  ) : null}
                  {(s.synonyms && s.synonyms.length) || (s.antonyms && s.antonyms.length) ? (
                    <div style={{ marginTop: 4 }}>
                      {s.synonyms?.length ? (
                        <div><span style={{ color: '#555' }}>類義:</span> {s.synonyms.join(', ')}</div>
                      ) : null}
                      {s.antonyms?.length ? (
                        <div><span style={{ color: '#555' }}>反義:</span> {s.antonyms.join(', ')}</div>
                      ) : null}
                    </div>
                  ) : null}
                  {s.register ? (
                    <div style={{ marginTop: 4 }}><span style={{ color: '#555' }}>レジスター:</span> {s.register}</div>
                  ) : null}
                  {s.notes_ja ? (
                    <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{s.notes_ja}</div>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p>なし</p>
          )}
        </section>

        <section id="etymology" className="wp-section">
          <h3>語源</h3>
          <p>{data!.etymology?.note || '-'}</p>
          <p>確度: {data!.etymology?.confidence}</p>
        </section>

        <section id="examples" className="wp-section">
          <h3>
            例文 
            <span style={{ fontSize: '0.7em', fontWeight: 'normal', color: 'var(--color-subtle)', marginLeft: '0.5rem' }}>
              (総数 {(() => {
                const total = (data!.examples?.Dev?.length || 0) + 
                             (data!.examples?.CS?.length || 0) + 
                             (data!.examples?.LLM?.length || 0) + 
                             (data!.examples?.Business?.length || 0) + 
                             (data!.examples?.Common?.length || 0);
                return total;
              })()}件)
            </span>
          </h3>
          <style>{`
            .ex-grid { display: grid; grid-template-columns: 1fr; gap: 0.75rem; }
            .ex-card { border: 1px solid var(--color-border); border-radius: 8px; padding: 0.5rem 0.75rem; background: var(--color-surface); }
            .ex-label { display: inline-block; min-width: 3em; color: var(--color-subtle); font-size: 90%; }
            .ex-en { font-weight: 600; line-height: 1.5; }
            .ex-ja { color: var(--color-text); opacity: 0.9; margin-top: 2px; line-height: 1.6; }
            .ex-grammar { color: var(--color-subtle); font-size: 90%; margin-top: 4px; white-space: pre-wrap; }
            .ex-level { font-weight: 600; margin: 0.25rem 0; color: var(--color-level); }
          `}</style>
          {(['Dev','CS','LLM','Business','Common'] as const).map((k) => (
            <div key={k} id={`examples-${k}`} style={{ marginBottom: '0.5rem' }}>
              <div className="ex-level" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{k} ({data!.examples?.[k]?.length || 0}件)</span>
                <button
                  onClick={() => generateExamples(k)}
                  disabled={!currentWordPackId || loading}
                  aria-label={`generate-examples-${k}`}
                  title={!currentWordPackId ? '保存済みWordPackのみ追加生成が可能です' : undefined}
                  style={{ fontSize: '0.85em', color: '#1565c0', border: '1px solid #1565c0', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                >
                  追加生成（2件）
                </button>
              </div>
              {data!.examples?.[k]?.length ? (
                <div className="ex-grid">
                  {(data!.examples[k] as ExampleItem[]).map((ex: ExampleItem, i: number) => (
                    <article key={i} className="ex-card" aria-label={`example-${k}-${i}`}>
                      <div className="ex-en"><span className="ex-label">[{i + 1}] 英</span> {ex.en}</div>
                      <div className="ex-ja"><span className="ex-label">訳</span> {ex.ja}</div>
                      {ex.grammar_ja ? (
                        <div className="ex-grammar"><span className="ex-label">解説</span> {ex.grammar_ja}</div>
                      ) : null}
                      {currentWordPackId ? (
                        <div style={{ marginTop: 6 }}>
                          <button
                            onClick={() => deleteExample(k, i)}
                            disabled={loading}
                            aria-label={`delete-example-${k}-${i}`}
                            style={{ fontSize: '0.85em', color: '#d32f2f', border: '1px solid #d32f2f', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                          >
                            削除
                          </button>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              ) : <p>なし</p>}
            </div>
          ))}
        </section>

        <section id="collocations" className="wp-section">
          <h3>共起</h3>
          <div>
            <h4>一般</h4>
            <div className="mono">VO: {data!.collocations?.general?.verb_object?.length ? data!.collocations.general.verb_object.map((t,i) => (
              <React.Fragment key={i}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data!.collocations.general.verb_object.length - 1 ? ', ' : ''}
              </React.Fragment>
            )) : '-'}</div>
            <div className="mono">Adj+N: {data!.collocations?.general?.adj_noun?.length ? data!.collocations.general.adj_noun.map((t,i) => (
              <React.Fragment key={i}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data!.collocations.general.adj_noun.length - 1 ? ', ' : ''}
              </React.Fragment>
            )) : '-'}</div>
            <div className="mono">Prep+N: {data!.collocations?.general?.prep_noun?.length ? data!.collocations.general.prep_noun.map((t,i) => (
              <React.Fragment key={i}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data!.collocations.general.prep_noun.length - 1 ? ', ' : ''}
              </React.Fragment>
            )) : '-'}</div>
          </div>
          <div>
            <h4>アカデミック</h4>
            <div className="mono">VO: {data!.collocations?.academic?.verb_object?.length ? data!.collocations.academic.verb_object.map((t,i) => (
              <React.Fragment key={i}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data!.collocations.academic.verb_object.length - 1 ? ', ' : ''}
              </React.Fragment>
            )) : '-'}</div>
            <div className="mono">Adj+N: {data!.collocations?.academic?.adj_noun?.length ? data!.collocations.academic.adj_noun.map((t,i) => (
              <React.Fragment key={i}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data!.collocations.academic.adj_noun.length - 1 ? ', ' : ''}
              </React.Fragment>
            )) : '-'}</div>
            <div className="mono">Prep+N: {data!.collocations?.academic?.prep_noun?.length ? data!.collocations.academic.prep_noun.map((t,i) => (
              <React.Fragment key={i}>
                <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < data!.collocations.academic.prep_noun.length - 1 ? ', ' : ''}
              </React.Fragment>
            )) : '-'}</div>
          </div>
        </section>

        <section id="contrast" className="wp-section">
          <h3>対比</h3>
          {data!.contrast?.length ? (
            <ul>
              {data!.contrast.map((c, i) => (
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

        <section id="citations" className="wp-section">
          <h3>引用</h3>
          {data!.citations?.length ? (
            <ol>
              {data!.citations.map((c, i) => (
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
          <p>{data!.confidence}</p>
        </section>

      </div>
    </div>
  );

  return (
    <section>
      <style>{`
        .wp-container { display: grid; grid-template-columns: minmax(80px, 100px) 1fr; gap: 1rem; }
        .wp-nav { position: sticky; top: 0; align-self: start; display: flex; flex-direction: column; gap: 0.25rem; }
        .wp-nav a { text-decoration: none; color: var(--color-link); font-size: 0.7em; }
        .wp-section { padding-block: 0.25rem; border-top: 1px solid var(--color-border); }
        .blurred { filter: blur(6px); pointer-events: none; user-select: none; }
        .selfcheck { position: relative; border: 1px dashed var(--color-border); padding: 0.5rem; border-radius: 6px; }
        .selfcheck-overlay { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--color-overlay-bg); cursor: pointer; font-weight: bold; }
        .kv { display: grid; grid-template-columns: 10rem 1fr; row-gap: 0.25rem; }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
        @media (max-width: 840px) { .wp-container { grid-template-columns: 1fr; } }
      `}</style>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
        <input
          ref={focusRef as React.RefObject<HTMLInputElement>}
          value={lemma}
          onChange={(e) => setLemma(e.target.value)}
          placeholder="見出し語を入力"
          disabled={loading}
        />
        <button onClick={generate} disabled={loading || !lemma.trim()}>生成</button>
        <button onClick={createEmpty} disabled={loading || !lemma.trim()} title="内容の生成を行わず、空のWordPackのみ保存">WordPackのみ作成</button>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          モデル
          <select value={model} onChange={(e) => setModel(e.target.value)} disabled={loading}>
            <option value="gpt-5-mini">gpt-5-mini</option>
            <option value="gpt-4.1-mini">gpt-4.1-mini</option>
            <option value="gpt-4o-mini">gpt-4o-mini</option>
          </select>
        </label>
        {(model || '').toLowerCase() === 'gpt-5-mini' && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              reasoning.effort
              <select
                aria-label="reasoning.effort"
                value={settings.reasoningEffort || 'minimal'}
                onChange={(e) => setSettings({ ...settings, reasoningEffort: e.target.value as any })}
                disabled={loading}
              >
                <option value="minimal">minimal</option>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              text.verbosity
              <select
                aria-label="text.verbosity"
                value={settings.textVerbosity || 'medium'}
                onChange={(e) => setSettings({ ...settings, textVerbosity: e.target.value as any })}
                disabled={loading}
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>
          </div>
        )}
      </div>

      {/* 進捗ヘッダー */}

      {/* グローバル通知に置き換えたため、パネル内のローディング表示は削除 */}
      {msg && <div role={msg.kind}>{msg.text}</div>}

      {/* 詳細表示: 生成ワークフローでは内蔵モーダル、一覧モーダル内では素の内容のみを描画 */}
      {selectedWordPackId ? (
        data ? renderDetails() : null
      ) : (
        <Modal 
          isOpen={!!data && detailOpen}
          onClose={() => { setDetailOpen(false); try { setModalOpen(false); } catch {} }}
          title="WordPack プレビュー"
        >
          {data ? renderDetails() : null}
        </Modal>
      )}
    </section>
  );
};


