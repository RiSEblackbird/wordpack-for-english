import React, { useEffect, useRef } from 'react';

interface LemmaExplorerWindowProps {
  lemma: string;
  senseTitle?: string | null;
  minimized: boolean;
  width: number;
  status: 'loading' | 'ready' | 'error';
  errorMessage?: string | null;
  onClose: () => void;
  onMinimize: () => void;
  onRestore: () => void;
  onResize: (nextWidth: number) => void;
  children?: React.ReactNode;
}

const MIN_WIDTH = 280;
const MAX_WIDTH = 600;

type ActiveResizeState = {
  edge: 'left' | 'right';
  startX: number;
  startWidth: number;
};

type PointerListeners = {
  move: (event: PointerEvent) => void;
  up: (event: PointerEvent) => void;
};

export const LemmaExplorerWindow: React.FC<LemmaExplorerWindowProps> = ({
  lemma,
  senseTitle,
  minimized,
  width,
  status,
  errorMessage,
  onClose,
  onMinimize,
  onRestore,
  onResize,
  children,
}) => {
  const resizeStateRef = useRef<ActiveResizeState | null>(null);
  const listenersRef = useRef<PointerListeners | null>(null);

  useEffect(() => {
    return () => {
      if (listenersRef.current) {
        window.removeEventListener('pointermove', listenersRef.current.move);
        window.removeEventListener('pointerup', listenersRef.current.up);
        listenersRef.current = null;
      }
    };
  }, []);

  const startResize = (edge: 'left' | 'right') => (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const startState: ActiveResizeState = {
      edge,
      startX: event.clientX,
      startWidth: width,
    };
    resizeStateRef.current = startState;

    const handlePointerMove = (ev: PointerEvent) => {
      if (!resizeStateRef.current) return;
      const { edge: activeEdge, startX, startWidth } = resizeStateRef.current;
      const delta = ev.clientX - startX;
      let nextWidth = startWidth;
      if (activeEdge === 'left') {
        nextWidth = startWidth - delta;
      } else {
        nextWidth = startWidth + delta;
      }
      nextWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, nextWidth));
      onResize(nextWidth);
    };

    const handlePointerUp = () => {
      if (listenersRef.current) {
        window.removeEventListener('pointermove', listenersRef.current.move);
        window.removeEventListener('pointerup', listenersRef.current.up);
        listenersRef.current = null;
      }
      resizeStateRef.current = null;
    };

    listenersRef.current = { move: handlePointerMove, up: handlePointerUp };
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp, { once: true });
  };

  const subtitle = (senseTitle || '').trim();
  const trayLabel = subtitle
    ? (subtitle.toLowerCase().startsWith(lemma.toLowerCase()) ? subtitle : `${lemma} ${subtitle}`)
    : `${lemma} 概説`;

  return (
    <>
      {!minimized && (
        <div
          className="lemma-window"
          role="complementary"
          aria-label={`${lemma} のWordPack概要`}
          style={{ width }}
        >
          <div className="lemma-window-resizer left" onPointerDown={startResize('left')} aria-hidden="true" />
          <div className="lemma-window-resizer right" onPointerDown={startResize('right')} aria-hidden="true" />
          <header className="lemma-window-header">
            <div>
              <div className="lemma-window-title">{lemma}</div>
              {senseTitle ? <div className="lemma-window-subtitle">{senseTitle}</div> : null}
            </div>
            <div className="lemma-window-actions">
              <button type="button" className="lemma-window-minimize-btn" onClick={onMinimize} aria-label="最小化">
                最小化
              </button>
              <button type="button" className="lemma-window-close-btn" onClick={onClose} aria-label="閉じる">
                閉じる
              </button>
            </div>
          </header>
          <div className="lemma-window-body">
            {status === 'loading' ? (
              <p>読込中...</p>
            ) : status === 'error' ? (
              <p role="alert">{errorMessage || '概要の取得に失敗しました'}</p>
            ) : (
              children
            )}
            <div className="lemma-window-footer">保存済みWordPackの概要を表示しています。</div>
          </div>
        </div>
      )}
      {minimized && (
        <div className="lemma-window-tray">
          <button type="button" onClick={onRestore} aria-label={`${trayLabel} を復元`}>
            {trayLabel}
          </button>
        </div>
      )}
    </>
  );
};

