import React from 'react';
import { LemmaExplorerWindow } from '../LemmaExplorerWindow';
import { LemmaExplorerState } from './useLemmaExplorer';

interface LemmaExplorerPanelProps {
  explorer: LemmaExplorerState | null;
  content: React.ReactNode;
  onClose: () => void;
  onMinimize: () => void;
  onRestore: () => void;
  onResize: (nextWidth: number) => void;
}

/**
 * LemmaExplorerWindowの組立専用コンポーネント。
 * - WordPackPanelからは状態とハンドラを受け取るだけにし、UI構築を本コンポーネントで完結させる。
 */
export const LemmaExplorerPanel: React.FC<LemmaExplorerPanelProps> = ({
  explorer,
  content,
  onClose,
  onMinimize,
  onRestore,
  onResize,
}) => {
  if (!explorer) return null;

  return (
    <LemmaExplorerWindow
      lemma={explorer.lemma}
      senseTitle={explorer.senseTitle}
      minimized={explorer.minimized}
      width={explorer.width}
      status={explorer.status}
      errorMessage={explorer.errorMessage}
      onClose={onClose}
      onMinimize={onMinimize}
      onRestore={onRestore}
      onResize={onResize}
    >
      {content}
    </LemmaExplorerWindow>
  );
};

