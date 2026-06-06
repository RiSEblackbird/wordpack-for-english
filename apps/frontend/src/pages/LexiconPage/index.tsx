import React from 'react';
import { WordPackPanel } from '../../components/WordPackPanel';
import { WordPackListPanel } from '../../components/WordPackListPanel';
import { GenerationQueuePanel } from '../../components/GenerationQueuePanel';
import { Button } from '../../shared/ui';
import './lexicon.css';

interface LexiconPageProps {
  focusRef: React.RefObject<HTMLElement>;
  selectedWordPackId: string | null;
  onWordPackGenerated: (wordPackId: string | null) => void;
}

export const LexiconPage: React.FC<LexiconPageProps> = ({
  focusRef,
  onWordPackGenerated,
}) => {
  const focusCreateInput = () => {
    try { focusRef.current?.focus(); } catch {}
  };

  return (
    <div className="dictionary-main lexicon-main">
      <div className="lexicon-workspace">
        <div className="lexicon-primary">
          <div className="dictionary-page-heading lexicon-page-heading">
            <div className="dictionary-page-title">
              <h2>Lexicon</h2>
              <p>保存済みの個人辞書を検索・管理します。</p>
            </div>
            <div className="dictionary-top-actions lexicon-top-actions">
              <Button variant="primary" className="lexicon-create-shortcut" onClick={focusCreateInput}>
                <span aria-hidden="true">＋</span>
                新しいWordPack
              </Button>
            </div>
          </div>

          <section className="dictionary-section lexicon-list-section" aria-label="保存済みWordPack一覧 セクション">
            <WordPackListPanel />
          </section>
        </div>

        <section className="lexicon-rail" aria-label="生成と作成">
          <GenerationQueuePanel />
          <WordPackPanel
            focusRef={focusRef}
            onWordPackGenerated={onWordPackGenerated}
            creationPanelPlacement="inline"
            showDetails={false}
          />
        </section>
      </div>
    </div>
  );
};
