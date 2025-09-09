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
              Dev: [
                { en: `${lemma} dev example one with around twenty five tokens total.`, ja: `${lemma} のDev例文1`, grammar_ja: '第3文型' },
                { en: `${lemma} dev example two includes subordinate clauses and clear structure.`, ja: `${lemma} のDev例文2`, grammar_ja: '関係節' },
                { en: `${lemma} dev example three demonstrates prepositional phrases effectively.`, ja: `${lemma} のDev例文3`, grammar_ja: '前置詞句' },
                { en: `${lemma} dev example four focuses on application context and clarity.`, ja: `${lemma} のDev例文4`, grammar_ja: '不定詞' },
                { en: `${lemma} dev example five reflects code-review style feedback.`, ja: `${lemma} のDev例文5`, grammar_ja: '分詞構文' },
              ],
              CS: [
                { en: `In computer science, results ${lemma} toward a coherent theory under constraints.`, ja: `${lemma} のCS例文1`, grammar_ja: '倒置' },
                { en: `As complexity grows, algorithms ${lemma} on shared invariants.`, ja: `${lemma} のCS例文2`, grammar_ja: '従属節' },
                { en: `Formal proofs ${lemma} as lemmas link foundational claims.`, ja: `${lemma} のCS例文3`, grammar_ja: '仮定法' },
                { en: `Empirical results ${lemma} across benchmarks when variables are controlled.`, ja: `${lemma} のCS例文4`, grammar_ja: '受動態' },
                { en: `Theoretical bounds ${lemma} under relaxed assumptions.`, ja: `${lemma} のCS例文5`, grammar_ja: '関係代名詞' },
              ],
              LLM: [
                { en: `LLM outputs ${lemma} with more context provided via system prompts.`, ja: `LLM例文1`, grammar_ja: '時制一致' },
                { en: `Fine-tuned models ${lemma} on domain-specific jargon effectively.`, ja: `LLM例文2`, grammar_ja: '前置詞句' },
                { en: `Safety mitigations ${lemma} as alignment objectives are strengthened.`, ja: `LLM例文3`, grammar_ja: '分詞' },
                { en: `Evaluation metrics ${lemma} when test sets reflect real usage.`, ja: `LLM例文4`, grammar_ja: '従属節' },
                { en: `Chain-of-thought traces ${lemma} with improved reasoning over steps.`, ja: `LLM例文5`, grammar_ja: '不定詞' },
              ],
              Tech: [
                { en: `Under mild assumptions, iterative updates ${lemma} to a local optimum.`, ja: `Tech例1`, grammar_ja: '不定詞' },
                { en: `Multiple systems ${lemma} when signals stabilize over time.`, ja: `Tech例2`, grammar_ja: '関係代名詞' },
                { en: `Gradients ${lemma} as learning rates decay across epochs.`, ja: `Tech例3`, grammar_ja: '分詞' },
              ],
              Common: [
                { en: `Over months, ideas ${lemma} into a clear plan.`, ja: `Common例1`, grammar_ja: '副詞句' },
                { en: `Our opinions ${lemma} after discussing the options.`, ja: `Common例2`, grammar_ja: '現在完了' },
                { en: `Paths ${lemma} at the main square downtown.`, ja: `Common例3`, grammar_ja: '前置詞句' },
                { en: `Tastes ${lemma} as people grow older and gain experience.`, ja: `Common例4`, grammar_ja: '現在形' },
                { en: `Schedules ${lemma} around the team’s availability.`, ja: `Common例5`, grammar_ja: '三単現' },
                { en: `Trains ${lemma} at this station every hour.`, ja: `Common例6`, grammar_ja: '進行形' },
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


