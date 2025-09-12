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
        return new Response(
          JSON.stringify({
            items: [
              { id: 'wp:test:1', lemma: 'delta', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            ],
            total: 1,
            limit: 20,
            offset: 0,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/review/stats')) {
        return new Response(JSON.stringify({ due_now: 0, reviewed_today: 0, recent: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.startsWith('/api/review/popular')) {
        return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
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
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.startsWith('/api/review/card_by_lemma?')) {
        return new Response(JSON.stringify({ repetitions: 1, interval_days: 1, due_at: new Date(Date.now() + 3600_000).toISOString() }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('カードをクリックするとモーダルでWordPack内容を表示する', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{5}{/Alt}');
    });

    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());

    await act(async () => {
      await user.click(screen.getByTestId('wp-card'));
    });

    // モーダルが開き、WordPack の概要が表示される
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'WordPack プレビュー' })).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('学習カード要点')).toBeInTheDocument());

    // 閉じる
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '閉じる' }));
    });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'WordPack プレビュー' })).not.toBeInTheDocument());
  });
});


