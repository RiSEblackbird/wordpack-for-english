import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';

describe('WordPackListPanel bulk delete', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).fetch = vi.fn();
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
    try {
      localStorage.removeItem('wordpack.auth.v1');
    } catch {}
  });

  function renderWithAuth() {
    return render(
      <AppProviders googleClientId="test-client">
        <App />
      </AppProviders>,
    );
  }

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

      if (url.startsWith('/api/word/packs?') && method === 'GET') {
        listCall += 1;
        if (listCall === 1) {
          return new Response(
            JSON.stringify({
              items: [
                {
                  id: 'wp:test:alpha',
                  lemma: 'alpha',
                  sense_title: 'Alpha overview',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                },
                {
                  id: 'wp:test:beta',
                  lemma: 'beta',
                  sense_title: 'Beta overview',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                },
                {
                  id: 'wp:test:gamma',
                  lemma: 'gamma',
                  sense_title: 'Gamma overview',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                },
              ],
              total: 3,
              limit: 200,
              offset: 0,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 'wp:test:gamma',
                lemma: 'gamma',
                sense_title: 'Gamma overview',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ],
            total: 1,
            limit: 200,
            offset: 0,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/packs/wp:test:') && method === 'DELETE') {
        return new Response(
          JSON.stringify({ message: 'deleted' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('allows selecting multiple WordPacks and deleting them together', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());

    const alphaCheckbox = await screen.findByRole('checkbox', { name: 'WordPack alpha を選択' });
    const betaCheckbox = await screen.findByRole('checkbox', { name: 'WordPack beta を選択' });
    expect(alphaCheckbox).not.toBeChecked();
    expect(betaCheckbox).not.toBeChecked();

    await act(async () => {
      await user.click(alphaCheckbox);
      await user.click(betaCheckbox);
    });

    expect(alphaCheckbox).toBeChecked();
    expect(betaCheckbox).toBeChecked();

    const bulkDeleteButton = await screen.findByRole('button', { name: '選択したWordPackを削除' });
    expect(bulkDeleteButton).not.toBeDisabled();

    await act(async () => {
      await user.click(bulkDeleteButton);
    });

    const confirmYes = await screen.findByRole('button', { name: 'はい' });
    await act(async () => {
      await user.click(confirmYes);
    });

    await waitFor(() => expect(screen.getByText('WordPackを2件削除しました')).toBeInTheDocument());

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/word/packs/wp:test:alpha',
      expect.objectContaining({ method: 'DELETE' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/word/packs/wp:test:beta',
      expect.objectContaining({ method: 'DELETE' }),
    );

    await waitFor(() => {
      expect(screen.queryByText('alpha')).not.toBeInTheDocument();
      expect(screen.queryByText('beta')).not.toBeInTheDocument();
      expect(screen.getByText('gamma')).toBeInTheDocument();
    });
  });
});

