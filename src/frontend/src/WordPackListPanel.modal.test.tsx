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
    const mock = vi.spyOn(global, 'fetch' as any).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
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
            senses: [{ id: 's1', gloss_ja: '意味', patterns: [] }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: { A1: [{ en: `delta example.`, ja: `delta の例文` }], B1: [], C1: [], tech: [] },
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

  it('opens modal and shows WordPack content when clicking 表示', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{5}{/Alt}');
    });

    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '表示' }));
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


