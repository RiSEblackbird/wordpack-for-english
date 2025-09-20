import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ArticleDetailModal, { ArticleDetailData } from './ArticleDetailModal';

describe('ArticleDetailModal', () => {
  it('displays article metadata above related word packs', () => {
    const article: ArticleDetailData = {
      id: 'art:test',
      title_en: 'Sample Title',
      body_en: 'English body',
      body_ja: '日本語本文',
      notes_ja: '補足',
      llm_model: 'gpt-5-mini',
      llm_params: 'reasoning.effort=minimal;text.verbosity=medium',
      created_at: '2024-05-01T10:00:00+09:00',
      updated_at: '2024-05-01T10:01:05+09:00',
      related_word_packs: [
        { word_pack_id: 'wp:1', lemma: 'alpha', status: 'existing' },
      ],
    };

    render(
      <ArticleDetailModal
        isOpen
        onClose={() => {}}
        title="文章プレビュー"
        article={article}
      />,
    );

    const meta = screen.getByTestId('article-meta');
    expect(meta).toHaveTextContent('作成');
    expect(meta).toHaveTextContent('更新');
    expect(meta).toHaveTextContent('生成所要時間');
    expect(meta).toHaveTextContent('AIモデル');
    expect(meta).toHaveTextContent('AIパラメータ');
    expect(meta).toHaveTextContent('gpt-5-mini');
    expect(meta).toHaveTextContent('reasoning.effort=minimal;text.verbosity=medium');
    expect(meta).toHaveTextContent('2024/05/01 10:00');
    expect(meta).toHaveTextContent('1分5秒');
    expect(screen.getByRole('heading', { level: 4, name: '関連WordPack' })).toBeInTheDocument();
  });
});
