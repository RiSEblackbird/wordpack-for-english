import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { App } from './App';
import { vi } from 'vitest';

describe('WordPackPanel E2E (mocked fetch)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function setupFetchMocks() {
    const mock = vi.spyOn(global, 'fetch' as any).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      if (url.endsWith('/api/review/stats')) {
        return new Response(JSON.stringify({ due_now: 1, reviewed_today: 0, recent: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.startsWith('/api/review/popular')) {
        return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.endsWith('/api/word/pack') && init?.method === 'POST') {
        const body = init?.body ? JSON.parse(init.body as string) : {};
        const lemma = body.lemma || 'test';
        return new Response(
          JSON.stringify({
            lemma,
            pronunciation: { ipa_GA: null, ipa_RP: null, syllables: null, stress_index: null, linking_notes: [] },
            senses: [{ id: 's1', gloss_ja: '意味', definition_ja: '定義', nuances_ja: 'ニュアンス', patterns: ['p1'], synonyms: ['syn'], antonyms: ['ant'], register: 'formal', notes_ja: '注意' }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: {
              A1: [
                { en: `${lemma} example one with around twenty five tokens total.`, ja: `${lemma} の例文1`, grammar_ja: '第3文型' },
                { en: `${lemma} example two includes subordinate clauses and clear structure.`, ja: `${lemma} の例文2`, grammar_ja: '関係節' },
                { en: `${lemma} example three demonstrates prepositional phrases effectively.`, ja: `${lemma} の例文3`, grammar_ja: '前置詞句' },
              ],
              B1: [
                { en: `This ${lemma} sentence explains a concept in moderate complexity.`, ja: `${lemma} の例文4`, grammar_ja: '分詞構文' },
                { en: `Writers often ${lemma} when evidence points in the same direction.`, ja: `${lemma} の例文5`, grammar_ja: '時制一致' },
                { en: `Over time, ideas ${lemma} and form a coherent perspective.`, ja: `${lemma} の例文6`, grammar_ja: '副詞句' },
              ],
              C1: [
                { en: `Scholars ${lemma} on nuanced interpretations as methodologies mature.`, ja: `${lemma} の例文7`, grammar_ja: '倒置' },
                { en: `As constraints relax, results ${lemma} toward a stable equilibrium.`, ja: `${lemma} の例文8`, grammar_ja: '従属節' },
                { en: `Once assumptions hold, estimates ${lemma} with provable guarantees.`, ja: `${lemma} の例文9`, grammar_ja: '仮定法' },
              ],
              tech: [
                { en: `Under mild assumptions, iterative updates ${lemma} to a local optimum.`, ja: `技術例1`, grammar_ja: '不定詞' },
                { en: `Multiple models ${lemma} when trained on sufficiently diverse datasets.`, ja: `技術例2`, grammar_ja: '関係代名詞' },
                { en: `Gradients ${lemma} as the learning rate decays over epochs.`, ja: `技術例3`, grammar_ja: '分詞' },
                { en: `Posterior distributions ${lemma} given informative priors and larger samples.`, ja: `技術例4`, grammar_ja: '受動態' },
                { en: `Independent estimates ${lemma} despite heterogeneous measurement noise.`, ja: `技術例5`, grammar_ja: '譲歩構文' },
              ],
            },
            etymology: { note: '-', confidence: 'low' },
            study_card: `study of ${lemma}`,
            citations: [{ text: 'citation' }],
            confidence: 'medium',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.startsWith('/api/review/card_by_lemma?')) {
        return new Response(JSON.stringify({ repetitions: 1, interval_days: 1, due_at: new Date(Date.now() + 3600_000).toISOString() }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.endsWith('/api/review/grade_by_lemma') && init?.method === 'POST') {
        return new Response(JSON.stringify({ ok: true, next_due: new Date(Date.now() + 3600_000).toISOString() }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('generates WordPack and grades via buttons', async () => {
    const fetchMock = setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });

    const input = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    await act(async () => {
      await user.type(input, 'delta');
      await user.click(screen.getByRole('button', { name: '生成' }));
    });

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('WordPack を生成しました'));
    // study_card 内容が表示される
    expect(screen.getByText('学習カード要点')).toBeInTheDocument();

    // 例文カードUI: 英/訳/解説ラベルのうち「解説」が表示されること
    // （モック例文には grammar_ja が含まれている）
    expect(screen.getAllByText(/解説/).length).toBeGreaterThan(0);

    // 採点（○）
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '○ できた (3)' }));
    });

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('採点しました'));

    // fetch が正しいエンドポイントで呼ばれていること
    const urls = fetchMock.mock.calls.map((c) => (typeof c[0] === 'string' ? c[0] : (c[0] as URL).toString()));
    expect(urls.some((u) => u.endsWith('/api/word/pack'))).toBe(true);
    expect(urls.some((u) => u.endsWith('/api/review/grade_by_lemma'))).toBe(true);
  });
});


