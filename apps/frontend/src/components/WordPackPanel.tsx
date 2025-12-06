import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { useConfirmDialog } from '../ConfirmDialogContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { useWordPack, ExampleItem, Examples, WordPack } from '../hooks/useWordPack';
import { useWordPackForm } from '../hooks/useWordPackForm';
import { LoadingIndicator } from './LoadingIndicator';
import { useNotifications } from '../NotificationsContext';
import { Modal } from './Modal';
import { formatDateJst } from '../lib/date';
import { TTSButton } from './TTSButton';
import { SidebarPortal } from './SidebarPortal';
import { highlightLemma } from '../lib/highlight';
import { LemmaExplorerWindow } from './LemmaExplorerWindow';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
  selectedWordPackId?: string | null;
  onWordPackGenerated?: (wordPackId: string | null) => void;
  selectedMeta?: { created_at: string; updated_at: string } | null;
  onStudyProgressRecorded?: (payload: { wordPackId: string; checked_only_count: number; learned_count: number }) => void;
}

interface LemmaLookupResponseData {
  found: boolean;
  id?: string | null;
  lemma?: string | null;
  sense_title?: string | null;
}

interface LemmaExplorerState {
  lemma: string;
  senseTitle?: string | null;
  wordPackId: string;
  status: 'loading' | 'ready' | 'error';
  data?: WordPack | null;
  errorMessage?: string | null;
  minimized: boolean;
  width: number;
}


