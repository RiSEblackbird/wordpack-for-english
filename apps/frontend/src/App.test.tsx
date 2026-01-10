import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import type { MockedFunction } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';
import { AUTO_RETRY_INTERVAL_MS } from './SettingsContext';
import type { FC, ReactNode } from 'react';

interface MockCredentialResponse {
  credential?: string | null;
  clientId?: string | null;
  select_by?: string | null;
}

type GoogleLoginHandlerSet = {
  onSuccess?: (response?: MockCredentialResponse) => void;
  onError?: () => void;
};

type GoogleLoginClickImplementation = (handlers: GoogleLoginHandlerSet) => void;

const {
  googleLoginController,
  GoogleLoginMock,
} = vi.hoisted(() => {
  const defaultGoogleLogin: GoogleLoginClickImplementation = ({ onSuccess }) => {
    onSuccess?.({ credential: 'mock-id-token', clientId: 'test-client', select_by: 'user' });
  };

  const controller = {
    impl: defaultGoogleLogin as GoogleLoginClickImplementation,
    setImplementation(next: GoogleLoginClickImplementation) {
      this.impl = next;
    },
    reset() {
      this.impl = defaultGoogleLogin;
    },
  };

  const GoogleLoginMock: FC<{
    onSuccess?: (response?: MockCredentialResponse) => void;
    onError?: () => void;
  }> = ({ onSuccess, onError }) => (
    <button
      type="button"
      onClick={() => controller.impl({ onSuccess, onError })}
    >
      Googleでログイン
    </button>
  );

  return {
    googleLoginController: controller,
    GoogleLoginMock,
  };
});

vi.mock('@react-oauth/google', () => {
  const GoogleOAuthProvider = ({ children }: { children: ReactNode }) => <>{children}</>;
  return { GoogleOAuthProvider, GoogleLogin: GoogleLoginMock };
});

type FetchMock = MockedFunction<typeof fetch>;
type FetchCall = Parameters<FetchMock>;

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

const renderWithProviders = (clientId = 'test-client') =>
  render(
    <AppProviders googleClientId={clientId}>
      <App />
    </AppProviders>,
  );

const setupFetchForAuthenticatedFlow = (fetchMock: FetchMock) => {
  fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
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
  fetchMock: FetchMock,
  user: ReturnType<typeof userEvent.setup>,
) => {
  if (!fetchMock.mock.calls.length) {
    setupFetchForAuthenticatedFlow(fetchMock);
  }
  const loginButton = await screen.findByRole('button', { name: /Google.?でログイン/ });
  await act(async () => {
    await user.click(loginButton);
  });
  await screen.findByPlaceholderText('見出し語を入力（英数字・ハイフン・アポストロフィ・半角スペースのみ）');
};

let fetchMock: FetchMock;

beforeEach(() => {
  vi.clearAllMocks();
  fetchMock = vi.fn() as FetchMock;
  (globalThis as any).fetch = fetchMock;
  googleLoginController.reset();
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
});

