import { render, waitFor, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';
import { vi } from 'vitest';
import type { MockedFunction } from 'vitest';
import { AuthProvider, useAuth } from '../AuthContext';

const googleProviderMock = vi.fn(({ children }: { children: React.ReactNode }) => <>{children}</>);

vi.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => googleProviderMock({ children }),
}));

const MissingFlagProbe: React.FC = () => {
  const { missingClientId } = useAuth();
  return <span data-testid="client-flag">{missingClientId ? 'missing' : 'ok'}</span>;
};

const TokenLeakProbe: React.FC = () => {
  const contextValue = useAuth();
  const hasTokenKey = Object.prototype.hasOwnProperty.call(
    contextValue as Record<string, unknown>,
    'token',
  );
  return <span data-testid="token-leak">{hasTokenKey ? 'leaked' : 'clean'}</span>;
};

describe('AuthProvider logging behaviour', () => {
  // 新規参画者向けメモ: 認証バイパス有効時のログレベル切り替えを固定するための回帰テスト。
  // バイパス環境では error を抑制し warn に切り替わることをここで保証する。
  let fetchMock: MockedFunction<typeof fetch>;

  beforeEach(() => {
    fetchMock = vi.fn();
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock;
    googleProviderMock.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderProvider = () => {
    render(
      <AuthProvider clientId="">
        <div data-testid="auth-provider-child" />
      </AuthProvider>,
    );
  };

  it('provides missingClientId flag and skips Google provider when client ID is empty', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    render(
      <AuthProvider clientId=" ">
        <MissingFlagProbe />
      </AuthProvider>,
    );

    expect(await screen.findByTestId('client-flag')).toHaveTextContent('missing');
    expect(googleProviderMock).not.toHaveBeenCalled();
  });

  it('prefers console.warn when bypass mode supplies a development credential', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input instanceof Request ? input.url : '';
      if (url.endsWith('/api/config')) {
        return Promise.resolve(
          new Response(JSON.stringify({ session_auth_disabled: true }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(new Response('{}', { status: 200 }));
    });

    renderProvider();

    await waitFor(() => {
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('VITE_GOOGLE_CLIENT_ID is not set; Google login will not work.'),
      );
    });
    expect(errorSpy).not.toHaveBeenCalled();
  });

  it('falls back to console.error when bypass is not available', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input instanceof Request ? input.url : '';
      if (url.endsWith('/api/config')) {
        return Promise.resolve(
          new Response(JSON.stringify({}), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(new Response('{}', { status: 200 }));
    });

    renderProvider();

    await waitFor(() => {
      expect(errorSpy).toHaveBeenCalledWith(
        'VITE_GOOGLE_CLIENT_ID is not set; Google login will not work.',
      );
    });
    expect(warnSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('Authentication bypass is active; continuing with development fallback.'),
    );
  });
});

describe('AuthProvider persistence behaviour', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    try { localStorage.clear(); } catch { /* ignore */ }
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('persists user information without ID token leakage', async () => {
    const sampleUser = {
      google_sub: 'sub-123',
      email: 'tester@example.com',
      display_name: 'Tester',
    };

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith('/api/config') && (!init || init.method === 'GET' || !init.method)) {
        return Promise.resolve(
          new Response(JSON.stringify({}), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (url.endsWith('/api/auth/google') && init?.method === 'POST') {
        return Promise.resolve(
          new Response(
            JSON.stringify({ user: sampleUser }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      return Promise.resolve(new Response('not found', { status: 404 }));
    });

    const setItemSpy = vi.spyOn(Object.getPrototypeOf(window.localStorage), 'setItem');

    const SignInProbe: React.FC = () => {
      const { signIn, user } = useAuth();
      React.useEffect(() => {
        if (!user) {
          void (signIn('dummy-id-token').catch(() => undefined));
        }
      }, [signIn, user]);
      return null;
    };

    render(
      <AuthProvider clientId="test-client">
        <SignInProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/google'),
        expect.objectContaining({ method: 'POST' }),
      );
    });

    await waitFor(() => {
      expect(setItemSpy).toHaveBeenCalledWith(
        'wordpack.auth.v1',
        expect.any(String),
      );
    });

    const [, storedValue] = setItemSpy.mock.calls[setItemSpy.mock.calls.length - 1];
    const payload = JSON.parse(storedValue as string) as Record<string, unknown>;

    expect(payload).toHaveProperty('user');
    expect(payload).not.toHaveProperty('token');
    expect(payload.user).toMatchObject(sampleUser);

    setItemSpy.mockRestore();
  });
});

describe('AuthProvider public API surface', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    try { localStorage.clear(); } catch { /* ignore */ }
  });

  it('does not expose token field via context value', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    render(
      <AuthProvider clientId="test-client">
        <TokenLeakProbe />
      </AuthProvider>,
    );

    expect(await screen.findByTestId('token-leak')).toHaveTextContent('clean');
    expect(fetchMock).toHaveBeenCalledWith('/api/config', { method: 'GET' });
  });
});
