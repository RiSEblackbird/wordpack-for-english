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
            senses: [{ id: 's1', gloss_ja: '意味', patterns: [] }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: { A1: [{ en: `${lemma} example.`, ja: `${lemma} の例文` }], B1: [], C1: [], tech: [] },
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


