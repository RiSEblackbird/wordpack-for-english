import React from 'react';
import { ArticleImportPanel } from '../../components/ArticleImportPanel';
import { ArticleListPanel } from '../../components/ArticleListPanel';
import { Badge, SearchBox } from '../../shared/ui';

export const ReaderPage: React.FC = () => (
  <div className="dictionary-main">
    <div className="dictionary-page-heading">
      <div className="dictionary-page-title">
        <h2>Reader</h2>
        <p>文章を教材化せず、読んで気になった語を辞書へつなぐ読解机。</p>
      </div>
      <div className="dictionary-top-actions">
        <SearchBox label="記事と抽出語を検索" placeholder="Search articles, lemmas..." />
      </div>
    </div>
    <div className="dictionary-grid two-column">
      <section className="dictionary-section">
        <div className="dictionary-section-header">
          <div>
            <h3>Paste / import text</h3>
            <p>4,000文字以内の文章を読み込み、関連 WordPack へ接続します。</p>
          </div>
          <Badge variant="accent">reader desk</Badge>
        </div>
        <ArticleImportPanel />
      </section>
      <aside className="dictionary-section" aria-label="Reader side peek preview">
        <div className="dictionary-section-header">
          <div>
            <h3>Extracted words</h3>
            <p>本文から拾った語を右側で開くための余白です。</p>
          </div>
        </div>
        <div className="dictionary-reader-canvas">
          <strong>API reliability notes</strong>
          <p>
            The service deployed a <mark>robust</mark> fallback when the upstream API failed.
          </p>
          <p>本文中の lemma は既存の詳細/例文コンポーネント側の hover/click 導線を維持します。</p>
        </div>
      </aside>
    </div>
    <section className="dictionary-section">
      <ArticleListPanel />
    </section>
  </div>
);

