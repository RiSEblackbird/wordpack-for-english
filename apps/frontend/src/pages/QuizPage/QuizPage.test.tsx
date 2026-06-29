import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationsProvider } from '../../NotificationsContext';
import { QuizPage } from './index';
import type { Quiz } from '../../features/quiz/types';

const authState = vi.hoisted(() => ({ isGuest: true }));

vi.mock('../../AuthContext', () => ({
  useAuth: () => ({
    isGuest: authState.isGuest,
  }),
}));

vi.mock('../../SettingsContext', () => ({
  useSettings: () => ({
    settings: {
      apiBase: '/api',
      requestTimeoutMs: 60000,
      model: 'gpt-5.4-mini',
      reasoningEffort: 'minimal',
      textVerbosity: 'medium',
      pronunciationEnabled: true,
      regenerateScope: 'all',
    },
  }),
}));

vi.mock('../../components/WordPackPreviewModal', () => ({
  WordPackPreviewModal: ({ isOpen, wordPackId }: { isOpen: boolean; wordPackId: string | null }) => (
    isOpen ? <div role="dialog" aria-label="WordPack プレビュー">Preview {wordPackId}</div> : null
  ),
}));

const quiz: Quiz = {
  id: 'quiz:alpha',
  title_en: 'Reliable API Deployments',
  format_profile: 'single_passage',
  generation_domain: 'technical',
  domain_intensity: 'standard',
  difficulty: 'medium',
  passages: [
    {
      id: 'p1',
      order: 1,
      kind: 'article',
      title: 'Deployment review',
      body_en: 'Teams mitigate latency by adding a fallback. API v2.0 rollout succeeded.\n\nThe process keeps release reviews reliable.',
      body_ja: 'チームはフォールバックを追加してレイテンシを軽減する。API v2.0の展開は成功した。このプロセスによりリリースレビューの信頼性が保たれる。',
      speaker_labels: [],
    },
  ],
  notes_ja: '根拠を本文から確認します。',
  sections: [
    {
      id: 's1',
      order: 1,
      title: 'Reading',
      description_ja: '本文理解',
      passage_ids: ['p1'],
      questions: [
        {
          id: 'q1',
          order: 1,
          type: 'detail',
          prompt: 'What reduces latency?',
          choices: [
            { id: 'A', text: 'A fallback' },
            { id: 'B', text: 'A redesign' },
            { id: 'C', text: 'A delay' },
            { id: 'D', text: 'A meeting' },
          ],
          correct_choice_id: 'A',
          explanation: {
            explanation_ja: 'fallback が latency を軽減する根拠です。',
            evidence_passage_id: 'p1',
            evidence_text: 'mitigate latency by adding a fallback',
            evidence_start: 6,
            evidence_end: 43,
            wrong_choice_explanations_ja: { B: '本文にありません。' },
            related_lemmas: ['mitigate', 'latency', 'fallback'],
          },
        },
      ],
    },
  ],
  related_word_packs: [
    {
      word_pack_id: 'wp:mitigate',
      lemma: 'mitigate',
      status: 'existing',
      is_empty: false,
      occurrences: [{ passage_id: 'p1', start: 6, end: 14 }],
      warning: null,
    },
    {
      word_pack_id: null,
      lemma: 'fallback',
      status: 'missing',
      is_empty: false,
      occurrences: [{ passage_id: 'p1', start: 35, end: 43 }],
      warning: null,
    },
    {
      word_pack_id: 'wp:latency',
      lemma: 'latency',
      status: 'existing',
      is_empty: false,
      occurrences: [],
      warning: null,
    },
  ],
  source_word_pack_ids: ['wp:mitigate'],
  source_lemmas: ['mitigate'],
  topic_seed: 'API deploy',
  avoid_topics: [],
  llm_model: 'gpt-5.4-mini',
  llm_params: 'reasoning.effort=minimal;text.verbosity=medium',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
  guest_public: true,
};

