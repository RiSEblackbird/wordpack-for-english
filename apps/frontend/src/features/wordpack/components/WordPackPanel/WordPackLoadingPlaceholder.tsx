import React from 'react';

interface WordPackLoadingPlaceholderProps {
  placeholderLemma: string;
}

export const WordPackLoadingPlaceholder: React.FC<WordPackLoadingPlaceholderProps> = ({
  placeholderLemma,
}) => (
  <div className="wp-container" aria-busy="true">
    <section className="wp-section" aria-live="polite">
      <h3>読み込み中</h3>
      <div className="kv wp-loading-title">
        <div>見出し語</div>
        <div className="wp-modal-lemma">
          <strong>{placeholderLemma}</strong>
        </div>
      </div>
      <div className="sidebar-field wp-loading-field">
        <label htmlFor="wordpack-lemma-input-loading">見出し語</label>
        <input
          id="wordpack-lemma-input-loading"
          value={placeholderLemma}
          readOnly
          aria-readonly
          aria-label="WordPack見出し語読み込み中"
        />
        <p className="wp-loading-note">
          WordPack を読み込み中です。プレビューが準備されるまでお待ちください。
        </p>
      </div>
    </section>
  </div>
);
