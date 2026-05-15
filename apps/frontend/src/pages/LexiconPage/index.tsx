import React from 'react';
import { WordPackPanel } from '../../components/WordPackPanel';
import { WordPackListPanel } from '../../components/WordPackListPanel';
import { Badge, SearchBox } from '../../shared/ui';

interface LexiconPageProps {
  focusRef: React.RefObject<HTMLElement>;
  selectedWordPackId: string | null;
  onWordPackGenerated: (wordPackId: string | null) => void;
}

export const LexiconPage: React.FC<LexiconPageProps> = ({
  focusRef,
  selectedWordPackId,
  onWordPackGenerated,
}) => (
  <div className="dictionary-main">
    <div className="dictionary-page-heading">
      <div className="dictionary-page-title">
        <h2>Lexicon</h2>
        <p>検索して、開いて、用例と文脈へ辿る個人辞書。</p>
      </div>
      <div className="dictionary-top-actions">
        <SearchBox label="WordPack、用例、記事を検索" placeholder="Search WordPack, examples, articles..." shortcut="⌘K" />
      </div>
    </div>

    <section className="dictionary-section" aria-label="Lexicon overview">
      <div className="dictionary-section-header">
        <div>
          <h3>Recently touched</h3>
          <p>辞書記事への入口。生成や管理は控えめな道具としてここに残します。</p>
        </div>
        <div className="dictionary-meta-row">
          <Badge variant="accent">dictionary first</Badge>
          <Badge>guest public</Badge>
          <Badge>empty entries</Badge>
        </div>
      </div>
      <WordPackPanel
        focusRef={focusRef}
        selectedWordPackId={selectedWordPackId}
        onWordPackGenerated={onWordPackGenerated}
      />
    </section>

    <section className="dictionary-section" aria-label="保存済みWordPack一覧 セクション">
      <WordPackListPanel />
    </section>
  </div>
);

