import React from 'react';
import { AppRightRail, RailCard } from '../../components/AppRightRail';
import { ArticleImportPanel } from '../../components/ArticleImportPanel';
import { ArticleListPanel } from '../../components/ArticleListPanel';
import { Badge, SearchBox } from '../../shared/ui';

export const ReaderPage: React.FC = () => (
  <div className="dictionary-main">
    <div className="dictionary-workspace">
      <div className="dictionary-primary">
        <div className="dictionary-page-heading">
          <div className="dictionary-page-title">
            <h2>Reader</h2>
            <p>
              文章を読み込み、文脈の中で気になった語をWordPackへつなぎます。
            </p>
          </div>
          <div className="dictionary-top-actions">
            <SearchBox
              label="記事を検索"
              placeholder="記事タイトルや本文で検索"
            />
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
      <AppRightRail>
        <RailCard title="作業の流れ" badge="context">
          <ol className="dictionary-rail-steps">
            <li>文章を貼り付けて保存します。</li>
            <li>文章内の語をWordPackへ接続します。</li>
            <li>生成や再生成の進行はここで追跡します。</li>
          </ol>
        </RailCard>
      </AppRightRail>
    </div>
  </div>
);
