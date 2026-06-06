import React from "react";
import { AppRightRail, RailCard } from "../../components/AppRightRail";
import { WordPackPanel } from "../../components/WordPackPanel";
import { Badge, Button } from "../../shared/ui";

interface WordPackDetailPageProps {
  focusRef: React.RefObject<HTMLElement>;
  wordPackId: string;
  onBackToLexicon: () => void;
}

export const WordPackDetailPage: React.FC<WordPackDetailPageProps> = ({
  focusRef,
  wordPackId,
  onBackToLexicon,
}) => (
  <div className="dictionary-main">
    <div className="dictionary-workspace">
      <div className="dictionary-primary">
        <div className="dictionary-page-heading">
          <div className="dictionary-page-title">
            <h2>WordPack</h2>
            <p>辞書記事として読み、必要な用例だけを生成・練習します。</p>
          </div>
          <div className="dictionary-top-actions">
            <Badge variant="accent">dictionary article</Badge>
            <Button variant="subtle" onClick={onBackToLexicon}>
              Lexiconへ戻る
            </Button>
          </div>
        </div>
        <section className="dictionary-section">
          <WordPackPanel focusRef={focusRef} selectedWordPackId={wordPackId} />
        </section>
      </div>
      <AppRightRail>
        <RailCard title="この記事の作業" badge="detail">
          <p className="dictionary-rail-copy">
            例文追加や再生成を実行しても、進行状況は他画面と同じ生成キューに残ります。
          </p>
        </RailCard>
      </AppRightRail>
    </div>
  </div>
);
