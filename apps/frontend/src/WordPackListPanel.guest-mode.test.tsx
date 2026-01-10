import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';
import { guestLockMessage } from './components/GuestLock';

const renderWithGuestSession = () =>
  render(
    <AppProviders googleClientId="test-client">
      <App />
    </AppProviders>,
  );

// ゲストのUI制御を観察するため、最小の WordPack レスポンスを固定化する。
const setupGuestWordPackFetch = () => {
  (globalThis as any).fetch = vi.fn();
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : (input as URL).toString();
    const method = init?.method ?? 'GET';

    if (url.endsWith('/api/config') && method === 'GET') {
      return new Response(
        JSON.stringify({ request_timeout_ms: 60000, llm_model: 'gpt-5-mini' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    if (url.startsWith('/api/word/packs?') && method === 'GET') {
      return new Response(
        JSON.stringify({
          items: [
            {
              id: 'wp:guest:alpha',
              lemma: 'alpha',
              sense_title: 'Alpha overview',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              is_empty: true,
              checked_only_count: 0,
              learned_count: 0,
            },
          ],
          total: 1,
          limit: 200,
          offset: 0,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
  });

  return fetchMock;
};

describe('WordPackListPanel guest controls', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupGuestWordPackFetch();
    try {
      localStorage.setItem('wordpack.auth.v1', JSON.stringify({ authMode: 'guest' }));
    } catch {
      // localStorage が利用できない環境でもテストを継続する。
    }
  });

  afterEach(() => {
    try {
      localStorage.removeItem('wordpack.auth.v1');
    } catch {
      // ignore
    }
  });

  it('disables write actions and shows the guest tooltip on hover', async () => {
    renderWithGuestSession();

    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());

    vi.useFakeTimers();

    const bulkDeleteButton = screen.getByRole('button', { name: '選択したWordPackを削除' });
    const generateButton = screen.getByRole('button', { name: '生成' });
    const deleteButtons = screen.getAllByRole('button', { name: '削除' });

    expect(bulkDeleteButton).toBeDisabled();
    expect(generateButton).toBeDisabled();
    expect(deleteButtons[0]).toBeDisabled();

    const wrapper = bulkDeleteButton.parentElement as HTMLElement;
    act(() => {
      fireEvent.mouseEnter(wrapper);
    });
    expect(screen.queryByText(guestLockMessage)).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(screen.getByText(guestLockMessage)).toBeInTheDocument();

    act(() => {
      fireEvent.mouseLeave(wrapper);
    });
    expect(screen.queryByText(guestLockMessage)).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
