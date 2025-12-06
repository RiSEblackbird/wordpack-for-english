import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { useConfirmDialog } from '../ConfirmDialogContext';
import { useWordPack, Examples, WordPack } from '../hooks/useWordPack';
import { useWordPackForm } from '../hooks/useWordPackForm';
import { useNotifications } from '../NotificationsContext';
import { Modal } from './Modal';
import { formatDateJst } from '../lib/date';
import { SidebarPortal } from './SidebarPortal';
import { LemmaExplorerPanel } from './LemmaExplorer/LemmaExplorerPanel';
import { LemmaLookupResponseData, useLemmaExplorer } from './LemmaExplorer/useLemmaExplorer';
import { useExampleActions } from '../hooks/useExampleActions';
import { OverviewSection } from './wordpack/OverviewSection';
import { PronunciationSection } from './wordpack/PronunciationSection';
import { SensesSection } from './wordpack/SensesSection';
import { ExamplesSection } from './wordpack/ExamplesSection';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
  selectedWordPackId?: string | null;
  onWordPackGenerated?: (wordPackId: string | null) => void;
  selectedMeta?: { created_at: string; updated_at: string } | null;
  onStudyProgressRecorded?: (payload: { wordPackId: string; checked_only_count: number; learned_count: number }) => void;
}

/**
 * WordPack全体のパネル。データ取得/生成や各セクションへの責務分割を担い、
 * UI本体は小さなセクションコンポーネントへ委譲する。
 */
