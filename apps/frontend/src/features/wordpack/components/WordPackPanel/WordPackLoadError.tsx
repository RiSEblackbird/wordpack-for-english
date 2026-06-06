import React from 'react';

interface WordPackLoadErrorProps {
  placeholderLemma: string;
  message: string;
  onRetry: () => void;
  onClose?: () => void;
}

export const WordPackLoadError: React.FC<WordPackLoadErrorProps> = ({
  placeholderLemma,
  message,
  onRetry,
  onClose,
}) => (
  <div className="wp-container">
    <section className="wp-section wp-load-error" role="alert" aria-live="assertive">
      <h3>WordPackを読み込めませんでした</h3>
      <div className="kv wp-loading-title">
        <div>対象</div>
        <div className="wp-modal-lemma">
          <strong>{placeholderLemma}</strong>
        </div>
      </div>
      <p className="wp-load-error__message">
        {message}
      </p>
      <p className="wp-load-error__note">
        一覧で選んだ情報は保持されています。通信状態を確認して再試行するか、プレビューを閉じて別のWordPackを選んでください。
      </p>
      <div className="wp-load-error__actions">
        <button type="button" onClick={onRetry}>
          再試行
        </button>
        {onClose ? (
          <button type="button" onClick={onClose}>
            プレビューを閉じる
          </button>
        ) : null}
      </div>
    </section>
  </div>
);
