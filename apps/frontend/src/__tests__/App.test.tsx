import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from '../App';
import { AppProviders } from '../main';

const renderWithProviders = () =>
  render(
    <AppProviders googleClientId="test-client">
      <App />
    </AppProviders>,
  );

// ゲスト導線のみに絞ったテストなので /api/config と認証関連エンドポイントを最小レスポンスで固定する。
const setupConfigFetch = () => {
  const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.endsWith('/api/config')) {
      return Promise.resolve(
        new Response(JSON.stringify({ request_timeout_ms: 60000, llm_model: 'gpt-5-mini' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (url.endsWith('/api/auth/logout')) {
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    if (url.endsWith('/api/auth/guest')) {
      return Promise.resolve(
        new Response(JSON.stringify({ mode: 'guest' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    return Promise.resolve(
      new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
  });
  (globalThis as any).fetch = fetchMock;
  return fetchMock;
};

describe('App guest mode entry', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupConfigFetch();
  });

  it('shows the guest button and transitions into guest mode', async () => {
    renderWithProviders();

    const user = userEvent.setup();
    const guestButton = await screen.findByRole('button', { name: 'ゲスト閲覧モード' });

    await act(async () => {
      await user.click(guestButton);
    });

    expect(await screen.findByRole('heading', { name: 'WordPack' })).toBeInTheDocument();
    expect(screen.getByText('ゲスト閲覧モード')).toBeInTheDocument();
  });
});
