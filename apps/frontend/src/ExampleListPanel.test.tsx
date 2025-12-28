import { render, screen, act, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';

describe('ExampleListPanel pagination offset behavior', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).fetch = vi.fn();
    // sessionStorage を汚染しないようにクリア
    try { sessionStorage.clear(); } catch {}
    try {
      localStorage.setItem(
        'wordpack.auth.v1',
        JSON.stringify({
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

  function setupFetchMocks() {
    const mock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: any) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      if (url.endsWith('/api/config') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/examples?')) {
        const u = new URL(url, 'http://localhost');
        const limit = Number(u.searchParams.get('limit')) || 200;
        const offset = Number(u.searchParams.get('offset')) || 0;
        // ダミーデータ: total=450件とし、idは offset..offset+limit-1
        const total = 450;
        const items = Array.from({ length: Math.max(0, Math.min(limit, Math.max(0, total - offset))) }).map((_, i) => {
          const id = offset + i + 1; // 1-based id for readability
          return {
            id,
            word_pack_id: `wp:test:${Math.ceil(id / 5)}`,
            lemma: `lemma${id}`,
            category: (['Dev','CS','LLM','Business','Common'] as const)[id % 5],
            en: `example en ${id}`,
            ja: `例文 ja ${id}`,
            grammar_ja: null,
            created_at: new Date().toISOString(),
            word_pack_updated_at: null,
            transcription_typing_count: 0,
          };
        });
        return new Response(
          JSON.stringify({ items, total, limit, offset }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('uses requested offset for Next/Prev and shows correct range', async () => {
    setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();

    // 例文一覧タブへ（設定ロード完了を待ってボタンが出てからクリック）
    await openTab(user, '例文一覧');

    // 初期ロードのレンジ表記とボタン状態（見出しをheadingロールで特定）
    await screen.findByRole('heading', { name: '例文一覧' });
    const ttsButtons = await screen.findAllByRole('button', { name: '音声' });
    expect(ttsButtons.length).toBeGreaterThan(0);
    // limit=200, total=450, offset=0 => 1-200 / 450件
    const range1 = await screen.findByText(/1-200 \/ 450件/);
    expect(range1).toBeInTheDocument();
    const prevBtn = screen.getByRole('button', { name: '前へ' }) as HTMLButtonElement;
    const nextBtn = screen.getByRole('button', { name: '次へ' }) as HTMLButtonElement;
    expect(prevBtn).toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    // 次へ: offset=200 を使用
    await act(async () => {
      await user.click(nextBtn);
    });
    const range2 = await screen.findByText(/201-400 \/ 450件/);
    expect(range2).toBeInTheDocument();
    expect(prevBtn).not.toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    // 次へ（2回目）: offset=400 を使用し、400-450
    await act(async () => {
      await user.click(nextBtn);
    });
    const range3 = await screen.findByText(/401-450 \/ 450件/);
    expect(range3).toBeInTheDocument();
    // 最終ページでは次へが無効
    expect(nextBtn).toBeDisabled();

    // 前へ: offset=200 に戻る
    await act(async () => {
      await user.click(prevBtn);
    });
    const range4 = await screen.findByText(/201-400 \/ 450件/);
    expect(range4).toBeInTheDocument();
  }, 15000);

  it('訳一括表示トグルで全訳文の開閉を一括操作できる', async () => {
    setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();

    await openTab(user, '例文一覧');

    await screen.findByRole('heading', { name: '例文一覧' });

    // 初期状態では訳文が非表示
    expect(screen.queryByText('例文 ja 1')).toBeNull();

    const toggle = screen.getByLabelText('訳一括表示') as HTMLInputElement;
    expect(toggle).not.toBeChecked();

    await act(async () => {
      await user.click(toggle);
    });

    await waitFor(() => {
      expect(screen.getByText('例文 ja 1')).toBeInTheDocument();
    });

    const cards = await screen.findAllByTestId('example-card');
    expect(cards.length).toBeGreaterThan(0);
    const firstTranslationButton = within(cards[0]).getByRole('button', { name: '訳表示' }) as HTMLButtonElement;
    expect(firstTranslationButton).toBeDisabled();

    await act(async () => {
      await user.click(toggle);
    });

    await waitFor(() => {
      expect(screen.queryByText('例文 ja 1')).toBeNull();
    });

    expect(firstTranslationButton).not.toBeDisabled();
  }, 15000);

  it('文字起こしタイピングの記録が一覧の回数表示へ即座に反映される', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      const method = init?.method ?? 'GET';

      if (url.endsWith('/api/config') && method === 'GET') {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/packs') && method === 'GET') {
        return new Response(
          JSON.stringify({ items: [], total: 0, limit: 200, offset: 0 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/examples?') && method === 'GET') {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 1,
                word_pack_id: 'wp:test:1',
                lemma: 'lemma1',
                category: 'Dev',
                en: 'example en 1',
                ja: '例文 ja 1',
                grammar_ja: null,
                created_at: new Date().toISOString(),
                word_pack_updated_at: null,
                transcription_typing_count: 0,
              },
            ],
            total: 1,
            limit: 200,
            offset: 0,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.endsWith('/api/word/examples/1/transcription-typing') && method === 'POST') {
        const body = init?.body ? JSON.parse(init.body as string) : {};
        expect(body).toEqual({ input_length: 'example en 1'.length });
        return new Response(
          JSON.stringify({ id: 1, word_pack_id: 'wp:test:1', transcription_typing_count: 3 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      return new Response('not found', { status: 404 });
    });

    renderWithAuth();

    const user = userEvent.setup();

    await openTab(user, '例文一覧');
    await screen.findByRole('heading', { name: '例文一覧' });

    const typingBadge = await screen.findByText('タイピング累計: 0文字');
    expect(typingBadge).toBeInTheDocument();

    const card = await screen.findByTestId('example-card');
    await act(async () => {
      await user.click(card);
    });

    const toggleTypingButton = await screen.findByRole('button', { name: '文字起こしタイピング (0文字)' });
    await act(async () => {
      await user.click(toggleTypingButton);
    });

    const textarea = await screen.findByLabelText('文字起こしタイピング入力');
    await act(async () => {
      await user.type(textarea, 'example en 1');
    });

    const recordButton = await screen.findByRole('button', { name: 'タイピング記録' });
    await act(async () => {
      await user.click(recordButton);
    });

    await waitFor(() => {
      expect(screen.getByText('タイピング累計: 3文字')).toBeInTheDocument();
    });

    await screen.findByRole('button', { name: '文字起こしタイピング (3文字)' });

    fetchMock.mockRestore();
  }, 20000);

  it('選択した例文をまとめて削除できる', async () => {
    const itemsFirstPage = [
      {
        id: 1,
        word_pack_id: 'wp:test:1',
        lemma: 'alpha',
        category: 'Dev' as const,
        en: 'example en 1',
        ja: '例文 ja 1',
        grammar_ja: null,
        created_at: new Date().toISOString(),
        word_pack_updated_at: null,
        transcription_typing_count: 0,
      },
      {
        id: 2,
        word_pack_id: 'wp:test:2',
        lemma: 'beta',
        category: 'CS' as const,
        en: 'example en 2',
        ja: '例文 ja 2',
        grammar_ja: null,
        created_at: new Date().toISOString(),
        word_pack_updated_at: null,
        transcription_typing_count: 0,
      },
      {
        id: 3,
        word_pack_id: 'wp:test:3',
        lemma: 'gamma',
        category: 'LLM' as const,
        en: 'example en 3',
        ja: '例文 ja 3',
        grammar_ja: null,
        created_at: new Date().toISOString(),
        word_pack_updated_at: null,
        transcription_typing_count: 0,
      },
    ];

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      const method = init?.method ?? 'GET';

      if (url.endsWith('/api/config') && method === 'GET') {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/packs') && method === 'GET') {
        return new Response(
          JSON.stringify({ items: [], total: 0, limit: 200, offset: 0 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/examples?') && method === 'GET') {
        const remainingIds = (fetchMock as any)._deleted ? [3] : [1, 2, 3];
        const items = itemsFirstPage.filter((it) => remainingIds.includes(it.id));
        return new Response(
          JSON.stringify({ items, total: items.length, limit: 200, offset: 0 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.endsWith('/api/word/examples/bulk-delete') && method === 'POST') {
        const body = init?.body ? JSON.parse(init.body as string) : { ids: [] };
        expect(body.ids).toEqual([1, 2]);
        (fetchMock as any)._deleted = true;
        return new Response(
          JSON.stringify({ deleted: 2, not_found: [] }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      return new Response('not found', { status: 404 });
    });

    renderWithAuth();
    const user = userEvent.setup();

    await openTab(user, '例文一覧');

    await screen.findByRole('heading', { name: '例文一覧' });
    await screen.findByText('example en 1');

    const checkbox1 = await screen.findByRole('checkbox', { name: '例文 example en 1 を選択' });
    const checkbox2 = await screen.findByRole('checkbox', { name: '例文 example en 2 を選択' });
    expect(checkbox1).not.toBeChecked();
    expect(checkbox2).not.toBeChecked();

    await act(async () => {
      await user.click(checkbox1);
      await user.click(checkbox2);
    });

    const bulkButton = await screen.findByRole('button', { name: '選択した例文を削除' });
    expect(bulkButton).not.toBeDisabled();

    await act(async () => {
      await user.click(bulkButton);
    });

    const confirmYes = await screen.findByRole('button', { name: 'はい' });
    await act(async () => {
      await user.click(confirmYes);
    });

    await screen.findByText('例文を2件削除しました', undefined, { timeout: 5000 });

    await waitFor(() => {
      expect(screen.queryByText('example en 1')).not.toBeInTheDocument();
      expect(screen.queryByText('example en 2')).not.toBeInTheDocument();
      expect(screen.getByText('example en 3')).toBeInTheDocument();
    });
  }, 15000);
});