export const WordPackPanel: React.FC<Props> = ({ focusRef, selectedWordPackId, onWordPackGenerated, selectedMeta, onStudyProgressRecorded }) => {
  const { settings, setSettings } = useSettings();
  const { setModalOpen } = useModal();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const confirmDialog = useConfirmDialog();
  const { apiBase, pronunciationEnabled, requestTimeoutMs, temperature } = settings;
  const { lemma, setLemma, lemmaValidation, model, showAdvancedModelOptions, handleChangeModel, advancedSettings } = useWordPackForm({ settings, setSettings });
  const [detailOpen, setDetailOpen] = useState(false);

  const {
    aiMeta,
    currentWordPackId,
    data,
    loading,
    message,
    setStatusMessage,
    generateWordPack,
    createEmptyWordPack,
    loadWordPack,
    regenerateWordPack,
    recordStudyProgress,
  } = useWordPack({ model, onWordPackGenerated, onStudyProgressRecorded });

  const {
    explorer: lemmaExplorer,
    explorerContent,
    openLemmaExplorer: onLemmaOpen,
    closeLemmaExplorer,
    minimizeLemmaExplorer,
    restoreLemmaExplorer,
    resizeLemmaExplorer,
    lookupLemmaMetadata,
    invalidateLemmaCache,
  } = useLemmaExplorer({ apiBase, requestTimeoutMs, onStatusMessage: setStatusMessage });

  const { examplesLoading, deleteExample, generateExamples, importArticleFromExample, copyExampleText } = useExampleActions({
    apiBase,
    requestTimeoutMs,
    currentWordPackId,
    data,
    model,
    temperature,
    reasoningEffort: advancedSettings.reasoningEffort,
    textVerbosity: advancedSettings.textVerbosity,
    setStatusMessage,
    loadWordPack,
    notify: { add: addNotification, update: updateNotification },
    confirmDialog,
    onWordPackGenerated,
  });

  const isInModalView = Boolean(selectedWordPackId) || (Boolean(data) && detailOpen);
  const isLemmaValid = lemmaValidation.valid;
  const normalizedLemma = lemmaValidation.normalizedLemma;
  const isActionLoading = loading || examplesLoading;

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
    [],
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
    [data, exampleCategories],
  );

  const packCheckedCount = data?.checked_only_count ?? 0;
  const packLearnedCount = data?.learned_count ?? 0;

  const triggerUnknownLemmaGeneration = useCallback(async (lemmaText: string) => {
    const trimmed = lemmaText.trim();
    if (!trimmed) return false;
    await generateWordPack(trimmed);
    try {
      invalidateLemmaCache(trimmed);
    } catch {}
    onLemmaOpen(trimmed);
    return true;
  }, [generateWordPack, invalidateLemmaCache, onLemmaOpen]);

  const handleGenerate = useCallback(async () => {
    if (!lemmaValidation.valid) {
      setStatusMessage({ kind: 'alert', text: lemmaValidation.message });
      return;
    }
    setLemma('');
    try { focusRef.current?.focus(); } catch {}
    await generateWordPack(normalizedLemma);
  }, [focusRef, generateWordPack, lemmaValidation, normalizedLemma, setLemma, setStatusMessage]);

  const handleCreateEmpty = useCallback(async () => {
    if (!lemmaValidation.valid) {
      setStatusMessage({ kind: 'alert', text: lemmaValidation.message });
      return;
    }
    await createEmptyWordPack(normalizedLemma);
  }, [createEmptyWordPack, lemmaValidation, normalizedLemma, setStatusMessage]);

  const handleLoadWordPack = useCallback(
    async (wordPackId: string) => {
      await loadWordPack(wordPackId);
    },
    [loadWordPack],
  );

  const handleRegenerateWordPack = useCallback(async () => {
    if (!currentWordPackId) return;
    await regenerateWordPack(currentWordPackId, data?.lemma || 'WordPack');
  }, [currentWordPackId, data?.lemma, regenerateWordPack]);

  const handleGenerateExamples = useCallback(
    async (category: keyof Examples) => {
      await generateExamples(category);
    },
    [generateExamples],
  );

  useEffect(() => {
    if (!selectedWordPackId || selectedWordPackId === currentWordPackId) return;
    handleLoadWordPack(selectedWordPackId);
  }, [currentWordPackId, handleLoadWordPack, selectedWordPackId]);

  const renderCollocations = (target: WordPack['collocations']) => (
    <section id="collocations" className="wp-section">
      <h3>共起</h3>
      <div>
        <h4>一般</h4>
        <div className="mono">VO: {target?.general?.verb_object?.length ? target.general.verb_object.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < target.general.verb_object.length - 1 ? ', ' : ''}
          </React.Fragment>
        )) : '-'}</div>
        <div className="mono">Adj+N: {target?.general?.adj_noun?.length ? target.general.adj_noun.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < target.general.adj_noun.length - 1 ? ', ' : ''}
          </React.Fragment>
        )) : '-'}</div>
        <div className="mono">Prep+N: {target?.general?.prep_noun?.length ? target.general.prep_noun.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < target.general.prep_noun.length - 1 ? ', ' : ''}
          </React.Fragment>
        )) : '-'}</div>
      </div>
      <div>
        <h4>アカデミック</h4>
        <div className="mono">VO: {target?.academic?.verb_object?.length ? target.academic.verb_object.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < target.academic.verb_object.length - 1 ? ', ' : ''}
          </React.Fragment>
        )) : '-'}</div>
        <div className="mono">Adj+N: {target?.academic?.adj_noun?.length ? target.academic.adj_noun.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < target.academic.adj_noun.length - 1 ? ', ' : ''}
          </React.Fragment>
        )) : '-'}</div>
        <div className="mono">Prep+N: {target?.academic?.prep_noun?.length ? target.academic.prep_noun.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" onClick={(e) => { e.preventDefault(); setLemma(t.split(' ').pop() || t); }}>{t}</a>{i < target.academic.prep_noun.length - 1 ? ', ' : ''}
          </React.Fragment>
        )) : '-'}</div>
      </div>
    </section>
  );

  const detailsContent = data ? (
    <div className="wp-container">
      {/* セクションナビゲーション: 画面内リンクで各要素へショートカット */}
      <nav className="wp-nav" aria-label="セクション">
        {sectionIds.map((s) => (
          <a key={s.id} href={`#${s.id}`}>{s.label}</a>
        ))}
        {exampleCategories.map((category) => (
          <a
            key={`examples-${category}`}
            href={`#examples-${category}`}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(`examples-${category}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }}
          >例文: {category}</a>
        ))}
      </nav>

      <div>
        <OverviewSection
          data={data}
          selectedMeta={selectedMeta}
          aiMeta={aiMeta}
          exampleStats={exampleStats}
          currentWordPackId={currentWordPackId}
          isActionLoading={isActionLoading}
          packCheckedCount={packCheckedCount}
          packLearnedCount={packLearnedCount}
          onRecordStudyProgress={recordStudyProgress}
          onRegenerate={handleRegenerateWordPack}
          formatDate={formatDate}
          showTtsButton={isInModalView}
        />

        {pronunciationEnabled ? <PronunciationSection pronunciation={data.pronunciation} /> : null}
        <SensesSection senses={data.senses} />

        <section id="etymology" className="wp-section">
          <h3>語源</h3>
          <p>{data.etymology?.note || '-'}</p>
          <p>確度: {data.etymology?.confidence}</p>
        </section>

        <ExamplesSection
          data={data}
          currentWordPackId={currentWordPackId}
          isActionLoading={isActionLoading}
          onGenerateExamples={handleGenerateExamples}
          onDeleteExample={deleteExample}
          onImportArticleFromExample={importArticleFromExample}
          onCopyExampleText={copyExampleText}
          onLemmaOpen={onLemmaOpen}
          lookupLemmaMetadata={lookupLemmaMetadata as (lemmaText: string) => Promise<LemmaLookupResponseData>}
          triggerUnknownLemmaGeneration={triggerUnknownLemmaGeneration}
        />

        {renderCollocations(data.collocations)}

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
      </div>
    </div>
  ) : null;

  return (
    <>
      {/* 生成フォーム: サイドバーに固定し、入力とモデル設定をまとめる */}
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
                disabled={isActionLoading}
              />
              <p aria-live="polite" className="sidebar-help" style={{ color: isLemmaValid ? '#666' : '#d32f2f' }}>
                {lemmaValidation.message}
              </p>
            </div>
            <div className="sidebar-actions">
              <button type="button" onClick={handleGenerate} disabled={!isLemmaValid || isActionLoading}>
                生成
              </button>
              <button
                type="button"
                onClick={handleCreateEmpty}
                disabled={!isLemmaValid || isActionLoading}
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
                disabled={isActionLoading}
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
                    disabled={isActionLoading}
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
                    disabled={isActionLoading}
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

        {message && <div role={message.kind}>{message.text}</div>}

        {/* 詳細表示: モーダル/ダイレクト表示の両対応 */}
        {selectedWordPackId ? (
          data ? detailsContent : null
        ) : (
          <Modal
            isOpen={!!data && detailOpen}
            onClose={() => { setDetailOpen(false); try { setModalOpen(false); } catch {} }}
            title="WordPack プレビュー"
          >
            {detailsContent}
          </Modal>
        )}
      </section>

      {lemmaExplorer ? (
        <LemmaExplorerPanel
          explorer={lemmaExplorer}
          content={explorerContent}
          onClose={closeLemmaExplorer}
          onMinimize={minimizeLemmaExplorer}
          onRestore={restoreLemmaExplorer}
          onResize={resizeLemmaExplorer}
        />
      ) : null}
    </>
  );
};
