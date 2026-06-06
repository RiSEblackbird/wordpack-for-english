import React from 'react';
import { WordPackPanel } from '../../components/WordPackPanel';
import { WordPackListPanel } from '../../components/WordPackListPanel';
import { SearchBox } from '../../shared/ui';

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

    <WordPackPanel
      focusRef={focusRef}
      selectedWordPackId={selectedWordPackId}
      onWordPackGenerated={onWordPackGenerated}
    />

    <section className="dictionary-section" aria-label="保存済みWordPack一覧 セクション">
      <WordPackListPanel />
    </section>
  </div>
);