export const WordPackPanel: React.FC<Props> = ({ focusRef, selectedWordPackId, onWordPackGenerated, selectedMeta, onStudyProgressRecorded }) => {
  const { settings, setSettings } = useSettings();
  const { isModalOpen, setModalOpen } = useModal();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const confirmDialog = useConfirmDialog();
  const {
    apiBase,
    pronunciationEnabled,
    regenerateScope,
    requestTimeoutMs,
    temperature,
  } = settings;
  const {
    lemma,
    setLemma,
    lemmaValidation,
    model,
    showAdvancedModelOptions,
    handleChangeModel,
    advancedSettings,
  } = useWordPackForm({ settings, setSettings });
  const [lemmaExplorer, setLemmaExplorer] = useState<LemmaExplorerState | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const lemmaCacheRef = useRef<Map<string, LemmaLookupResponseData>>(new Map());
  const lemmaActionRef = useRef<{
    tooltip: HTMLElement;
    aborter: AbortController | null;
    outsideHandler?: (ev: MouseEvent) => void;
    keyHandler?: (ev: KeyboardEvent) => void;
    blockHandler?: (ev: Event) => void;
  } | null>(null);
  const {
    // WordPackの取得・生成などの副作用処理はカスタムフックに委譲し、UIは状態の受け取りに集中する。
    aiMeta,
    currentWordPackId,
    data,
    loading,
    progressUpdating,
    message,
    setStatusMessage,
    generateWordPack,
    createEmptyWordPack,
    loadWordPack,
    regenerateWordPack,
    deleteExample: deleteExampleFromHook,
    generateExamples: generateExamplesFromHook,
    recordStudyProgress,
  } = useWordPack({ model, onWordPackGenerated, onStudyProgressRecorded });
  const [reveal, setReveal] = useState(false);
  const [count, setCount] = useState(3);
  const mountedRef = useRef(true);
  const isInModalView = Boolean(selectedWordPackId) || (Boolean(data) && detailOpen);
  const isLemmaValid = lemmaValidation.valid;
  const normalizedLemma = lemmaValidation.normalizedLemma;

  const detachLemmaActionTooltip = useCallback(() => {
    const active = lemmaActionRef.current;
    if (!active) return;
    const { tooltip, aborter, outsideHandler, keyHandler, blockHandler } = active;
    if (aborter) {
      try { aborter.abort(); } catch {}
    }
    if (outsideHandler) document.removeEventListener('click', outsideHandler, true);
    if (keyHandler) tooltip.removeEventListener('keydown', keyHandler);
    if (blockHandler) tooltip.removeEventListener('pointerdown', blockHandler, true);
    if (tooltip.isConnected) tooltip.remove();
    lemmaActionRef.current = null;
  }, []);

  const normalizeWordPack = useCallback(
    (wp: WordPack): WordPack => ({
      ...wp,
      checked_only_count: wp.checked_only_count ?? 0,
      learned_count: wp.learned_count ?? 0,
    }),
    [],
  );

  const ensureLemmaCache = useCallback((): Map<string, LemmaLookupResponseData> => {
    if (typeof window === 'undefined') {
      return lemmaCacheRef.current;
    }
    const w = window as typeof window & { __lemmaCache?: Map<string, LemmaLookupResponseData> };
    if (!w.__lemmaCache) {
      w.__lemmaCache = lemmaCacheRef.current;
    }
    lemmaCacheRef.current = w.__lemmaCache;
    return lemmaCacheRef.current;
  }, []);

  const openLemmaExplorer = useCallback(
    async (raw: string) => {
      const target = raw.trim();
      if (!target) return;
      const cache = ensureLemmaCache();
      const key = `lemma:${target.toLowerCase()}`;
      let info = cache.get(key);
      if (!info) {
        try {
          info = await fetchJson<LemmaLookupResponseData>(`${apiBase}/word/lemma/${encodeURIComponent(target)}`, {
            timeoutMs: requestTimeoutMs,
          });
        } catch {
          info = { found: false };
        }
        cache.set(key, info);
      }
      if (!info || !info.found || !info.id) {
        setStatusMessage({ kind: 'alert', text: `「${target}」のWordPackは保存されていません` });
        return;
      }
      if (!mountedRef.current) return;
      setLemmaExplorer((prev) => ({
        lemma: info!.lemma || target,
        senseTitle: info!.sense_title ?? null,
        wordPackId: info!.id!,
        status: 'loading',
        data: prev && prev.wordPackId === info!.id ? prev.data : null,
        errorMessage: null,
        minimized: false,
        width: prev?.width ?? 360,
      }));
      try {
        const detail = await fetchJson<WordPack>(`${apiBase}/word/packs/${info.id}`, {
          timeoutMs: requestTimeoutMs,
        });
        if (!mountedRef.current) return;
        setLemmaExplorer((prev) => {
          if (!prev || prev.wordPackId !== info!.id) return prev;
          return {
            ...prev,
            status: 'ready',
            senseTitle: (detail.sense_title || prev.senseTitle) ?? null,
            data: normalizeWordPack(detail),
            errorMessage: null,
          };
        });
      } catch (error) {
        if (!mountedRef.current) return;
        setLemmaExplorer((prev) => {
          if (!prev || prev.wordPackId !== info!.id) return prev;
          return {
            ...prev,
            status: 'error',
            errorMessage: error instanceof Error ? error.message : null,
          };
        });
      }
    },
    [apiBase, ensureLemmaCache, normalizeWordPack, requestTimeoutMs],
  );

  const triggerUnknownLemmaGeneration = useCallback(async (lemmaText: string) => {
    const trimmed = lemmaText.trim();
    if (!trimmed) return false;
    detachLemmaActionTooltip();
    setReveal(false);
    setCount(3);
    await generateWordPack(trimmed);
    try {
      const cache = ensureLemmaCache();
      cache.delete(`lemma:${trimmed.toLowerCase()}`);
    } catch {}
    openLemmaExplorer(trimmed);
    return true;
  }, [detachLemmaActionTooltip, ensureLemmaCache, generateWordPack, openLemmaExplorer, setCount, setReveal]);

  const showAdvancedModelOptions = useMemo(() => {
    const lower = (model || '').toLowerCase();
    return lower === 'gpt-5-mini' || lower === 'gpt-5-nano';
  }, [model]);

  const handleChangeModel = useCallback(
    (value: string) => {
      setModel(value);
      setSettings((prev) => ({ ...prev, model: value }));
    },
    [setSettings],
  );

  const closeLemmaExplorer = useCallback(() => setLemmaExplorer(null), []);

  const minimizeLemmaExplorer = useCallback(
    () => setLemmaExplorer((prev) => (prev ? { ...prev, minimized: true } : prev)),
    [],
  );

  const restoreLemmaExplorer = useCallback(
    () => setLemmaExplorer((prev) => (prev ? { ...prev, minimized: false } : prev)),
    [],
  );

  const resizeLemmaExplorer = useCallback(
    (nextWidth: number) => setLemmaExplorer((prev) => (prev ? { ...prev, width: nextWidth } : prev)),
    [],
  );

  const handleExampleActivation = useCallback(
    (event: React.MouseEvent<HTMLDivElement> | React.KeyboardEvent<HTMLDivElement>) => {
      if ('key' in event) {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
      }
      const container = event.currentTarget;
      const target = event.target as HTMLElement;
      const highlight = target.closest('span.lemma-highlight') as HTMLElement | null;
      if (highlight) {
        const lemmaAttr = highlight.getAttribute('data-lemma') || highlight.textContent?.trim();
        if (lemmaAttr) openLemmaExplorer(lemmaAttr);
        return;
      }
      const token = target.closest('span.lemma-token') as HTMLElement | null;
      if (token) {
        const lemmaMatch = token.getAttribute('data-lemma-match');
        if (lemmaMatch) {
          openLemmaExplorer(lemmaMatch);
          return;
        }
        const pendingLemma = token.getAttribute('data-pending-lemma') || container.getAttribute('data-pending-lemma');
        if (pendingLemma && pendingLemma.trim()) {
          const trimmed = pendingLemma.trim();
          container.removeAttribute('data-pending-lemma');
          container.removeAttribute('data-last-lemma');
          token.removeAttribute('data-pending-lemma');
          token.classList.remove('lemma-unknown');
          detachLemmaActionTooltip();
          void triggerUnknownLemmaGeneration(trimmed);
          return;
        }
      }
      const pending = container.getAttribute('data-pending-lemma');
      if (pending && pending.trim()) {
        container.removeAttribute('data-pending-lemma');
        container.removeAttribute('data-last-lemma');
        detachLemmaActionTooltip();
        void triggerUnknownLemmaGeneration(pending);
        return;
      }
      const fallback = container.getAttribute('data-last-lemma') || container.getAttribute('data-lemma');
      if (fallback) openLemmaExplorer(fallback);
    },
    [detachLemmaActionTooltip, openLemmaExplorer, triggerUnknownLemmaGeneration],
  );

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '-';
    return formatDateJst(dateStr);
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
    ],
    []
  );

  const exampleCategories = useMemo(() => (['Dev', 'CS', 'LLM', 'Business', 'Common'] as const), []);

  const exampleStats = useMemo(
    () => {
      const counts = exampleCategories.map((category) => ({
        category,
        count: data?.examples?.[category]?.length ?? 0,
      }));
      return {
        counts,
        total: counts.reduce((sum, item) => sum + item.count, 0),
      };
    },
    [data, exampleCategories]
  );

  const packCheckedCount = data?.checked_only_count ?? 0;
  const packLearnedCount = data?.learned_count ?? 0;

  const lemmaExplorerContent = useMemo(() => {
    if (!lemmaExplorer || !lemmaExplorer.data) return null;
    const pack = lemmaExplorer.data;
    const senses = pack.senses?.slice(0, 3) ?? [];
    const exampleSummary = exampleCategories.map((category) => ({
      category,
      count: pack.examples?.[category]?.length ?? 0,
    }));
    return (
      <div className="lemma-window-meta">
        <div>
          <strong>語義タイトル</strong>
          <div>{pack.sense_title || '-'}</div>
        </div>
        <div>
          <strong>語義（上位3件）</strong>
          {senses.length ? (
            <ol>
              {senses.map((sense) => (
                <li key={sense.id}>
                  <span>{sense.gloss_ja}</span>
                  {sense.definition_ja ? (
                    <div style={{ fontSize: '0.85em', color: '#555' }}>{sense.definition_ja}</div>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p>語義情報なし</p>
          )}
        </div>
        <div>
          <strong>例文数</strong>
          <ul>
            {exampleSummary.map(({ category, count }) => (
              <li key={category}>{category}: {count}件</li>
            ))}
          </ul>
        </div>
        {pack.study_card ? (
          <div>
            <strong>学習カード</strong>
            <p>{pack.study_card}</p>
          </div>
        ) : null}
        {pack.confidence ? (
          <div>
            <strong>信頼度</strong>
            <span>{pack.confidence}</span>
          </div>
        ) : null}
      </div>
    );
  }, [lemmaExplorer, exampleCategories]);

  const handleGenerate = useCallback(async () => {
    if (!lemmaValidation.valid) {
      setStatusMessage({ kind: 'alert', text: lemmaValidation.message });
      return;
    }
    setReveal(false);
    setCount(3);
    setLemma('');
    try { focusRef.current?.focus(); } catch {}
    await generateWordPack(normalizedLemma);
  }, [focusRef, generateWordPack, lemmaValidation, normalizedLemma, setStatusMessage]);

  const handleCreateEmpty = useCallback(async () => {
    if (!lemmaValidation.valid) {
      setStatusMessage({ kind: 'alert', text: lemmaValidation.message });
      return;
    }
    setReveal(false);
    setCount(3);
    await createEmptyWordPack(normalizedLemma);
  }, [createEmptyWordPack, lemmaValidation, normalizedLemma, setStatusMessage]);

  const handleLoadWordPack = useCallback(
    async (wordPackId: string) => {
      setReveal(false);
      setCount(3);
      await loadWordPack(wordPackId);
    },
    [loadWordPack],
  );

  const handleRegenerateWordPack = useCallback(async () => {
    if (!currentWordPackId) return;
    setReveal(false);
    setCount(3);
    await regenerateWordPack(currentWordPackId, data?.lemma || 'WordPack');
  }, [currentWordPackId, data?.lemma, regenerateWordPack]);

  const handleDeleteExample = useCallback(
    async (category: 'Dev' | 'CS' | 'LLM' | 'Business' | 'Common', index: number) => {
      if (!currentWordPackId) return;
      const confirmed = await confirmDialog('例文');
      if (!confirmed) return;
      await deleteExampleFromHook(category, index);
    },
    [confirmDialog, currentWordPackId, deleteExampleFromHook],
  );

  const importArticleFromExample = async (category: 'Dev'|'CS'|'LLM'|'Business'|'Common', index: number) => {
    try {
      const ex = data?.examples?.[category]?.[index];
      if (!ex || !ex.en) {
        setStatusMessage({ kind: 'alert', text: '例文が見つかりません' });
        return;
      }
      const ctrl = new AbortController();
      const lemma5 = data?.lemma || '(unknown)';
      const notifId = addNotification({ title: `【${lemma5}】文章インポート中...`, message: '当該の例文を元に記事を生成しています', status: 'progress' });
      await fetchJson<{ id: string }>(`${apiBase}/article/import`, {
        method: 'POST',
        body: { text: ex.en },
        signal: ctrl.signal,
        timeoutMs: requestTimeoutMs,
      });
      updateNotification(notifId, { title: '文章インポート完了', status: 'success', message: '記事一覧を更新しました' });
      try { window.dispatchEvent(new CustomEvent('article:updated')); } catch {}
      setStatusMessage({ kind: 'status', text: '例文から文章インポートを実行しました' });
    } catch (e) {
      const m = e instanceof ApiError ? e.message : '文章インポートに失敗しました';
      setStatusMessage({ kind: 'alert', text: m });
    }
  };

  const copyExampleText = async (category: 'Dev' | 'CS' | 'LLM' | 'Business' | 'Common', index: number) => {
    try {
      const ex = data?.examples?.[category]?.[index];
      if (!ex || !ex.en) {
        setStatusMessage({ kind: 'alert', text: '例文が見つかりません' });
        return;
      }
      const text = ex.en;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      addNotification({ title: 'コピー完了', message: '例文をクリップボードにコピーしました', status: 'success' });
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'コピーに失敗しました';
      setStatusMessage({ kind: 'alert', text: m });
    }
  };

  const handleGenerateExamples = useCallback(
    async (category: 'Dev' | 'CS' | 'LLM' | 'Business' | 'Common') => {
      if (!currentWordPackId) return;
      setReveal(false);
      setCount(3);
      await generateExamplesFromHook(category);
    },
    [currentWordPackId, generateExamplesFromHook],
  );

  // 選択されたWordPackIDが変更された場合の処理
  useEffect(() => {
    if (!selectedWordPackId || selectedWordPackId === currentWordPackId) return;
    handleLoadWordPack(selectedWordPackId);
  }, [currentWordPackId, handleLoadWordPack, selectedWordPackId]);

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

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => () => detachLemmaActionTooltip(), [detachLemmaActionTooltip]);


  function renderExampleEnText(text: string, lemma: string): React.ReactNode {
    const highlighted = highlightLemma(text, lemma, {
      spanProps: {
        'data-lemma': lemma,
      },
    });
    const nodes: React.ReactNode[] = [];
    let tokenSerial = 0;
    const wrapWords = (s: string) => {
      const parts = s.split(/([A-Za-z][A-Za-z\-']*)/g);
      for (let idx = 0; idx < parts.length; idx++) {
        const p = parts[idx];
        if (!p) continue;
        if (/^[A-Za-z][A-Za-z\-']*$/.test(p)) {
          nodes.push(
            <span key={`tok-${tokenSerial}-${idx}`} className="lemma-token" data-tok-idx={tokenSerial++}>{p}</span>
          );
        } else {
          nodes.push(p);
        }
      }
    };
    if (Array.isArray(highlighted)) {
      highlighted.forEach((n) => {
        if (typeof n === 'string') {
          wrapWords(n);
        } else {
          nodes.push(n);
        }
      });
    } else if (typeof highlighted === 'string') {
      wrapWords(highlighted);
    } else {
      nodes.push(highlighted);
    }
    return nodes;
  }

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
          <div className="kv" style={{ fontSize: '1.7em', marginBottom: '0.8rem' }}>
            <div>見出し語</div>
            <div className="wp-modal-lemma">
              <strong>{data!.lemma}</strong>
              {isInModalView ? (
                <TTSButton text={data!.lemma} className="wp-modal-tts-btn" />
              ) : null}
            </div>
          </div>
          {selectedMeta ? (
            <div className="kv" style={{ marginBottom: '0.5rem', fontSize: '0.7em' }}>
              <div>作成</div><div>{formatDate(selectedMeta.created_at)}</div>
              <div>更新</div><div>{formatDate(selectedMeta.updated_at)}</div>
              {aiMeta?.model ? (<><div>AIモデル</div><div>{aiMeta.model}</div></>) : null}
              {aiMeta?.params ? (<><div>AIパラメータ</div><div>{aiMeta.params}</div></>) : null}
            </div>
          ) : null}
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <strong style={{ color: 'var(--color-accent)' }}>📊 例文統計</strong>
              <span style={{ fontSize: '1.1em', fontWeight: 'bold' }}>
                総数 {exampleStats.total}件
              </span>
            </div>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.9em' }}>
              {exampleStats.counts.map(({ category, count }) => (
                <span key={category} style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  padding: '0.25rem 0.5rem',
                  backgroundColor: count > 0 ? 'var(--color-accent-bg)' : 'var(--color-neutral-surface)',
                  color: count > 0 ? 'var(--color-accent)' : 'var(--color-subtle)',
                  borderRadius: '4px',
                  border: `1px solid ${count > 0 ? 'var(--color-accent)' : 'var(--color-border)'}`
                }}>
                  <span style={{ fontWeight: 'bold' }}>{category}</span>
                  <span style={{ fontSize: '0.85em' }}>{count}件</span>
                </span>
              ))}
            </div>
          </div>
          <div
            style={{
              marginTop: '0.5rem',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.75rem',
              alignItems: 'center',
            }}
          >
            <div
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}
              aria-label="学習記録の操作"
            >
              <strong style={{ fontSize: '0.9em' }}>学習記録</strong>
              <button
                type="button"
                onClick={() => recordStudyProgress('checked')}
                disabled={!currentWordPackId || progressUpdating}
                title={!currentWordPackId ? '保存済みWordPackのみ記録できます' : undefined}
                style={{
                  padding: '0.3rem 0.7rem',
                  borderRadius: 6,
                  border: '1px solid #ffa726',
                  backgroundColor: '#fff3e0',
                  color: '#ef6c00',
                }}
              >
                確認した ({packCheckedCount})
              </button>
              <button
                type="button"
                onClick={() => recordStudyProgress('learned')}
                disabled={!currentWordPackId || progressUpdating}
                title={!currentWordPackId ? '保存済みWordPackのみ記録できます' : undefined}
                style={{
                  padding: '0.3rem 0.7rem',
                  borderRadius: 6,
                  border: '1px solid #81c784',
                  backgroundColor: '#e8f5e9',
                  color: '#1b5e20',
                }}
              >
                学習した ({packLearnedCount})
              </button>
            </div>
            {currentWordPackId && (
              <button
                type="button"
                onClick={handleRegenerateWordPack}
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
            .lemma-highlight { color: #1565c0; }
            .lemma-known { font-weight: 700; }
            .lemma-unknown { color: #ef6c00; text-decoration: underline dotted #ef6c00; }
            .lemma-tooltip { position: fixed; z-index: 10000; background: #212121; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); pointer-events: none; }
            .lemma-window { position: fixed; bottom: 24px; right: 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; box-shadow: 0 16px 32px rgba(0,0,0,0.25); display: flex; flex-direction: column; max-height: min(70vh, 520px); overflow: hidden; z-index: 950; }
            .lemma-window-header { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: var(--color-neutral-surface); border-bottom: 1px solid var(--color-border); }
            .lemma-window-title { font-size: 1rem; font-weight: 700; }
            .lemma-window-subtitle { font-size: 0.8rem; color: var(--color-subtle); margin-top: 0.2rem; }
            .lemma-window-actions { margin-left: auto; display: inline-flex; gap: 0.5rem; }
            .lemma-window-body { padding: 0.75rem 1rem 1rem; overflow-y: auto; line-height: 1.6; font-size: 0.9rem; }
            .lemma-window-resizer { position: absolute; top: 0; bottom: 0; width: 12px; cursor: ew-resize; }
            .lemma-window-resizer.left { left: -6px; }
            .lemma-window-resizer.right { right: -6px; }
            .lemma-window-footer { margin-top: 0.75rem; font-size: 0.75rem; color: var(--color-subtle); }
            .lemma-window-tray { position: fixed; bottom: 16px; right: 16px; display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end; z-index: 940; }
            .lemma-window-tray button { border-radius: 999px; padding: 0.4rem 0.9rem; background: var(--color-surface); border: 1px solid var(--color-border); box-shadow: 0 6px 18px rgba(0,0,0,0.25); cursor: pointer; font-size: 0.85rem; color: var(--color-text); }
            .lemma-window-minimize-btn, .lemma-window-close-btn { border: none; background: transparent; cursor: pointer; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }
            .lemma-window-minimize-btn:hover, .lemma-window-close-btn:hover { background: var(--color-neutral-surface); }
            .lemma-window-minimize-btn:focus-visible, .lemma-window-close-btn:focus-visible, .lemma-window-tray button:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
            .ex-en[role="button"] { cursor: pointer; }
            .ex-en[role="button"]:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
          `}</style>
          {(['Dev','CS','LLM','Business','Common'] as const).map((k) => (
            <div key={k} id={`examples-${k}`} style={{ marginBottom: '0.5rem' }}>
              <div className="ex-level" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{k} ({data!.examples?.[k]?.length || 0}件)</span>
                <button
                  onClick={() => handleGenerateExamples(k)}
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
                      <div
                        className="ex-en"
                        data-lemma={data!.lemma}
                        data-sense-title={data!.sense_title}
                        role="button"
                        tabIndex={0}
                        onClick={handleExampleActivation}
                        onKeyDown={handleExampleActivation}
                        onMouseOver={async (e) => {
                          const target = e.target as HTMLElement;
                          const hl = target.closest('span.lemma-highlight') as HTMLElement | null;
                          const tok = hl ? null : (target.closest('span.lemma-token') as HTMLElement | null);
                          const container = (e.currentTarget as HTMLElement);
                          const apiBase = (document.querySelector('meta[name="wp-api-base"]') as HTMLMetaElement)?.content || '/api';
                          const cache = ensureLemmaCache();
                          let matchedInfo: LemmaLookupResponseData | null = null;
                          let matchedCandidate: { idxs: number[]; text: string } | null = null;
                          const cleanup = detachLemmaActionTooltip;

                          if (hl) {
                            cleanup();
                            const display = container.getAttribute('data-sense-title') || '';
                            if (!display) return;
                            try { window.clearTimeout((hl as any).__ttimer); } catch {}
                            ;(hl as any).__ttimer = window.setTimeout(() => {
                              document.querySelectorAll('.lemma-tooltip').forEach((n) => n.remove());
                              const rect = hl.getBoundingClientRect();
                              const tip = document.createElement('div');
                              tip.setAttribute('role', 'tooltip');
                              tip.className = 'lemma-tooltip';
                              tip.textContent = display;
                              document.body.appendChild(tip);
                              const pad = 6;
                              const x = Math.min(Math.max(rect.left, 8), (window.innerWidth - tip.offsetWidth - 8));
                              const y = Math.max(rect.top - tip.offsetHeight - pad, 8);
                              tip.style.left = `${x}px`;
                              tip.style.top = `${y}px`;
                            }, 500);
                            return;
                          }

                          if (!tok) {
                            cleanup();
                            return;
                          }
                          cleanup();
                          const row = container;
                          const tokens = Array.from(row.querySelectorAll('span.lemma-token')) as HTMLElement[];
                          row.removeAttribute('data-last-lemma');
                          row.removeAttribute('data-pending-lemma');
                          tokens.forEach((el) => {
                            el.classList.remove('lemma-known', 'lemma-unknown');
                            el.removeAttribute('data-lemma-match');
                            el.removeAttribute('data-lemma-sense');
                            el.removeAttribute('data-lemma-id');
                            el.removeAttribute('data-pending-lemma');
                          });
                          const iTok = Number(tok.getAttribute('data-tok-idx')) || 0;
                          const getText = (el: HTMLElement) => (el.textContent || '').replace(/[\s\u00A0]+/g, ' ').trim();
                          const cands: { idxs: number[]; text: string }[] = [];
                          const push = (idxs: number[]) => {
                            const txt = idxs.map((k) => getText(tokens[k])).join(' ').trim();
                            if (txt) cands.push({ idxs, text: txt });
                          };
                          if (iTok > 0 && iTok < tokens.length - 1) push([iTok - 1, iTok, iTok + 1]);
                          if (iTok < tokens.length - 1) push([iTok, iTok + 1]);
                          if (iTok > 0) push([iTok - 1, iTok]);
                          push([iTok]);

                          let foundSense = '';
                          let foundIdxs: number[] | null = null;
                          for (const c of cands) {
                            const key = `lemma:${c.text.toLowerCase()}`;
                            let info = cache.get(key);
                            if (!info) {
                              try {
                                const res = await fetch(`${apiBase}/word/lemma/${encodeURIComponent(c.text)}`);
                                info = res.ok ? ((await res.json()) as LemmaLookupResponseData) : { found: false };
                                cache.set(key, info);
                              } catch {
                                info = { found: false };
                              }
                            }
                            if (info && info.found && info.sense_title) {
                              foundSense = info.sense_title;
                              foundIdxs = c.idxs;
                              matchedInfo = info;
                              matchedCandidate = c;
                              break;
                            }
                          }
                          if (!foundSense || !foundIdxs) {
                            const candidateTextRaw = matchedCandidate?.text || tok.textContent || '';
                            const candidateText = candidateTextRaw.trim();
                            if (candidateText) {
                              row.setAttribute('data-last-lemma', candidateText);
                              row.setAttribute('data-pending-lemma', candidateText);
                              tok.setAttribute('data-pending-lemma', candidateText);
                              tok.classList.add('lemma-unknown');
                            }
                            document.querySelectorAll('.lemma-tooltip').forEach((n) => n.remove());
                            const tooltip = document.createElement('div');
                            tooltip.className = 'lemma-tooltip';
                            tooltip.setAttribute('role', 'tooltip');
                            tooltip.textContent = '未生成';
                            const rect = tok.getBoundingClientRect();
                            const pad = 6;
                            document.body.appendChild(tooltip);
                            const x = Math.min(Math.max(rect.left, 8), (window.innerWidth - tooltip.offsetWidth - 8));
                            const y = Math.max(rect.top - tooltip.offsetHeight - pad, 8);
                            tooltip.style.left = `${x}px`;
                            tooltip.style.top = `${y}px`;

                            lemmaActionRef.current = {
                              tooltip,
                              aborter: null,
                            };
                            return;
                          }
                          const lemmaValue = (matchedInfo?.lemma || matchedCandidate?.text || '').trim();
                          foundIdxs.forEach((k) => {
                            const tokenEl = tokens[k];
                            if (!tokenEl) return;
                            tokenEl.classList.remove('lemma-unknown');
                            tokenEl.classList.add('lemma-known');
                            if (lemmaValue) tokenEl.setAttribute('data-lemma-match', lemmaValue);
                            if (matchedInfo?.sense_title) tokenEl.setAttribute('data-lemma-sense', matchedInfo.sense_title);
                            if (matchedInfo?.id) tokenEl.setAttribute('data-lemma-id', matchedInfo.id);
                          });
                          if (lemmaValue) {
                            container.setAttribute('data-last-lemma', lemmaValue);
                          }
                          if (matchedInfo?.sense_title) {
                            container.setAttribute('data-last-sense', matchedInfo.sense_title);
                          }
                          try { window.clearTimeout((tok as any).__ttimer); } catch {}
                          ;(tok as any).__ttimer = window.setTimeout(() => {
                            document.querySelectorAll('.lemma-tooltip').forEach((n) => n.remove());
                            const rect = tok.getBoundingClientRect();
                            const tip = document.createElement('div');
                            tip.setAttribute('role', 'tooltip');
                            tip.className = 'lemma-tooltip';
                            tip.textContent = foundSense;
                            document.body.appendChild(tip);
                            const pad = 6;
                            const x = Math.min(Math.max(rect.left, 8), (window.innerWidth - tip.offsetWidth - 8));
                            const y = Math.max(rect.top - tip.offsetHeight - pad, 8);
                            tip.style.left = `${x}px`;
                            tip.style.top = `${y}px`;
                          }, 500);
                        }}
                        onMouseOut={(e) => {
                          const target = e.target as HTMLElement;
                          const related = e.relatedTarget as Node | null;
                          const hl = target.closest('span.lemma-highlight') as HTMLElement | null;
                          const tok = target.closest('span.lemma-token') as HTMLElement | null;
                          if (hl) { try { window.clearTimeout((hl as any).__ttimer); } catch {} }
                          if (tok) { try { window.clearTimeout((tok as any).__ttimer); } catch {} }
                          const activeTooltip = lemmaActionRef.current?.tooltip || null;
                          if (activeTooltip && related && activeTooltip.contains(related)) {
                            return;
                          }
                          const row = e.currentTarget as HTMLElement;
                          detachLemmaActionTooltip();
                          row.removeAttribute('data-pending-lemma');
                          row.querySelectorAll('span.lemma-token').forEach((el) => {
                            el.classList.remove('lemma-known', 'lemma-unknown');
                            el.removeAttribute('data-pending-lemma');
                          });
                          document.querySelectorAll('.lemma-tooltip').forEach((n) => n.remove());
                        }}
                      >
                        <span className="ex-label">[{i + 1}] 英</span> {renderExampleEnText(ex.en, data!.lemma)}
                      </div>
                      <div className="ex-ja"><span className="ex-label">訳</span> {ex.ja}</div>
                      {ex.grammar_ja ? (
                        <div className="ex-grammar"><span className="ex-label">解説</span> {ex.grammar_ja}</div>
                      ) : null}
                      <div style={{ marginTop: 6, display: 'inline-flex', gap: 6, flexWrap: 'wrap' }}>
                        <TTSButton
                          text={ex.en}
                          voice="alloy"
                          style={{ fontSize: '0.85em', color: '#6a1b9a', border: '1px solid #6a1b9a', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                        />
                        {currentWordPackId ? (
                          <>
                            <button
                              onClick={() => deleteExample(k, i)}
                              disabled={loading}
                              aria-label={`delete-example-${k}-${i}`}
                              style={{ fontSize: '0.85em', color: '#d32f2f', border: '1px solid #d32f2f', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                            >
                              削除
                            </button>
                            <button
                              onClick={() => importArticleFromExample(k, i)}
                              disabled={loading}
                              aria-label={`import-article-from-example-${k}-${i}`}
                              style={{ fontSize: '0.85em', color: '#1565c0', border: '1px solid #1565c0', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                            >
                              文章インポート
                            </button>
                            <button
                              onClick={() => copyExampleText(k, i)}
                              disabled={loading}
                              aria-label={`copy-example-${k}-${i}`}
                              style={{ fontSize: '0.85em', color: '#2e7d32', border: '1px solid #2e7d32', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                            >
                              コピー
                            </button>
                          </>
                        ) : null}
                      </div>
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
    <>
      {!isInModalView && (
        <SidebarPortal>
          <section className="sidebar-section" aria-label="WordPackの生成">
            <h2>WordPack生成</h2>
            <div className="sidebar-field">
              <label htmlFor="wordpack-lemma-input">見出し語</label>
              <input
                id="wordpack-lemma-input"
                ref={focusRef as React.RefObject<HTMLInputElement>}
                value={lemma}
                onChange={(e) => setLemma(e.target.value)}
                placeholder="見出し語を入力（英数字・ハイフン・アポストロフィ・半角スペースのみ）"
                disabled={loading}
              />
              <p aria-live="polite" className="sidebar-help" style={{ color: isLemmaValid ? '#666' : '#d32f2f' }}>
                {lemmaValidation.message}
              </p>
            </div>
            <div className="sidebar-actions">
              <button type="button" onClick={handleGenerate} disabled={!isLemmaValid || loading}>
                生成
              </button>
              <button
                type="button"
                onClick={handleCreateEmpty}
                disabled={!isLemmaValid || loading}
                title="内容の生成を行わず、空のWordPackのみ保存"
              >
                WordPackのみ作成
              </button>
            </div>
            <div className="sidebar-field">
              <label htmlFor="wordpack-model-select">モデル</label>
              <select
                id="wordpack-model-select"
                value={model}
                onChange={(e) => handleChangeModel(e.target.value)}
                disabled={loading}
              >
                <option value="gpt-5-mini">gpt-5-mini</option>
                <option value="gpt-5-nano">gpt-5-nano</option>
                <option value="gpt-4.1-mini">gpt-4.1-mini</option>
                <option value="gpt-4o-mini">gpt-4o-mini</option>
              </select>
            </div>
            {showAdvancedModelOptions && (
              <div className="sidebar-inline">
                <div className="sidebar-field">
                  <label htmlFor="wordpack-reasoning-select">reasoning.effort</label>
                  <select
                    id="wordpack-reasoning-select"
                    aria-label="reasoning.effort"
                    value={advancedSettings.reasoningEffort}
                    onChange={(e) => advancedSettings.handleChangeReasoningEffort(e.target.value as typeof advancedSettings.reasoningEffort)}
                    disabled={loading}
                  >
                    <option value="minimal">minimal</option>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </div>
                <div className="sidebar-field">
                  <label htmlFor="wordpack-verbosity-select">text.verbosity</label>
                  <select
                    id="wordpack-verbosity-select"
                    aria-label="text.verbosity"
                    value={advancedSettings.textVerbosity}
                    onChange={(e) => advancedSettings.handleChangeTextVerbosity(e.target.value as typeof advancedSettings.textVerbosity)}
                    disabled={loading}
                  >
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </div>
              </div>
            )}
          </section>
        </SidebarPortal>
      )}
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
        .wp-modal-lemma { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
        .wp-modal-tts-btn { font-size: 0.6em; padding: 0.15rem 0.45rem; border-radius: 4px; }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
        @media (max-width: 840px) { .wp-container { grid-template-columns: 1fr; } }
      `}</style>

      {!isInModalView && <div style={{ marginBottom: '0.75rem' }} />}

      {/* 進捗ヘッダー */}

      {/* グローバル通知に置き換えたため、パネル内のローディング表示は削除 */}
      {message && <div role={message.kind}>{message.text}</div>}

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
      {lemmaExplorer ? (
        <LemmaExplorerWindow
          lemma={lemmaExplorer.lemma}
          senseTitle={lemmaExplorer.senseTitle}
          minimized={lemmaExplorer.minimized}
          width={lemmaExplorer.width}
          status={lemmaExplorer.status}
          errorMessage={lemmaExplorer.errorMessage}
          onClose={closeLemmaExplorer}
          onMinimize={minimizeLemmaExplorer}
          onRestore={restoreLemmaExplorer}
          onResize={resizeLemmaExplorer}
        >
          {lemmaExplorerContent}
        </LemmaExplorerWindow>
      ) : null}
    </>
  );
};


