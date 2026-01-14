import { render, screen, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';
import { ARTICLE_IMPORT_TEXT_MAX_LENGTH } from './constants/article';

describe('ArticleImportPanel model/params wiring (mocked fetch)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).fetch = vi.fn();
    try {
      localStorage.setItem(
        'wordpack.auth.v1',
        JSON.stringify({
          authMode: 'authenticated',
          user: { google_sub: 'tester', email: 'tester@example.com', display_name: 'Tester' },
        }),
      );
    } catch {}
  });

  afterEach(() => {
    try { localStorage.removeItem('wordpack.auth.v1'); } catch {}
  });

  const renderWithAuth = () =>
    render(
      <AppProviders googleClientId="test-client">
        <App />
      </AppProviders>,
    );

  function setupFetchMocks() {
    const mock = vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      if (url.endsWith('/api/config') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }
      if (url.endsWith('/api/article/import') && init?.method === 'POST') {
        return new Response(
          JSON.stringify({ id: 'art:abcd1234' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/article/generate_and_import') && init?.method === 'POST') {
        return new Response(
          JSON.stringify({ lemma: 'test', word_pack_id: 'wp:test:abcd', category: 'Common', generated_examples: 2, article_ids: ['art:1', 'art:2'] }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/article/art:abcd1234') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({
            id: 'art:abcd1234',
            title_en: 'Title',
            body_en: 'Body EN',
            body_ja: 'Body JA',
            llm_model: 'gpt-5-mini',
            llm_params: 'reasoning.effort=minimal;text.verbosity=medium',
            related_word_packs: [
              { word_pack_id: 'wp:regen:1', lemma: 'alpha', status: 'existing', is_empty: false },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/word/packs/wp:regen:1/regenerate/async') && init?.method === 'POST') {
        return new Response(
          JSON.stringify({ job_id: 'job:regen:1', status: 'succeeded' }),
          { status: 202, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/word/packs/wp:regen:1/regenerate/jobs/job:regen:1')) {
        return new Response(
          JSON.stringify({ job_id: 'job:regen:1', status: 'succeeded' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  const openTab = async (user: ReturnType<typeof userEvent.setup>, label: string) => {
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(toggle);
    });
    const tabButton = await screen.findByRole('button', { name: label });
    await act(async () => {
      await user.click(tabButton);
    });
  };

  it('sends model/temperature for sampling model on import', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    // モデルUIが表示される
    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-4o-mini');
    });

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello world');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    // リクエスト検証
    const calls = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(calls.length).toBeGreaterThan(0);
    expect(calls.some((b) => b.model === 'gpt-4o-mini' && typeof b.temperature === 'number' && !('reasoning' in b) && !('text_opts' in b))).toBe(true);
  });

  it('sends reasoning/text_opts for gpt-5-mini on import, and reasoning/text on generate_and_import', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    // gpt-5-mini 選択で追加UIが表示
    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-5-mini');
    });
    expect(screen.getByLabelText('reasoning.effort')).toBeInTheDocument();
    expect(screen.getByLabelText('text.verbosity')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello world 2');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const importBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(importBodies.some((b) => b.model === 'gpt-5-mini' && b.reasoning && b.text_opts && !('temperature' in b))).toBe(true);

    // 生成＆インポートでも同様のパラメータ（text キー）
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /生成＆インポート/ }));
    });

    const genBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/generate_and_import') : ((c[0] as URL).toString().endsWith('/api/article/generate_and_import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(genBodies.some((b) => b.model === 'gpt-5-mini' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('sends selected generation_category in /api/article/import payload', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    // カテゴリ選択→インポート
    const categorySelect = await screen.findByLabelText('カテゴリ');
    await act(async () => {
      await user.selectOptions(categorySelect, 'Dev');
    });
    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello cat');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const bodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(bodies.length).toBeGreaterThan(0);
    expect(bodies.some((b) => b.generation_category === 'Dev')).toBe(true);
  });

  it('sends reasoning params for gpt-5-nano on both import and generate_and_import', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-5-nano');
    });
    // 追加UIが表示される
    expect(screen.getByLabelText('reasoning.effort')).toBeInTheDocument();
    expect(screen.getByLabelText('text.verbosity')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello world nano');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const importBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(importBodies.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text_opts && !('temperature' in b))).toBe(true);

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /生成＆インポート/ }));
    });
    const genBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/generate_and_import') : ((c[0] as URL).toString().endsWith('/api/article/generate_and_import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(genBodies.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('disables import button and alerts when text length exceeds limit', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    const overLimitText = 'あ'.repeat(ARTICLE_IMPORT_TEXT_MAX_LENGTH + 1);
    await act(async () => {
      fireEvent.change(textarea, { target: { value: overLimitText } });
    });

    const importButton = screen.getByRole('button', { name: 'インポート' });
    expect(importButton).toBeDisabled();
    const warning = screen.getByText(
      `文章は${ARTICLE_IMPORT_TEXT_MAX_LENGTH}文字以内で入力してください（現在 ${overLimitText.length} 文字）`,
    );
    expect(warning).toHaveAttribute('role', 'alert');

    const importBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(importBodies).toHaveLength(0);
  });

  it('sends the selected category when generating and importing examples', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    const categorySelect = await screen.findByLabelText('カテゴリ');
    await act(async () => {
      await user.selectOptions(categorySelect, 'Dev');
    });
    expect((categorySelect as HTMLSelectElement).value).toBe('Dev');

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /生成＆インポート/ }));
    });

    const genBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/generate_and_import') : ((c[0] as URL).toString().endsWith('/api/article/generate_and_import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(genBodies.length).toBeGreaterThan(0);
    expect(genBodies.some((b) => b.category === 'Dev')).toBe(true);
  });

  it('uses selected model for regenerate from import result modal (reasoning model)', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-5-nano');
    });
    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello regenerate');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const regenBtn = await screen.findByRole('button', { name: '生成' });
    await act(async () => {
      await user.click(regenBtn);
    });

    const regenBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/packs/wp:regen:1/regenerate/async') : ((c[0] as URL).toString().endsWith('/api/word/packs/wp:regen:1/regenerate/async'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(regenBodies.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('uses selected model for regenerate from import result modal (sampling model)', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    await openTab(user, '文章インポート');

    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-4o-mini');
    });
    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello regenerate sampling');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const regenBtn = await screen.findByRole('button', { name: '生成' });
    await act(async () => {
      await user.click(regenBtn);
    });

    const regenBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/packs/wp:regen:1/regenerate/async') : ((c[0] as URL).toString().endsWith('/api/word/packs/wp:regen:1/regenerate/async'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(regenBodies.some((b) => b.model === 'gpt-4o-mini' && typeof b.temperature === 'number' && !('reasoning' in b) && !('text' in b))).toBe(true);
  });
});

