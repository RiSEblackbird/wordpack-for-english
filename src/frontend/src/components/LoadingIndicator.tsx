import React, { useEffect, useMemo, useState } from 'react';

interface Props {
  label?: string;
  subtext?: string;
}

export const LoadingIndicator: React.FC<Props> = ({ label = '読み込み中…', subtext }) => {
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  useEffect(() => {
    const startedAt = Date.now();
    const t = window.setInterval(() => setElapsedMs(Date.now() - startedAt), 250);
    return () => window.clearInterval(t);
  }, []);

  const hhmmss = useMemo(() => {
    const s = Math.floor(elapsedMs / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${m}:${String(ss).padStart(2, '0')}`;
  }, [elapsedMs]);

  return (
    <div role="status" aria-live="polite" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .ldg-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid #cbd5e1;
          border-top-color: #2563eb;
          border-radius: 50%;
          animation: spin 0.9s linear infinite;
        }
        .ldg-wrap { display: flex; align-items: center; gap: 12px; }
        .ldg-texts { display: flex; flex-direction: column; }
        .ldg-label { font-weight: 600; }
        .ldg-sub { color: #555; font-size: 90%; }
        .ldg-time { color: #6b7280; font-variant-numeric: tabular-nums; font-size: 90%; }
      `}</style>
      <div className="ldg-wrap">
        <div className="ldg-spinner" aria-hidden="true" />
        <div className="ldg-texts">
          <div className="ldg-label">{label}</div>
          {subtext ? <div className="ldg-sub">{subtext}</div> : null}
          <div className="ldg-time">経過 {hhmmss}</div>
        </div>
      </div>
    </div>
  );
};


