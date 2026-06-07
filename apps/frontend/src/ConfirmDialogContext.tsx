import React, { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { Modal } from './components/Modal';

interface ConfirmDialogContextValue {
  confirm: (targetLabel: string) => Promise<boolean>;
}

interface PendingConfirm {
  targetLabel: string;
  resolve: (result: boolean) => void;
}

const ConfirmDialogContext = createContext<ConfirmDialogContextValue | undefined>(undefined);

export const ConfirmDialogProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [pending, setPending] = useState<PendingConfirm | null>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  const requestConfirm = useCallback((targetLabel: string) => {
    return new Promise<boolean>((resolve) => {
      setPending({ targetLabel, resolve });
    });
  }, []);

  const close = useCallback((result: boolean) => {
    setPending((prev) => {
      prev?.resolve(result);
      return null;
    });
  }, []);

  const targetLabel = pending?.targetLabel ?? '';

  return (
    <ConfirmDialogContext.Provider value={{ confirm: requestConfirm }}>
      {children}
      <Modal
        isOpen={pending !== null}
        onClose={() => close(false)}
        title="削除確認"
        maxWidth="min(92vw, 34rem)"
        initialFocusRef={cancelButtonRef}
      >
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <p style={{ margin: 0, lineHeight: 1.6 }}>
            <strong>{targetLabel}</strong> を削除します。
          </p>
          <p style={{ margin: 0, lineHeight: 1.6, color: 'var(--color-subtle)' }}>
            この操作は保存済みデータから対象を削除します。実行後はこの画面から取り消せません。
          </p>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
          <button ref={cancelButtonRef} type="button" onClick={() => close(false)}>キャンセル</button>
          <button
            type="button"
            onClick={() => close(true)}
            style={{ background: '#b91c1c', borderColor: '#b91c1c', color: '#fff' }}
          >
            削除する
          </button>
        </div>
      </Modal>
    </ConfirmDialogContext.Provider>
  );
};

export const useConfirmDialog = (): ConfirmDialogContextValue['confirm'] => {
  const context = useContext(ConfirmDialogContext);
  if (!context) {
    throw new Error('useConfirmDialog must be used within a ConfirmDialogProvider');
  }
  return context.confirm;
};