const setupFetch = () => {
  const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.startsWith('/api/quiz?')) {
      return Promise.resolve(
        new Response(JSON.stringify({
          items: [
            {
              id: quiz.id,
              title_en: quiz.title_en,
              format_profile: quiz.format_profile,
              generation_domain: quiz.generation_domain,
              domain_intensity: quiz.domain_intensity,
              difficulty: quiz.difficulty,
              question_count: 1,
              passage_count: 1,
              source_lemmas: quiz.source_lemmas,
              created_at: quiz.created_at,
              updated_at: quiz.updated_at,
              guest_public: true,
            },
          ],
          total: 1,
          limit: 50,
          offset: 0,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    }
    if (url === '/api/quiz/quiz%3Aalpha') {
      return Promise.resolve(
        new Response(JSON.stringify(quiz), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    }
    if (url === '/api/quiz/quiz%3Aalpha/guest-public' && init?.method === 'POST') {
      return Promise.resolve(
        new Response(JSON.stringify({ quiz_id: quiz.id, guest_public: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (url.startsWith('/api/word/packs?')) {
      return Promise.resolve(
        new Response(JSON.stringify({
          items: [
            {
              id: 'wp:mitigate',
              lemma: 'mitigate',
              sense_title: '軽減する',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-02T00:00:00Z',
              is_empty: false,
              guest_public: true,
              examples_count: { Dev: 1, CS: 0, LLM: 0, Business: 0, Common: 0 },
              checked_only_count: 0,
              learned_count: 0,
            },
            {
              id: 'wp:fallback-empty',
              lemma: 'fallback',
              sense_title: '',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-02T00:00:00Z',
              is_empty: true,
              guest_public: true,
              examples_count: { Dev: 0, CS: 0, LLM: 0, Business: 0, Common: 0 },
              checked_only_count: 0,
              learned_count: 0,
            },
            {
              id: 'wp:latency',
              lemma: 'latency',
              sense_title: '遅延',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-02T00:00:00Z',
              is_empty: false,
              guest_public: true,
              examples_count: { Dev: 1, CS: 1, LLM: 0, Business: 0, Common: 0 },
              checked_only_count: 0,
              learned_count: 0,
            },
            {
              id: 'wp:reliable',
              lemma: 'reliable',
              sense_title: '信頼できる',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-02T00:00:00Z',
              is_empty: false,
              guest_public: true,
              examples_count: { Dev: 0, CS: 1, LLM: 0, Business: 1, Common: 0 },
              checked_only_count: 0,
              learned_count: 0,
            },
          ],
          total: 4,
          limit: 100,
          offset: 0,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    }
    return Promise.resolve(
      new Response(JSON.stringify({ message: `unexpected ${init?.method ?? 'GET'} ${url}` }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
  });
  (globalThis as any).fetch = fetchMock;
  return fetchMock;
};

const renderQuizPage = () => render(
  <NotificationsProvider persist={false}>
    <QuizPage />
  </NotificationsProvider>,
);

describe('QuizPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    authState.isGuest = true;
    setupFetch();
  });

  it('loads a saved quiz and lets guests grade locally without saving attempts', async () => {
    const fetchMock = setupFetch();
    renderQuizPage();

    expect(screen.getByRole('heading', { name: 'Quiz' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Reliable API Deployments' })).toBeInTheDocument();
    expect(screen.getByText('ゲスト閲覧では保存できません')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成開始' })).toBeDisabled();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('radio', { name: /A fallback/ }));
      await user.click(screen.getByRole('button', { name: '採点する' }));
    });

    expect(screen.getByText('ゲスト閲覧のため採点結果は保存していません。')).toBeInTheDocument();
    expect(screen.getByText('1/1')).toBeInTheDocument();
    expect(screen.getByText('fallback が latency を軽減する根拠です。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'mitigate のWordPack操作を開く' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'latency のWordPack操作を開く' })).toBeEnabled();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/attempts'))).toBe(false);
  });

  it('opens existing WordPack links from the passage', async () => {
    renderQuizPage();
    expect(await screen.findByRole('heading', { name: 'Reliable API Deployments' })).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByText('日本語訳'));
    });
    const firstEnglishSentence = screen.getByRole('group', { name: '英文 1: 日本語訳と対応' });
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'mitigate のWordPack操作を開く' }));
    });

    expect(firstEnglishSentence).not.toHaveClass('is-pinned');
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'WordPack プレビュー' })).toHaveTextContent('wp:mitigate');
    });
  });

  it('keeps translation paragraphs aligned with English paragraphs and highlights paired sentences', async () => {
    const { container } = renderQuizPage();
    expect(await screen.findByRole('heading', { name: 'Reliable API Deployments' })).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByText('日本語訳'));
    });

    expect(container.querySelectorAll('.quiz-passage-paragraph')).toHaveLength(2);
    expect(container.querySelectorAll('.quiz-translation__paragraph')).toHaveLength(2);

    const englishSecondSentence = screen.getByRole('group', { name: '英文 2: 日本語訳と対応' });
    const japaneseSecondSentence = screen.getByRole('group', { name: '日本語訳 2: 英文と対応' });
    expect(englishSecondSentence).toHaveTextContent('API v2.0 rollout succeeded.');

    await act(async () => {
      await user.hover(englishSecondSentence);
    });

    expect(englishSecondSentence).toHaveClass('is-active');
    expect(japaneseSecondSentence).toHaveClass('is-active');

    await act(async () => {
      await user.unhover(englishSecondSentence);
      await user.click(japaneseSecondSentence);
    });

    expect(englishSecondSentence).toHaveClass('is-pinned');
    expect(japaneseSecondSentence).toHaveClass('is-pinned');
  });

  it('switches the selected quiz detail into a full-width reading layout', async () => {
    renderQuizPage();
    expect(await screen.findByRole('heading', { name: 'Reliable API Deployments' })).toBeInTheDocument();

    const generator = screen.getByRole('form', { name: 'Quiz生成フォーム' });
    const savedList = screen.getByRole('region', { name: '保存済みQuiz' });
    const user = userEvent.setup();

    const focusButton = screen.getByRole('button', { name: '本文/問題を広げる' });
    expect(focusButton).toHaveAttribute('aria-pressed', 'false');
    expect(generator).toBeVisible();
    expect(savedList).toBeVisible();

    await act(async () => {
      await user.click(focusButton);
    });

    expect(screen.getByRole('button', { name: '3カラムに戻す' })).toHaveAttribute('aria-pressed', 'true');
    expect(generator).not.toBeVisible();
    expect(savedList).not.toBeVisible();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '3カラムに戻す' }));
    });

    expect(screen.getByRole('button', { name: '本文/問題を広げる' })).toHaveAttribute('aria-pressed', 'false');
    expect(generator).toBeVisible();
    expect(savedList).toBeVisible();
  });

  it('shows only generated WordPacks and auto-fills optional lemmas from them', async () => {
    renderQuizPage();

    expect(await screen.findByRole('heading', { name: 'Reliable API Deployments' })).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: 'mitigate / 軽減する' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'latency / 遅延' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'reliable / 信頼できる' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'fallback' })).not.toBeInTheDocument();
    expect(screen.getByText('生成済みWordPackだけを表示します。未生成WordPack1件は候補から除外しています。')).toBeInTheDocument();

    const user = userEvent.setup();
    const lemmaInput = screen.getByLabelText('任意 lemma');
    await act(async () => {
      await user.clear(lemmaInput);
      await user.click(screen.getByRole('button', { name: 'お任せで3件セット' }));
    });

    expect(lemmaInput).toHaveValue('mitigate, latency, reliable');
    expect(screen.getByText('生成済みWordPackから3件のlemmaを任意lemmaにセットしました。')).toBeInTheDocument();
  });

  it('lets authenticated users toggle guest public visibility from the quiz list', async () => {
    authState.isGuest = false;
    const fetchMock = setupFetch();
    renderQuizPage();

    expect(await screen.findByRole('heading', { name: 'Reliable API Deployments' })).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '非公開にする' }));
    });

    expect(fetchMock.mock.calls.some(([input]) => String(input) === '/api/quiz/quiz%3Aalpha/guest-public')).toBe(true);
    expect(screen.getByText('Quizを非公開にしました。')).toBeInTheDocument();
  });
});
