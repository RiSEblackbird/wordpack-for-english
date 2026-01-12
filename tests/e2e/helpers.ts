import type { BrowserContext, Page, Route } from '@playwright/test';

export interface MockUser {
  google_sub: string;
  email: string;
  display_name: string;
}

const DEFAULT_USER: MockUser = {
  google_sub: 'e2e-user',
  email: 'e2e@example.com',
  display_name: 'E2E User',
};

export const createAuthStoragePayload = (user: MockUser = DEFAULT_USER) => ({
  authMode: 'authenticated',
  user,
});

/**
 * OAuth ポップアップを回避するため、Cookie と localStorage を両方セットする。
 * なぜ: UI 依存を外しつつ、認証済みの画面遷移だけを再現するため。
 */
export const seedAuthenticatedSession = async (
  context: BrowserContext,
  page: Page,
  user: MockUser = DEFAULT_USER,
): Promise<void> => {
  const now = Date.now();
  await context.addCookies([
    {
      name: 'wp_session',
      value: 'e2e-session-token',
      domain: '127.0.0.1',
      path: '/',
      httpOnly: true,
      sameSite: 'Lax',
      expires: Math.floor((now + 60 * 60 * 1000) / 1000),
    },
    {
      name: '__session',
      value: 'e2e-session-token',
      domain: '127.0.0.1',
      path: '/',
      httpOnly: true,
      sameSite: 'Lax',
      expires: Math.floor((now + 60 * 60 * 1000) / 1000),
    },
  ]);
  await page.addInitScript((payload) => {
    window.localStorage.setItem('wordpack.auth.v1', JSON.stringify(payload));
  }, createAuthStoragePayload(user));
};

export const mockConfig = async (
  page: Page,
  options: { requestTimeoutMs?: number; sessionAuthDisabled?: boolean } = {},
): Promise<void> => {
  const { requestTimeoutMs = 60000, sessionAuthDisabled = false } = options;
  await page.route('**/api/config', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        request_timeout_ms: requestTimeoutMs,
        session_auth_disabled: sessionAuthDisabled,
      }),
    }),
  );
};

export const json = (data: unknown, status = 200): { status: number; contentType: string; body: string } => ({
  status,
  contentType: 'application/json',
  body: JSON.stringify(data),
});

export const ignoreRoute = async (route: Route): Promise<void> => {
  await route.fulfill({ status: 204 });
};
