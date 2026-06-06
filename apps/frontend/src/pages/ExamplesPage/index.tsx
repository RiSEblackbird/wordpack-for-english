import React from 'react';
import { AppRightRail, RailCard } from '../../components/AppRightRail';
import { ExampleListPanel } from '../../components/ExampleListPanel';
import { Badge, SearchBox } from '../../shared/ui';

export const ExamplesPage: React.FC = () => (
  <div className="dictionary-main">
    <div className="dictionary-workspace">
      <div className="dictionary-primary">
        <div className="dictionary-page-heading">
          <div className="dictionary-page-title">
            <h2>Examples</h2>
            <p>保存済み用例を横断検索し、語の使われ方だけを比較します。</p>
          </div>
          <div className="dictionary-top-actions">
            <SearchBox
              label="例文を検索"
              placeholder="語句や文脈で検索"
              shortcut="⌘K"
            />
          </div>
        </div>
        <section className="dictionary-section">
          <div className="dictionary-section-header">
            <div>
              <h3>KWIC view</h3>
              <p>前後の語を揃え、用法の違いだけを素早く見ます。</p>
            </div>
            <div className="dictionary-meta-row">
              <Badge variant="accent">KWIC</Badge>
              <Badge>Dev</Badge>
              <Badge>CS</Badge>
              <Badge>LLM</Badge>
              <Badge>Business</Badge>
              <Badge>Common</Badge>
            </div>
          </div>
          <ExampleListPanel />
        </section>
      </div>
      <AppRightRail>
        <RailCard title="コーパスの見方" badge="KWIC">
          <p className="dictionary-rail-copy">
            検索、カテゴリ絞り込み、展開表示の設定は保持されます。生成中の用例追加は画面を移動しても同じキューに残ります。
          </p>
        </RailCard>
      </AppRightRail>
    </div>
  </div>
);
