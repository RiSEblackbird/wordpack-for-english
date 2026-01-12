import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

// 統合テストでは実HTTPを使うため、MSW のモック層を明示的に無効化する。
const isIntegrationTest = process.env.INTEGRATION_TEST === 'true';

// Ensure global fetch exists without external deps
if (!(globalThis as any).fetch) {
  (globalThis as any).fetch = ((): any => {
    throw new Error('global fetch is not available. Provide a mock in tests.');
  }) as any;
}

// Provide a robust matchMedia polyfill for jsdom environment used by Vitest
if (!(globalThis as any).window?.matchMedia) {
  const mm = (query: string) => {
    const listeners: Set<(e: MediaQueryListEvent) => void> = new Set();
    const mql: MediaQueryList = {
      media: query,
      matches: false,
      onchange: null,
      addListener: (cb: (e: MediaQueryListEvent) => void) => listeners.add(cb), // legacy API
      removeListener: (cb: (e: MediaQueryListEvent) => void) => listeners.delete(cb), // legacy API
      addEventListener: (_type: 'change', cb: (e: MediaQueryListEvent) => void) => listeners.add(cb as any),
      removeEventListener: (_type: 'change', cb: (e: MediaQueryListEvent) => void) => listeners.delete(cb as any),
      dispatchEvent: (_ev: Event) => false,
    } as any;
    return mql;
  };
  (globalThis as any).window = (globalThis as any).window ?? (globalThis as any);
  (globalThis as any).window.matchMedia = mm as any;
}

// SettingsContext/AuthContext の初期同期に使う /api/config をテスト環境で安定供給する。
export const server = setupServer(
  http.get('/api/config', () => {
    return HttpResponse.json({ request_timeout_ms: 60000 });
  }),
);

beforeAll(() => {
  if (isIntegrationTest) return;
  server.listen({ onUnhandledRequest: 'warn' });
});

afterEach(() => {
  if (!isIntegrationTest) {
    server.resetHandlers();
  }
  vi.clearAllMocks();
});

afterAll(() => {
  if (isIntegrationTest) return;
  server.close();
});


