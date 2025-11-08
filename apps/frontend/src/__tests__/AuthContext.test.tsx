import { render, waitFor, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';
import { vi } from 'vitest';
import { AuthProvider, useAuth } from '../AuthContext';

const googleProviderMock = vi.fn(({ children }: { children: React.ReactNode }) => <>{children}</>);

vi.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => googleProviderMock({ children }),
}));

const MissingFlagProbe: React.FC = () => {
  const { missingClientId } = useAuth();
  return <span data-testid="client-flag">{missingClientId ? 'missing' : 'ok'}</span>;
};

describe('AuthProvider logging behaviour', () => {
  // 新規参画者向けメモ: 認証バイパス有効時のログレベル切り替えを固定するための回帰テスト。
  // バイパス環境では error を抑制し warn に切り替わることをここで保証する。
  let fetchMock: vi.MockedFunction<typeof fetch>;

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

    fetchMock.mockImplementation((input) => {
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

    fetchMock.mockImplementation((input) => {
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
