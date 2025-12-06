import React, { useMemo } from 'react';
import { ExampleItem, Examples, WordPack } from '../../hooks/useWordPack';
import { LemmaLookupResponseData } from '../LemmaExplorer/useLemmaExplorer';
import { TTSButton } from '../TTSButton';
import { highlightLemma } from '../../lib/highlight';
import { useLemmaTooltip } from './useLemmaTooltip';

export type ExampleCategory = keyof Examples;

interface ExamplesSectionProps {
  data: WordPack;
  currentWordPackId: string | null;
  isActionLoading: boolean;
  onGenerateExamples: (category: ExampleCategory) => Promise<void>;
  onDeleteExample: (category: ExampleCategory, index: number) => Promise<void>;
  onImportArticleFromExample: (category: ExampleCategory, index: number) => Promise<void>;
  onCopyExampleText: (category: ExampleCategory, index: number) => Promise<void>;
  onLemmaOpen: (lemmaText: string) => void;
  lookupLemmaMetadata: (lemmaText: string) => Promise<LemmaLookupResponseData>;
  triggerUnknownLemmaGeneration: (lemmaText: string) => Promise<boolean>;
}

/**
 * 例文一覧と派生操作（追加生成・削除・記事化など）をまとめるセクション。
 * レイアウト/スタイルとイベントハンドラを局所化し、上位はデータとハンドラだけを渡す。
 */
export const ExamplesSection: React.FC<ExamplesSectionProps> = ({
  data,
  currentWordPackId,
  isActionLoading,
  onGenerateExamples,
  onDeleteExample,
  onImportArticleFromExample,
  onCopyExampleText,
  onLemmaOpen,
  lookupLemmaMetadata,
  triggerUnknownLemmaGeneration,
}) => {
  const exampleCategories = useMemo(() => (['Dev', 'CS', 'LLM', 'Business', 'Common'] as ExampleCategory[]), []);
  const styleDefinition = useMemo(
    () => `
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
      .ex-en[role="button"] { cursor: pointer; }
      .ex-en[role="button"]:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
    `,
    [],
  );
  const { handleMouseOver, handleMouseOut, detachTooltip } = useLemmaTooltip({ lookupLemmaMetadata });

  const renderExampleEnText = (text: string, lemma: string): React.ReactNode => {
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
            <span key={`tok-${tokenSerial}-${idx}`} className="lemma-token" data-tok-idx={tokenSerial++}>{p}</span>,
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
  };

  const handleExampleActivation = (
    event: React.MouseEvent<HTMLDivElement> | React.KeyboardEvent<HTMLDivElement>,
  ) => {
    if ('key' in event) {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
    }
    const container = event.currentTarget;
    const target = event.target as HTMLElement;
    const highlight = target.closest('span.lemma-highlight') as HTMLElement | null;
    if (highlight) {
      const lemmaAttr = highlight.getAttribute('data-lemma') || highlight.textContent?.trim();
      if (lemmaAttr) onLemmaOpen(lemmaAttr);
      return;
    }
    const token = target.closest('span.lemma-token') as HTMLElement | null;
    if (token) {
      const lemmaMatch = token.getAttribute('data-lemma-match');
      if (lemmaMatch) {
        onLemmaOpen(lemmaMatch);
        return;
      }
      const pendingLemma = token.getAttribute('data-pending-lemma') || container.getAttribute('data-pending-lemma');
      if (pendingLemma && pendingLemma.trim()) {
        const trimmed = pendingLemma.trim();
        container.removeAttribute('data-pending-lemma');
        container.removeAttribute('data-last-lemma');
        token.removeAttribute('data-pending-lemma');
        token.classList.remove('lemma-unknown');
        detachTooltip();
        void triggerUnknownLemmaGeneration(trimmed);
        return;
      }
    }
    const pending = container.getAttribute('data-pending-lemma');
    if (pending && pending.trim()) {
      container.removeAttribute('data-pending-lemma');
      container.removeAttribute('data-last-lemma');
      detachTooltip();
      void triggerUnknownLemmaGeneration(pending);
      return;
    }
    const fallback = container.getAttribute('data-last-lemma') || container.getAttribute('data-lemma');
    if (fallback) onLemmaOpen(fallback);
  };

  const totalExamples = useMemo(
    () => exampleCategories.reduce((sum, key) => sum + (data.examples?.[key]?.length || 0), 0),
    [data.examples, exampleCategories],
  );

  return (
    <section id="examples" className="wp-section">
      <h3>
        例文
        <span style={{ fontSize: '0.7em', fontWeight: 'normal', color: 'var(--color-subtle)', marginLeft: '0.5rem' }}>
          (総数 {totalExamples}件)
        </span>
      </h3>
      <style>{styleDefinition}</style>
      {exampleCategories.map((category) => (
        <div key={category} id={`examples-${category}`} style={{ marginBottom: '0.5rem' }}>
          <div className="ex-level" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>{category} ({data.examples?.[category]?.length || 0}件)</span>
            <button
              onClick={() => onGenerateExamples(category)}
              disabled={!currentWordPackId || isActionLoading}
              aria-label={`generate-examples-${category}`}
              title={!currentWordPackId ? '保存済みWordPackのみ追加生成が可能です' : undefined}
              style={{ fontSize: '0.85em', color: '#1565c0', border: '1px solid #1565c0', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
            >
              追加生成（2件）
            </button>
          </div>
          {data.examples?.[category]?.length ? (
            <div className="ex-grid">
              {(data.examples[category] as ExampleItem[]).map((ex: ExampleItem, index: number) => (
                <article key={index} className="ex-card" aria-label={`example-${category}-${index}`}>
                  <div
                    className="ex-en"
                    data-lemma={data.lemma}
                    data-sense-title={data.sense_title}
                    role="button"
                    tabIndex={0}
                    onClick={handleExampleActivation}
                    onKeyDown={handleExampleActivation}
                    onMouseOver={handleMouseOver}
                    onMouseOut={handleMouseOut}
                  >
                    <span className="ex-label">[{index + 1}] 英</span> {renderExampleEnText(ex.en, data.lemma)}
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
                          onClick={() => onDeleteExample(category, index)}
                          disabled={isActionLoading}
                          aria-label={`delete-example-${category}-${index}`}
                          style={{ fontSize: '0.85em', color: '#d32f2f', border: '1px solid #d32f2f', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                        >
                          削除
                        </button>
                        <button
                          onClick={() => onImportArticleFromExample(category, index)}
                          disabled={isActionLoading}
                          aria-label={`import-example-${category}-${index}`}
                          style={{ fontSize: '0.85em', color: '#2e7d32', border: '1px solid #2e7d32', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                        >
                          記事化
                        </button>
                        <button
                          onClick={() => onCopyExampleText(category, index)}
                          disabled={isActionLoading}
                          aria-label={`copy-example-${category}-${index}`}
                          style={{ fontSize: '0.85em', color: '#1976d2', border: '1px solid #1976d2', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
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
  );
};
