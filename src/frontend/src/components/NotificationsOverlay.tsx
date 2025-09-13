import React, { useEffect, useMemo, useState } from 'react';
import { useNotifications } from '../NotificationsContext';

export const NotificationsOverlay: React.FC = () => {
  const { notifications, remove } = useNotifications();
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  useEffect(() => {
    const t = window.setInterval(() => setNowMs(Date.now()), 250);
    return () => window.clearInterval(t);
  }, []);

  const formatElapsed = (ms: number): string => {
    const s = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${m}:${String(ss).padStart(2, '0')}`;
  };

  return (
    <div aria-live="polite" aria-relevant="additions" style={{ position: 'fixed', right: 12, bottom: 12, zIndex: 1000, display: 'flex', flexDirection: 'column-reverse', gap: 8, pointerEvents: 'none' }}>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .ntf-card { pointer-events: auto; width: min(280px, 72vw); background: var(--color-surface, #fff); border: 1px solid var(--color-border, #ddd); border-radius: 8px; box-shadow: 0 6px 18px rgba(0,0,0,0.1); padding: 4px 9px; display: grid; grid-template-columns: 24px 1fr 24px; align-items: center; gap: 8px; }
        .ntf-title { font-weight: 600; font-size: 75%; }
        .ntf-msg { color: var(--color-muted, #555); font-size: 60%; }
        .ntf-time { color: var(--color-subtle, #777); font-size: 50%; font-variant-numeric: tabular-nums; }
        .ntf-icon { width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; }
        .ntf-spinner { width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--color-spinner-border, #ddd); border-top-color: var(--color-spinner-top, #1976d2); animation: spin 0.9s linear infinite; }
        .ntf-success { color: #2e7d32; }
        .ntf-error { color: #c62828; }
        .ntf-close { cursor: pointer; user-select: none; border: none; background: transparent; font-size: 14px; color: var(--color-subtle, #666); }
        .ntf-close:hover { color: #000; }
      `}</style>
      {notifications.map((n) => {
        const elapsedMs = n.status === 'progress' ? nowMs - n.createdAt : n.updatedAt - n.createdAt;
        const timeLabel = n.status === 'progress' ? '経過' : '所要';
        return (
        <div key={n.id} className="ntf-card" role="status" aria-label={`${n.title} - ${n.status}`}>
          <div className="ntf-icon" aria-hidden="true">
            {n.status === 'progress' ? (
              <div className="ntf-spinner" />
            ) : n.status === 'success' ? (
              <span className="ntf-success">✓</span>
            ) : (
              <span className="ntf-error">✕</span>
            )}
          </div>
          <div>
            <div className="ntf-title">{n.title}</div>
            {n.message ? <div className="ntf-msg">{n.message}</div> : null}
            <div className="ntf-time">{timeLabel} {formatElapsed(elapsedMs)}</div>
          </div>
          <button className="ntf-close" aria-label="閉じる" onClick={() => remove(n.id)}>✕</button>
        </div>
        );
      })}
    </div>
  );
};


