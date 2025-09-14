import React from 'react';
import { Modal } from './Modal';

export interface ArticleWordPackLink {
  word_pack_id: string;
  lemma: string;
  status: 'existing' | 'created';
  is_empty?: boolean;
}

export interface ArticleDetailData {
  id: string;
  title_en: string;
  body_en: string;
  body_ja: string;
  notes_ja?: string | null;
  related_word_packs: ArticleWordPackLink[];
  created_at?: string;
  updated_at?: string;
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
  return (
    <Modal
      isOpen={!!article && isOpen}
      onClose={onClose}
      title={title}
    >
      {article ? (
        <div>
          <style>{`
            .ai-wp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.5rem; }
            .ai-card { border: 1px solid var(--color-border); border-radius: 6px; padding: 0.5rem; background: var(--color-surface); }
            .ai-badge { font-size: 0.75em; padding: 0.1rem 0.4rem; border-radius: 999px; border: 1px solid var(--color-border); }
          `}</style>
          <h3 style={{ marginTop: 0 }}>{article.title_en}</h3>
          <div style={{ whiteSpace: 'pre-wrap', margin: '0.5rem 0' }}>{article.body_en}</div>
          <hr />
          <div style={{ whiteSpace: 'pre-wrap', margin: '0.5rem 0' }}>{article.body_ja}</div>
          {article.notes_ja ? (
            <div style={{ marginTop: '0.5rem', color: 'var(--color-subtle)' }}>{article.notes_ja}</div>
          ) : null}
          <h4>関連WordPack</h4>
          <div className="ai-wp-grid">
            {article.related_word_packs.map((l) => (
              <div key={l.word_pack_id} className="ai-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {onOpenWordPackPreview ? (
                    <a href="#" onClick={(e) => { e.preventDefault(); onOpenWordPackPreview(l.word_pack_id); }}>
                      <strong>{l.lemma}</strong>
                    </a>
                  ) : (
                    <strong>{l.lemma}</strong>
                  )}
                  <span className="ai-badge">{l.status === 'created' ? '新規' : '既存'}</span>
                  {l.is_empty ? (
                    <span className="ai-badge" style={{ background: '#fff3cd', borderColor: '#ffe08a', color: '#7a5b00' }}>空</span>
                  ) : null}
                  {onRegenerateWordPack ? (
                    <button onClick={() => onRegenerateWordPack(l.word_pack_id)} style={{ marginLeft: 'auto' }}>生成</button>
                  ) : null}
                  {onDeleteWordPack ? (
                    <button
                      onClick={() => onDeleteWordPack(l.word_pack_id)}
                      aria-label={`delete-wordpack-${l.word_pack_id}`}
                      style={{ marginLeft: 8, color: '#d32f2f', border: '1px solid #d32f2f', background: 'white', padding: '0.1rem 0.4rem', borderRadius: 4 }}
                    >
                      削除
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Modal>
  );
};

export default ArticleDetailModal;


