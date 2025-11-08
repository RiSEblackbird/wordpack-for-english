import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AuthProvider } from './AuthContext';
import { AUTO_RETRY_INTERVAL_MS } from './SettingsContext';

vi.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useGoogleLogin: (options: { onSuccess?: (res: { id_token?: string }) => void; onError?: () => void }) => {
    return () => {
      options?.onSuccess?.({ id_token: 'test-id-token' });
    };
  },
}));

const resolveUrl = (input: RequestInfo | URL): string => {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  if (input instanceof Request) return input.url;
  return String(input);
};

const configSuccess = () =>
  new Response(
    JSON.stringify({ request_timeout_ms: 60000, llm_model: 'gpt-5-mini' }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );

const authSuccess = () =>
  new Response(
    JSON.stringify({
      user: { google_sub: 'sub-123', email: 'user@example.com', display_name: 'Example User' },
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );

const logoutSuccess = () => new Response(null, { status: 204 });

const renderWithProviders = () =>
  render(
    <AuthProvider clientId="test-client">
      <App />
    </AuthProvider>,
  );

const setupFetchForAuthenticatedFlow = (fetchMock: vi.MockedFunction<typeof fetch>) => {
  fetchMock.mockImplementation((input, init) => {
    const url = resolveUrl(input);
    if (url.endsWith('/api/config')) {
      return Promise.resolve(configSuccess());
    }
    if (url.endsWith('/api/auth/google')) {
      return Promise.resolve(authSuccess());
    }
    if (url.endsWith('/api/auth/logout')) {
      return Promise.resolve(logoutSuccess());
    }
    return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
  });
};

const completeLogin = async (
  fetchMock: vi.MockedFunction<typeof fetch>,
  user: ReturnType<typeof userEvent.setup>,
) => {
  if (!fetchMock.mock.calls.length) {
    setupFetchForAuthenticatedFlow(fetchMock);
  }
  const loginButton = await screen.findByRole('button', { name: 'Googleでログイン' });
  await act(async () => {
    await user.click(loginButton);
  });
  await screen.findByPlaceholderText('見出し語を入力');
};

let fetchMock: vi.MockedFunction<typeof fetch>;

beforeEach(() => {
  vi.clearAllMocks();
  fetchMock = vi.fn() as vi.MockedFunction<typeof fetch>;
  (globalThis as any).fetch = fetchMock;
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
});

describe('App navigation', () => {
  it('shows login card when user has not authenticated yet', async () => {
    fetchMock.mockImplementation((input) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        return Promise.resolve(configSuccess());
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    renderWithProviders();

    expect(await screen.findByRole('heading', { name: 'WordPack にサインイン' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Googleでログイン' })).toBeInTheDocument();
  });

  it('shows the login screen when /api/config responds with 401', async () => {
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout');
    fetchMock.mockImplementation((input) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        return Promise.resolve(new Response('', { status: 401 }));
      }
      if (url.endsWith('/api/auth/logout')) {
        return Promise.resolve(logoutSuccess());
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    try {
      renderWithProviders();

      expect(await screen.findByRole('heading', { name: 'WordPack にサインイン' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Googleでログイン' })).toBeInTheDocument();
      // 401 ではログイン画面を即時に表示し、エラー用の自動リトライタイマーを開始しない。
      expect(
        setTimeoutSpy.mock.calls.some(([, timeout]) => timeout === AUTO_RETRY_INTERVAL_MS),
      ).toBe(false);
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('transitions to the main interface after a successful login', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    expect(await screen.findByRole('heading', { name: 'WordPack' })).toBeInTheDocument();
  });

  it('shows retry option when /api/config fetch fails', async () => {
    let attempts = 0;
    fetchMock.mockImplementation((input) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        if (attempts === 0) {
          attempts += 1;
          return Promise.reject(new Error('connection refused'));
        }
        return Promise.resolve(configSuccess());
      }
      if (url.endsWith('/api/auth/google')) {
        return Promise.resolve(authSuccess());
      }
      if (url.endsWith('/api/auth/logout')) {
        return Promise.resolve(logoutSuccess());
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    renderWithProviders();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/\/api\/config.*設定を取得できませんでした/);

    const retryButton = screen.getByRole('button', { name: '再試行' });
    const user = userEvent.setup();
    await act(async () => {
      await user.click(retryButton);
    });

    await completeLogin(fetchMock, user);
    expect(await screen.findByPlaceholderText('見出し語を入力')).toBeInTheDocument();
  });

  it('automatically retries syncing settings when the backend becomes available', async () => {
    let attempts = 0;
    fetchMock.mockImplementation((input) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        if (attempts === 0) {
          attempts += 1;
          return Promise.reject(new Error('connection refused'));
        }
        return Promise.resolve(
          new Response(
            JSON.stringify({ request_timeout_ms: 120000, llm_model: 'gpt-auto' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (url.endsWith('/api/auth/google')) {
        return Promise.resolve(authSuccess());
      }
      if (url.endsWith('/api/auth/logout')) {
        return Promise.resolve(logoutSuccess());
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    let triggerAutoRetry: (() => void) | null = null;
    const originalSetTimeout = window.setTimeout;
    const setTimeoutSpy = vi
      .spyOn(window, 'setTimeout')
      .mockImplementation(((handler: TimerHandler, timeout?: number, ...args: any[]) => {
        if (typeof timeout === 'number' && timeout >= AUTO_RETRY_INTERVAL_MS && typeof handler === 'function') {
          triggerAutoRetry = () => {
            (handler as (...cbArgs: any[]) => void)(...args);
          };
          return 0 as unknown as ReturnType<typeof window.setTimeout>;
        }
        return originalSetTimeout(handler as any, timeout as any, ...(args as any));
      }) as typeof window.setTimeout);

    try {
      renderWithProviders();

      const alert = await screen.findByRole('alert');
      await waitFor(() => {
        expect(alert).toHaveTextContent('自動再試行');
      });

      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(typeof triggerAutoRetry).toBe('function');

      await act(async () => {
        triggerAutoRetry?.();
      });

      await waitFor(() => {
        const configCalls = fetchMock.mock.calls.filter(([input]) => resolveUrl(input).endsWith('/api/config'));
        expect(configCalls.length).toBeGreaterThanOrEqual(2);
      });

      const user = userEvent.setup();
      await completeLogin(fetchMock, user);
      expect(await screen.findByPlaceholderText('見出し語を入力')).toBeInTheDocument();
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('renders WordPack by default and navigates with keyboard', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    expect(await screen.findByPlaceholderText('見出し語を入力')).toBeInTheDocument();

    await act(async () => {
      await user.keyboard('{Alt>}{2}{/Alt}');
    });
    expect(await screen.findByLabelText('発音を有効化')).toBeInTheDocument();
    expect(await screen.findByLabelText('temperature')).toBeInTheDocument();
  });

  it('opens the sidebar with the hamburger button and keeps it visible after selecting a tab', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const sidebar = screen.getByLabelText('アプリ内共通メニュー');
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');

    const computed = window.getComputedStyle(sidebar);
    expect(computed.display).toBe('block');
    expect(sidebar.getAttribute('style')).toContain('280px');

    const examplesButton = await screen.findByRole('button', { name: '例文一覧' });
    await act(async () => {
      await user.click(examplesButton);
    });

    expect(await screen.findByRole('heading', { name: '例文一覧' })).toBeInTheDocument();
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');

    const appShell = document.querySelector('.app-shell');
    const mainInner = document.querySelector('.main-inner');
    if (!appShell || !mainInner) {
      throw new Error('layout elements not found');
    }
    expect(appShell).toHaveClass('sidebar-open');

    const sidebarRect = sidebar.getBoundingClientRect();
    const mainRect = mainInner.getBoundingClientRect();
    expect(Math.round(sidebarRect.left)).toBe(0);
    expect(mainRect.left).toBeGreaterThanOrEqual(sidebarRect.right);
  });

  it('places the hamburger button on the viewport left edge', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    const rect = toggle.getBoundingClientRect();
    expect(Math.round(rect.left)).toBe(0);
    expect(Math.round(rect.top)).toBe(0);
  });

  it('renders the main content without a shift animation', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    await screen.findByRole('heading', { name: 'WordPack' });

    const mainInner = document.querySelector('.main-inner');
    if (!mainInner) {
      throw new Error('main content wrapper not found');
    }

    const styles = window.getComputedStyle(mainInner);
    expect(styles.transitionDuration === '0s' || styles.transitionDuration === '').toBe(true);
    expect(styles.transitionProperty === 'all' || styles.transitionProperty === '').toBe(true);
  });

  it('does not rely on deferred timers to stabilize the layout', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    await screen.findByRole('heading', { name: 'WordPack' });

    const appShell = document.querySelector('.app-shell') as HTMLElement | null;
    if (!appShell) {
      throw new Error('app shell not found');
    }

    expect(appShell.style.getPropertyValue('--main-shift')).toBe('');

    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });

    await act(async () => {
      await user.click(toggle);
    });

    expect(appShell.style.getPropertyValue('--main-shift')).toBe('');

    const mainInner = document.querySelector('.main-inner') as HTMLElement | null;
    if (!mainInner) {
      throw new Error('main content wrapper not found');
    }

    const computed = window.getComputedStyle(mainInner);
    expect(mainInner.style.left).toBe('');
    expect(computed.position === 'static' || computed.position === '').toBe(true);
  });

  it('aligns sidebar content to the top (no space-between stretching)', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const sidebarContent = document.querySelector('.sidebar-content');
    if (!sidebarContent) throw new Error('sidebar content not found');

    const computed = window.getComputedStyle(sidebarContent);
    expect(computed.alignContent === 'flex-start' || computed.alignContent === '').toBe(true);
  });

  it('returns to the login screen when signing out', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    const openMenu = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openMenu);
    });

    const settingsTab = await screen.findByRole('button', { name: '設定' });
    await act(async () => {
      await user.click(settingsTab);
    });

    const logoutButton = await screen.findByRole('button', { name: 'ログアウト（Google セッションを終了）' });
    await act(async () => {
      await user.click(logoutButton);
    });

    expect(await screen.findByRole('heading', { name: 'WordPack にサインイン' })).toBeInTheDocument();
  });
});
