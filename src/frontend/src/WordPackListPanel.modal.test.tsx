import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { App } from './App';
import { vi } from 'vitest';

describe('WordPackListPanel modal preview', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function setupFetchMocks() {
    const mock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: any) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      if (url.endsWith('/api/config') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.startsWith('/api/word/packs?')) {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000);
        
        return new Response(
          JSON.stringify({
            items: [
              { 
                id: 'wp:test:1', 
                lemma: 'delta', 
                created_at: twoDaysAgo.toISOString(), 
                updated_at: yesterday.toISOString(), 
                is_empty: true 
              },
              { 
                id: 'wp:test:2', 
                lemma: 'alpha', 
                created_at: yesterday.toISOString(), 
                updated_at: now.toISOString(), 
                is_empty: false,
                examples_count: { Dev: 2, CS: 1, LLM: 0, Business: 3, Common: 4 }
              },
              { 
                id: 'wp:test:3', 
                lemma: 'beta', 
                created_at: now.toISOString(), 
                updated_at: twoDaysAgo.toISOString(), 
                is_empty: false,
                examples_count: { Dev: 1, CS: 2, LLM: 1, Business: 1, Common: 2 }
              },
            ],
            total: 3,
            limit: 20,
            offset: 0,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      
      if (url.endsWith('/api/word/packs/wp:test:1')) {
        return new Response(
          JSON.stringify({
            lemma: 'delta',
            pronunciation: { ipa_GA: null, ipa_RP: null, syllables: null, stress_index: null, linking_notes: [] },
            senses: [{ id: 's1', gloss_ja: '意味', definition_ja: '定義', nuances_ja: 'ニュアンス', patterns: ['p1'], synonyms: ['syn'], antonyms: ['ant'], register: 'formal', notes_ja: '注意' }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: {
              Dev: [
                { en: `delta dev one about twenty five words overall in context.`, ja: `delta Dev例1`, grammar_ja: '第3文型' },
                { en: `delta dev two showcasing config and deployment narrative.`, ja: `delta Dev例2`, grammar_ja: '関係節' },
                { en: `delta dev three clarifying API stability and versioning.`, ja: `delta Dev例3`, grammar_ja: '前置詞句' },
                { en: `delta dev four reflecting review feedback and fixes.`, ja: `delta Dev例4`, grammar_ja: '不定詞' },
                { en: `delta dev five discussing refactor and readability.`, ja: `delta Dev例5`, grammar_ja: '分詞構文' },
              ],
              CS: [],
              LLM: [],
              Business: [
                { en: `In practice, estimates delta as constraints relax and noise diminishes.`, ja: `Business例1`, grammar_ja: '受動態' },
                { en: `Optimization routines delta when gradients vanish near stationary points.`, ja: `Business例2`, grammar_ja: '分詞' },
                { en: `Signals delta across nodes under synchronized sampling schedules.`, ja: `Business例3`, grammar_ja: '関係代名詞' },
              ],
              Common: [
                { en: `Paths delta near the central plaza after sunset.`, ja: `Common例1`, grammar_ja: '副詞句' },
                { en: `Their plans delta as deadlines approach.`, ja: `Common例2`, grammar_ja: '現在形' },
                { en: `Our views delta with more data and reflection.`, ja: `Common例3`, grammar_ja: '進行形' },
                { en: `Schedules delta around meetings and travel.`, ja: `Common例4`, grammar_ja: '前置詞句' },
                { en: `Tastes delta as we try new cuisines.`, ja: `Common例5`, grammar_ja: '三単現' },
                { en: `The lines delta at the corner of the page.`, ja: `Common例6`, grammar_ja: '受動態' },
              ],
            },
            etymology: { note: '-', confidence: 'low' },
            study_card: `study of delta`,
            citations: [{ text: 'citation' }],
            confidence: 'medium',
            // For UI rendering of AI info under 更新 row (from list meta)
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/word/packs/wp:test:2')) {
        return new Response(
          JSON.stringify({
            lemma: 'alpha',
            pronunciation: { ipa_GA: null, ipa_RP: null, syllables: null, stress_index: null, linking_notes: [] },
            senses: [{ id: 's1', gloss_ja: '意味', definition_ja: '定義', nuances_ja: 'ニュアンス', patterns: ['p1'], synonyms: ['syn'], antonyms: ['ant'], register: 'formal', notes_ja: '注意' }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: {
              Dev: [
                { en: `alpha dev one about twenty five words overall in context.`, ja: `alpha Dev例1`, grammar_ja: '第3文型' },
                { en: `alpha dev two showcasing config and deployment narrative.`, ja: `alpha Dev例2`, grammar_ja: '関係節' },
              ],
              CS: [
                { en: `alpha cs one about computer science concepts.`, ja: `alpha CS例1`, grammar_ja: '第3文型' },
              ],
              LLM: [],
              Business: [
                { en: `In practice, estimates alpha as constraints relax and noise diminishes.`, ja: `Business例1`, grammar_ja: '受動態' },
                { en: `Optimization routines alpha when gradients vanish near stationary points.`, ja: `Business例2`, grammar_ja: '分詞' },
                { en: `Signals alpha across nodes under synchronized sampling schedules.`, ja: `Business例3`, grammar_ja: '関係代名詞' },
              ],
              Common: [
                { en: `Paths alpha near the central plaza after sunset.`, ja: `Common例1`, grammar_ja: '副詞句' },
                { en: `Their plans alpha as deadlines approach.`, ja: `Common例2`, grammar_ja: '現在形' },
                { en: `Our views alpha with more data and reflection.`, ja: `Common例3`, grammar_ja: '進行形' },
                { en: `Schedules alpha around meetings and travel.`, ja: `Common例4`, grammar_ja: '前置詞句' },
              ],
            },
            etymology: { note: '-', confidence: 'low' },
            study_card: `study of alpha`,
            citations: [{ text: 'citation' }],
            confidence: 'medium',
            // For UI rendering of AI info under 更新 row (from list meta)
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      
      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('カードをクリックするとモーダルでWordPack内容を表示する（WordPackタブ統合後）', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();

    // WordPack タブへ（デフォルトがWordPackのため念のためAlt+4で明示）
    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });

    // 統合された一覧のヘッダーが表示される
    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());

    // 例文未生成バッジ表示
    await waitFor(() => expect(screen.getByText('例文未生成')).toBeInTheDocument());

    // カードをクリック
    const cards = screen.getAllByTestId('wp-card');
    expect(cards).toHaveLength(3);
    
    // カードがクリック可能になるまで少し待機
    await waitFor(() => expect(cards[0]).toBeInTheDocument());
    
    await act(async () => {
      await user.click(cards[0]);
    });

    // モーダルが開くまで待機
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'WordPack プレビュー' })).toBeInTheDocument(), { timeout: 5000 });
    
    // WordPackの詳細が読み込まれるまで待機（モーダル内の内容を一意に特定）
    const modalContent = await waitFor(() => screen.getByTestId('modal-wordpack-content'), { timeout: 10000 });
    expect(modalContent).toHaveTextContent('学習カード要点');

    // 閉じる
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '閉じる' }));
    });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'WordPack プレビュー' })).not.toBeInTheDocument(), { timeout: 3000 });
  }, 15000);

  it('ソート機能が正しく動作する', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();

    // WordPack タブへ
    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });

    // 一覧が表示されるまで待機
    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByTestId('wp-card')).toHaveLength(3));

    // デフォルトは更新日時降順（alpha, delta, beta）
    const cards = screen.getAllByTestId('wp-card');
    expect(cards[0]).toHaveTextContent(/alpha/);
    expect(cards[1]).toHaveTextContent(/delta/);
    expect(cards[2]).toHaveTextContent(/beta/);

    // 単語名でソート（昇順）
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('並び順:'), 'lemma');
    });
    await act(async () => {
      await user.click(screen.getByTitle('昇順'));
    });

    // alpha, beta, delta の順になる
    const sortedCards = screen.getAllByTestId('wp-card');
    expect(sortedCards[0]).toHaveTextContent(/alpha/);
    expect(sortedCards[1]).toHaveTextContent(/beta/);
    expect(sortedCards[2]).toHaveTextContent(/delta/);

    // 例文数でソート（降順）
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('並び順:'), 'total_examples');
    });
    await act(async () => {
      await user.click(screen.getByTitle('降順'));
    });

    // alpha(10), beta(7), delta(0) の順になる
    const exampleSortedCards = screen.getAllByTestId('wp-card');
    expect(exampleSortedCards[0]).toHaveTextContent(/alpha/);
    expect(exampleSortedCards[1]).toHaveTextContent(/beta/);
    expect(exampleSortedCards[2]).toHaveTextContent(/delta/);
  }, 10000);

  it('表示絞り込み（生成済/未生成/-）が正しく動作する', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();

    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });

    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByTestId('wp-card')).toHaveLength(3));

    // 生成済のみ
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('表示絞り込み:'), 'generated');
    });
    await waitFor(() => expect(screen.getAllByTestId('wp-card')).toHaveLength(2));
    const genCards = screen.getAllByTestId('wp-card');
    expect(genCards[0]).not.toHaveTextContent(/delta/);
    expect(genCards[1]).not.toHaveTextContent(/delta/);

    // 未生成のみ
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('表示絞り込み:'), 'not_generated');
    });
    const notGenCards = await waitFor(() => screen.getAllByTestId('wp-card'));
    expect(notGenCards).toHaveLength(1);
    expect(notGenCards[0]).toHaveTextContent(/delta/);

    // すべて（-）
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('表示絞り込み:'), 'all');
    });
    await waitFor(() => expect(screen.getAllByTestId('wp-card')).toHaveLength(3));
  }, 10000);

  it('検索機能（前方/後方/部分一致と適用操作）が正しく動作する', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();

    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });

    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByTestId('wp-card')).toHaveLength(3));

    // 前方一致 + ボタン適用: "al" -> alpha のみ
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('検索:'), 'prefix');
      await user.clear(screen.getByLabelText('検索文字列'));
      await user.type(screen.getByLabelText('検索文字列'), 'al');
      await user.click(screen.getByRole('button', { name: '検索' }));
    });
    const prefixCards = await waitFor(() => screen.getAllByTestId('wp-card'));
    expect(prefixCards).toHaveLength(1);
    expect(prefixCards[0]).toHaveTextContent(/alpha/);

    // 後方一致 + Enter適用: "ta" -> beta, delta
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('検索:'), 'suffix');
      const input = screen.getByLabelText('検索文字列');
      await user.clear(input);
      await user.type(input, 'ta');
      await user.keyboard('{Enter}');
    });
    const suffixCards = await waitFor(() => screen.getAllByTestId('wp-card'));
    expect(suffixCards).toHaveLength(2);
    expect(suffixCards.some(c => /beta/i.test(c.textContent || ''))).toBe(true);
    expect(suffixCards.some(c => /delta/i.test(c.textContent || ''))).toBe(true);

    // 部分一致 + ボタン適用: "et" -> beta のみ
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('検索:'), 'contains');
      await user.clear(screen.getByLabelText('検索文字列'));
      await user.type(screen.getByLabelText('検索文字列'), 'et');
      await user.click(screen.getByRole('button', { name: '検索' }));
    });
    const containsCards = await waitFor(() => screen.getAllByTestId('wp-card'));
    expect(containsCards).toHaveLength(1);
    expect(containsCards[0]).toHaveTextContent(/beta/);

    // 空文字で検索を再適用すると、全件（3件）に戻る
    await act(async () => {
      await user.clear(screen.getByLabelText('検索文字列'));
      await user.click(screen.getByRole('button', { name: '検索' }));
    });
    await waitFor(() => expect(screen.getAllByTestId('wp-card')).toHaveLength(3));
  }, 12000);
});


