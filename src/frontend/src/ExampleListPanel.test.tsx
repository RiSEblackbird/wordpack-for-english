import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { App } from './App';
import { vi } from 'vitest';

describe('ExampleListPanel pagination offset behavior', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // sessionStorage を汚染しないようにクリア
    try { sessionStorage.clear(); } catch {}
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
    render(<App />);

    const user = userEvent.setup();

    // 例文一覧タブへ（設定ロード完了を待ってボタンが出てからクリック）
    const examplesTabBtn = await screen.findByRole('button', { name: '例文一覧' });
    await act(async () => {
      await user.click(examplesTabBtn);
    });

    // 初期ロードのレンジ表記とボタン状態
    await waitFor(() => expect(screen.getByText(/例文一覧/)).toBeInTheDocument());
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
});


