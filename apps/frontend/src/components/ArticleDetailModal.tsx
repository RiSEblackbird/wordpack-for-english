import React from 'react';
import { Modal } from './Modal';
import { calculateDurationMs, formatDateJst, formatDurationMs } from '../lib/date';
import { TTSButton } from './TTSButton';

export interface ArticleWordPackLink {
  word_pack_id: string;
  lemma: string;
  status: 'existing' | 'created';
  is_empty?: boolean;
  warning?: string | null;
}

export interface ArticleDetailData {
  id: string;
  title_en: string;
  body_en: string;
  body_ja: string;
  notes_ja?: string | null;
  // 生成に使用したAI情報（任意）
  llm_model?: string | null;
  llm_params?: string | null;
  generation_category?: 'Dev' | 'CS' | 'LLM' | 'Business' | 'Common' | null;
  related_word_packs: ArticleWordPackLink[];
  warnings?: string[] | null;
  created_at?: string;
  updated_at?: string;
  generation_started_at?: string | null;
  generation_completed_at?: string | null;
  generation_duration_ms?: number | null;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  article: ArticleDetailData | null;
  title?: string;
  onRegenerateWordPack?: (wordPackId: string) => void;
  onOpenWordPackPreview?: (wordPackId: string) => void;
  onDeleteWordPack?: (wordPackId: string) => void;
}