describe('App navigation', () => {
  it('shows login card when user has not authenticated yet', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        return Promise.resolve(configSuccess());
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    renderWithProviders();

    expect(await screen.findByRole('heading', { name: 'WordPack にサインイン' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Google.?でログイン/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ゲスト閲覧モード' })).toBeInTheDocument();
  });

  it('renders configuration guidance when the Google client ID is missing', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        return Promise.resolve(configSuccess());
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    renderWithProviders('');

    expect(
      await screen.findByRole('heading', { name: 'Google ログインの設定が必要です' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/VITE_GOOGLE_CLIENT_ID が未設定のため Google のサインインを開始できません/),
    ).toBeInTheDocument();
    expect(
      screen.getByText('開発用の認証バイパスが無効な環境では、上記手順を完了するまでアプリへサインインできません。環境変数を設定後に再度アクセスしてください。'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ゲスト閲覧モード' })).toBeInTheDocument();
  });

  it('shows the login screen when /api/config responds with 401', async () => {
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout');
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
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
      expect(screen.getByRole('button', { name: /Google.?でログイン/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'ゲスト閲覧モード' })).toBeInTheDocument();
      // 401 ではログイン画面を即時に表示し、エラー用の自動リトライタイマーを開始しない。
      expect(
        setTimeoutSpy.mock.calls.some(([, timeout]) => timeout === AUTO_RETRY_INTERVAL_MS),
      ).toBe(false);
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('enters guest mode from the login screen', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        return Promise.resolve(configSuccess());
      }
      if (url.endsWith('/api/auth/logout')) {
        return Promise.resolve(logoutSuccess());
      }
      if (url.endsWith('/api/auth/guest')) {
        return Promise.resolve(
          new Response(JSON.stringify({ mode: 'guest' }), { status: 200, headers: { 'Content-Type': 'application/json' } })
        );
      }
      return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });

    renderWithProviders();

    const user = userEvent.setup();
    const guestButton = await screen.findByRole('button', { name: 'ゲスト閲覧モード' });
    await act(async () => {
      await user.click(guestButton);
    });

    expect(await screen.findByRole('heading', { name: 'WordPack' })).toBeInTheDocument();
    expect(screen.getByText('ゲスト閲覧モード')).toBeInTheDocument();
  });

  it('transitions to the main interface after a successful login', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    expect(await screen.findByRole('heading', { name: 'WordPack' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ログアウト' })).toBeInTheDocument();
    const authCall = (fetchMock.mock.calls as FetchCall[]).find(([input]) =>
      resolveUrl(input).endsWith('/api/auth/google'),
    );
    expect(authCall).toBeDefined();
    const [, init] = authCall!;
    expect(init?.method).toBe('POST');
    expect(init?.credentials).toBe('include');
    expect(init?.headers).toMatchObject({ 'Content-Type': 'application/json' });
    expect(init?.body).toBe(JSON.stringify({ id_token: 'mock-id-token' }));
  });

  it('shows an inline error when Google returns a token response without an ID token', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    googleLoginController.setImplementation(({ onSuccess }) => {
      onSuccess?.({ credential: undefined, clientId: 'test-client', select_by: 'user' });
    });

    const user = userEvent.setup();
    const loginButton = await screen.findByRole('button', { name: /Google.?でログイン/ });
    await act(async () => {
      await user.click(loginButton);
    });

    expect(
      await screen.findByText('ID トークンを取得できませんでした。ブラウザを更新して再試行してください。'),
    ).toBeInTheDocument();
    expect(
      (fetchMock.mock.calls as FetchCall[]).some(([input]) =>
        resolveUrl(input).endsWith('/api/auth/google'),
      ),
    ).toBe(false);
  });

  it('reports telemetry when Google login succeeds without an ID token', async () => {
    const telemetryCalls: Array<{ url: string; init?: RequestInit }> = [];
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = resolveUrl(input);
      if (url.endsWith('/api/config')) {
        return Promise.resolve(configSuccess());
      }
      if (url.endsWith('/api/diagnostics/oauth-telemetry')) {
        telemetryCalls.push({ url, init });
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      return Promise.resolve(
        new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    });

    renderWithProviders();

    googleLoginController.setImplementation(({ onSuccess }) => {
      onSuccess?.({ credential: undefined, clientId: 'test-client', select_by: 'user' });
    });

    const user = userEvent.setup();
    const loginButton = await screen.findByRole('button', { name: /Google.?でログイン/ });
    await act(async () => {
      await user.click(loginButton);
    });

    await waitFor(() => {
      expect(telemetryCalls).toHaveLength(1);
    });

    const { init } = telemetryCalls[0];
    expect(init?.method).toBe('POST');
    expect(init?.headers).toMatchObject({ 'Content-Type': 'application/json' });
    const body = JSON.parse((init?.body as string) ?? '{}');
    expect(body).toMatchObject({
      event: 'google_login_missing_id_token',
      googleClientId: 'test-client',
      errorCategory: 'missing_id_token',
    });
    expect(body.tokenResponse).toMatchObject({ clientId: 'test-client', select_by: 'user' });
    expect(body.tokenResponse).not.toHaveProperty('credential');

    expect(
      await screen.findByText('ID トークンを取得できませんでした。ブラウザを更新して再試行してください。'),
    ).toBeInTheDocument();
  });

  it('surfaces the default error message when Google signals a failure', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    googleLoginController.setImplementation(({ onError }) => {
      onError?.();
    });
    renderWithProviders();

    const user = userEvent.setup();
    const loginButton = await screen.findByRole('button', { name: /Google.?でログイン/ });
    await act(async () => {
      await user.click(loginButton);
    });

    expect(
      await screen.findByText('Google サインインでエラーが発生しました。時間を置いて再試行してください。'),
    ).toBeInTheDocument();
    expect(
      (fetchMock.mock.calls as FetchCall[]).some(([input]) =>
        resolveUrl(input).endsWith('/api/auth/google'),
      ),
    ).toBe(false);
  });

  it('shows retry option when /api/config fetch fails', async () => {
    let attempts = 0;
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
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
    expect(await screen.findByPlaceholderText('見出し語を入力（英数字・ハイフン・アポストロフィ・半角スペースのみ）')).toBeInTheDocument();
  });

  it('automatically retries syncing settings when the backend becomes available', async () => {
    let attempts = 0;
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
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
        const configCalls = (fetchMock.mock.calls as FetchCall[]).filter(([input]) =>
          resolveUrl(input).endsWith('/api/config'),
        );
        expect(configCalls.length).toBeGreaterThanOrEqual(2);
      });

      const user = userEvent.setup();
      await completeLogin(fetchMock, user);
      expect(await screen.findByPlaceholderText('見出し語を入力（英数字・ハイフン・アポストロフィ・半角スペースのみ）')).toBeInTheDocument();
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('renders WordPack by default and navigates with keyboard', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    expect(await screen.findByPlaceholderText('見出し語を入力（英数字・ハイフン・アポストロフィ・半角スペースのみ）')).toBeInTheDocument();

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

  it('returns to the login screen when signing out via the header control', async () => {
    setupFetchForAuthenticatedFlow(fetchMock);
    renderWithProviders();

    const user = userEvent.setup();
    await completeLogin(fetchMock, user);

    const logoutButton = await screen.findByRole('button', { name: 'ログアウト' });
    await act(async () => {
      await user.click(logoutButton);
    });

    expect(await screen.findByRole('heading', { name: 'WordPack にサインイン' })).toBeInTheDocument();
    const logoutCalls = (fetchMock.mock.calls as FetchCall[]).filter(([input]) =>
      resolveUrl(input).endsWith('/api/auth/logout'),
    );
    expect(logoutCalls).toHaveLength(1);
  });
});
