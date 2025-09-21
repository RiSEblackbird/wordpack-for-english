import React, { useEffect } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen]);

  if (!isOpen) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title || 'モーダル'}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--color-inverse-overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
   >
      <div
        style={{
          width: '100%',
          maxWidth: 'min(96vw, calc(var(--main-max-width, 1000px) * 0.90))',
          maxHeight: '90vh',
          overflow: 'auto',
          background: 'var(--color-surface)',
          borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1rem', borderBottom: '1px solid var(--color-border)' }}>
          <strong style={{ fontSize: '1.1rem' }}>{title}</strong>
          <button onClick={onClose} style={{ marginLeft: 'auto' }} aria-label="閉じる">閉じる</button>
        </div>
        <div style={{ padding: '1rem' }}>
          {children}
        </div>
      </div>
    </div>
  );
};


