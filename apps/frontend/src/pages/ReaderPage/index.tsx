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
        <SearchBox label="記事を検索" placeholder="Search articles..." />
      </div>
    </div>
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
    <section className="dictionary-section">
      <ArticleListPanel />
    </section>
  </div>
);
