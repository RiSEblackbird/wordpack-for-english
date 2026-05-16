import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ExplorePage } from './index';
import type { WordPack } from '../../features/wordpack/types';

vi.mock('../../SettingsContext', () => ({
  useSettings: () => ({
    settings: {
      apiBase: '/api',
      requestTimeoutMs: 60000,
    },
  }),
}));

const wordPackDetail: WordPack = {
  lemma: 'robust',
  sense_title: '壊れにくい',
  pronunciation: { linking_notes: [] },
  senses: [
    {
      id: 's1',
      gloss_ja: '壊れにくい',
      patterns: ['robust against N'],
      synonyms: ['resilient'],
      antonyms: ['fragile'],
    },
  ],
  collocations: {
    general: {
      verb_object: [],
      adj_noun: ['robust fallback', 'robust evidence'],
      prep_noun: [],
    },
    academic: {
      verb_object: [],
      adj_noun: [],
      prep_noun: [],
    },
  },
  contrast: [{ with: 'brittle', diff_ja: 'brittle は壊れやすさを示す。' }],
  examples: {
    Dev: [{ en: 'The service uses a robust fallback.', ja: 'サービスは堅牢なフォールバックを使う。' }],
    CS: [],
    LLM: [],
    Business: [],
    Common: [],
  },
  etymology: { note: 'test', confidence: 'low' },
  study_card: 'test',
  citations: [],
  confidence: 'low',
};

const setupFetch = () => {
  const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.startsWith('/api/word/packs?')) {
      return Promise.resolve(
        new Response(JSON.stringify({
          items: [
            {
              id: 'wp:robust',
              lemma: 'robust',
              sense_title: '壊れにくい',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-02T00:00:00Z',
              is_empty: false,
              guest_public: true,
              examples_count: { Dev: 1, CS: 0, LLM: 0, Business: 0, Common: 0 },
              checked_only_count: 1,
              learned_count: 0,
            },
            {
              id: 'wp:fallback',
              lemma: 'fallback',
              sense_title: '代替手段',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
              is_empty: false,
              guest_public: true,
              examples_count: { Dev: 0, CS: 0, LLM: 0, Business: 0, Common: 0 },
              checked_only_count: 0,
              learned_count: 0,
            },
          ],
          total: 2,
          limit: 200,
          offset: 0,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    }
    if (url.endsWith('/api/word/packs/wp:robust')) {
      return Promise.resolve(
        new Response(JSON.stringify(wordPackDetail), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    }
    return Promise.resolve(
      new Response(JSON.stringify({ ...wordPackDetail, lemma: 'fallback', sense_title: '代替手段' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
  });
  (globalThis as any).fetch = fetchMock;
  return fetchMock;
};

describe('ExplorePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupFetch();
  });

  it('loads existing WordPacks and shows relation cards from selected detail', async () => {
    render(<ExplorePage />);

    expect(screen.getByRole('heading', { name: 'Explore' })).toBeInTheDocument();
    expect(screen.getByLabelText('探索する lemma を検索')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /robust/ })).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Collocations' }));
    });

    expect(screen.getByRole('button', { name: 'Collocations' })).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('robust fallback')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '開く' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '未作成' })).toBeDisabled();

    await act(async () => {
      await user.type(screen.getByLabelText('探索する lemma を検索'), 'fall');
    });

    await waitFor(() => expect(screen.queryByRole('button', { name: /robust/ })).not.toBeInTheDocument());
    expect(screen.getByRole('button', { name: /fallback/ })).toBeInTheDocument();
  });
});
