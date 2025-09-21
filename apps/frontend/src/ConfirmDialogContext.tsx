import React, { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
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

  const message = pending ? `【${pending.targetLabel}】について削除しますか？` : '';

  return (
    <ConfirmDialogContext.Provider value={{ confirm: requestConfirm }}>
      {children}
      <Modal
        isOpen={pending !== null}
        onClose={() => close(false)}
        title="削除確認"
        maxWidth="min(48vw, calc(var(--main-max-width, 1000px) * 0.45))"
      >
        <p style={{ marginBottom: '1.5rem', lineHeight: 1.6 }}>{message}</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button onClick={() => close(false)}>いいえ</button>
          <button onClick={() => close(true)} style={{ background: 'var(--color-accent)', color: '#fff' }}>はい</button>
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