export const ArticleDetailModal: React.FC<Props> = ({
  isOpen,
  onClose,
  article,
  title = '文章詳細',
  onRegenerateWordPack,
  onOpenWordPackPreview,
  onDeleteWordPack,
}) => {
  const formatDateWithFallback = (value?: string | null) => {
    if (!value) return null;
    const formatted = formatDateJst(value);
    return formatted && formatted.trim() ? formatted : value;
  };

  const generationDuration = React.useMemo(() => {
    if (!article) return null;
    const durationValue = article.generation_duration_ms;
    const hasDbDuration = typeof durationValue === 'number' && Number.isFinite(durationValue);
    if (hasDbDuration) {
      const label = formatDurationMs(durationValue as number);
      if (label && label.trim()) return label;
      if ((durationValue as number) === 0) return '0秒';
    }
    const start = article.generation_started_at || article.created_at;
    const end = article.generation_completed_at || article.updated_at;
    if (!start || !end) return null;
    const diff = calculateDurationMs(start, end);
    if (diff === null) return null;
    const label = formatDurationMs(diff);
    if (label && label.trim()) return label;
    // フォールバック計算で 0ms 相当になった場合は「計測不可」とする（DB未記録時のみ）
    if (diff === 0 && !hasDbDuration) return '計測不可';
    if (diff === 0) return '0秒';
    return null;
  }, [article]);

  const metaRows = React.useMemo(() => {
    if (!article) return [] as { label: string; value: string }[];
    const rows: { label: string; value: string }[] = [];
    const created = formatDateWithFallback(article.generation_started_at || article.created_at) ?? '未記録';
    const updated = formatDateWithFallback(article.generation_completed_at || article.updated_at) ?? '未記録';
    const durationLabel = generationDuration || '計測不可';
    const categoryMap: Record<'Dev' | 'CS' | 'LLM' | 'Business' | 'Common', string> = {
      Dev: 'Dev（開発）',
      CS: 'CS（コンピュータサイエンス）',
      LLM: 'LLM（大規模言語モデル）',
      Business: 'Business（ビジネス）',
      Common: 'Common（日常）',
    };
    const rawCategory = (article.generation_category || '').trim();
    const categoryLabel = rawCategory ? (categoryMap[rawCategory as keyof typeof categoryMap] || rawCategory) : '';
    const modelLabel = (article.llm_model || '').trim() || '未記録';
    const paramsLabel = (article.llm_params || '').trim() || '未記録';

    rows.push({ label: '作成', value: created });
    rows.push({ label: '更新', value: updated });
    rows.push({ label: '生成所要時間', value: durationLabel });
    rows.push({ label: '生成カテゴリ', value: (categoryLabel || '未指定') });
    rows.push({ label: 'AIモデル', value: modelLabel });
    rows.push({ label: 'AIパラメータ', value: paramsLabel });
    return rows;
  }, [article, generationDuration]);

  return (
    <Modal
      isOpen={!!article && isOpen}
      onClose={onClose}
      title={title}
    >
      {article ? (
        <div>
          <style>{`
            .ai-wp-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: 0.35rem;
            }
            .ai-meta-grid {
              display: grid;
              grid-template-columns: minmax(6rem, 0.45fr) 1fr;
              column-gap: 0.75rem;
              row-gap: 0.35rem;
              font-size: 0.75em;
              color: var(--color-subtle);
              margin-top: 0.75rem;
              font-variant-numeric: tabular-nums;
            }
            .ai-meta-grid dt {
              font-weight: 600;
            }
            .ai-meta-grid dd {
              margin: 0;
              white-space: pre-wrap;
              word-break: break-word;
            }
            @media (max-width: 480px) {
              .ai-meta-grid {
                grid-template-columns: minmax(5rem, 0.55fr) 1fr;
              }
            }
            @media (min-width: 480px) {
              .ai-wp-grid {
                grid-template-columns: repeat(2, 1fr);
              }
            }
            @media (min-width: 768px) {
              .ai-wp-grid { 
                grid-template-columns: repeat(3, 1fr); 
              }
            }
            .ai-card { border: 1px solid var(--color-border); border-radius: 4px; padding: 0.35rem; background: var(--color-surface); }
            .ai-badge { font-size: 0.68em; padding: 0.06rem 0.3rem; border-radius: 999px; border: 1px solid var(--color-border); }
            .ai-warnings { border: 1px solid #ffe08a; background: #fff8e1; padding: 0.5rem; border-radius: 4px; }
            .ai-warnings ul { margin: 0.25rem 0 0 1.2rem; padding: 0; }
          `}</style>
          <div
            style={{
              marginTop: 0,
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
            }}
          >
            <h3 style={{ margin: 0, flex: '1 1 auto' }}>{article.title_en}</h3>
            <TTSButton
              text={article.body_en}
              style={{ flex: '0 0 auto' }}
            />
          </div>
          <div style={{ whiteSpace: 'pre-wrap', margin: '0.5rem 0' }}>{article.body_en}</div>
          <hr />
          <div style={{ whiteSpace: 'pre-wrap', margin: '0.5rem 0' }}>{article.body_ja}</div>
          {article.notes_ja ? (
            <div style={{ marginTop: '0.5rem', color: 'var(--color-subtle)' }}>{article.notes_ja}</div>
          ) : null}
          {article.warnings && article.warnings.length > 0 ? (
            <div className="ai-warnings" role="alert" aria-label="import-warnings">
              <strong>警告</strong>
              <ul>
                {article.warnings.map((w, idx) => (
                  <li key={`warn-${idx}`}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <h4>関連WordPack</h4>
          <div className="ai-wp-grid">
            {article.related_word_packs.map((l) => (
              <div key={l.word_pack_id} className="ai-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {onOpenWordPackPreview ? (
                    <a href="#" onClick={(e) => { e.preventDefault(); onOpenWordPackPreview(l.word_pack_id); }}>
                      <strong style={{ fontSize: '0.65em' }}>{l.lemma}</strong>
                    </a>
                  ) : (
                    <strong style={{ fontSize: '0.65em' }}>{l.lemma}</strong>
                  )}
                  {l.is_empty ? (
                    <span className="ai-badge" style={{ background: '#fff3cd', borderColor: '#ffe08a', color: '#7a5b00' }}>空</span>
                  ) : null}
                  {onRegenerateWordPack ? (
                    <button onClick={() => onRegenerateWordPack(l.word_pack_id)} style={{ marginLeft: 'auto', fontSize: '0.65em', padding: '0.05rem 0.2rem', borderRadius: 3 }}>生成</button>
                  ) : null}
                  {onDeleteWordPack ? (
                    <button
                      onClick={() => onDeleteWordPack(l.word_pack_id)}
                      aria-label={`delete-wordpack-${l.word_pack_id}`}
                      style={{ marginLeft: 4, color: '#d32f2f', border: '1px solid #d32f2f', background: 'white', padding: '0.05rem 0.2rem', borderRadius: 3, fontSize: '0.65em' }}
                    >
                      削除
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
          {metaRows.length > 0 ? (
            <dl className="ai-meta-grid" data-testid="article-meta">
              {metaRows.map((row, idx) => (
                <React.Fragment key={`${row.label}-${idx}`}>
                  <dt>{row.label}</dt>
                  <dd>{row.value}</dd>
                </React.Fragment>
              ))}
            </dl>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
};

export default ArticleDetailModal;


