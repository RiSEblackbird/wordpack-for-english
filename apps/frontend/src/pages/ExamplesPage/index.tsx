import React from 'react';
import { ExampleListPanel } from '../../components/ExampleListPanel';
import { Badge, SearchBox } from '../../shared/ui';

export const ExamplesPage: React.FC = () => (
  <div className="dictionary-main">
    <div className="dictionary-page-heading">
      <div className="dictionary-page-title">
        <h2>Examples Corpus</h2>
        <p>問題集ではなく、自分の用例コーパスとして横断検索する。</p>
      </div>
      <div className="dictionary-top-actions">
        <SearchBox label="例文を検索" placeholder="Search examples: deploy fallback" shortcut="⌘K" />
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
);

