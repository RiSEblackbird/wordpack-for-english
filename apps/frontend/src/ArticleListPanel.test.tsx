import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { App } from './App';
import { vi } from 'vitest';

describe('ArticleListPanel bulk delete', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    try { sessionStorage.clear(); } catch {}
  });

  function setupFetchMocks() {
    let listCall = 0;
    const mock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      const method = init?.method ?? 'GET';

      if (url.endsWith('/api/config') && method === 'GET') {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/article?') && method === 'GET') {
        listCall += 1;
        const baseItems = [
          {
            id: 'article-1',
            title_en: 'First article',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: 'article-2',
            title_en: 'Second article',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: 'article-3',
            title_en: 'Third article',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ];
        const items = listCall === 1 ? baseItems : baseItems.slice(2);
        return new Response(
          JSON.stringify({ items, total: items.length, limit: 20, offset: 0 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/article/') && method === 'DELETE') {
        return new Response(
          JSON.stringify({ message: 'deleted' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('allows selecting multiple articles and deleting them together', async () => {
    setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();

    const articleTabBtn = await screen.findByRole('button', { name: '文章インポート' });
    await act(async () => {
      await user.click(articleTabBtn);
    });

    await waitFor(() => expect(screen.getByText('インポート済み文章')).toBeInTheDocument());

    const checkbox1 = await screen.findByRole('checkbox', { name: '文章 First article を選択' });
    const checkbox2 = await screen.findByRole('checkbox', { name: '文章 Second article を選択' });

    await act(async () => {
      await user.click(checkbox1);
      await user.click(checkbox2);
    });

    const bulkButton = await screen.findByRole('button', { name: '選択した文章を削除' });
    expect(bulkButton).not.toBeDisabled();

    await act(async () => {
      await user.click(bulkButton);
    });

    const confirmYes = await screen.findByRole('button', { name: 'はい' });
    await act(async () => {
      await user.click(confirmYes);
    });

    await waitFor(() => expect(screen.getByText('文章を2件削除しました')).toBeInTheDocument());

    await waitFor(() => {
      expect(screen.queryByText('First article')).not.toBeInTheDocument();
      expect(screen.queryByText('Second article')).not.toBeInTheDocument();
      expect(screen.getByText('Third article')).toBeInTheDocument();
    });
  });
});

