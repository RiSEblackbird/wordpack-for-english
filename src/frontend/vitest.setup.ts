import { afterAll, afterEach, beforeAll, vi } from 'vitest';

// Ensure global fetch exists (jsdom 21 provides fetch by default, but keep fallback)
if (!(globalThis as any).fetch) {
  (globalThis as any).fetch = (...args: any[]) =>
    import('node-fetch').then(({ default: fetch }) => (fetch as any)(...args));
}

// Base mock for /api/config so SettingsContext doesn't 404 in tests
const originalFetch = globalThis.fetch.bind(globalThis);

beforeAll(() => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : (input as URL).toString();
    if (url.endsWith('/api/config') && (!init || (init && (!init.method || init.method === 'GET')))) {
      return new Response(
        JSON.stringify({ request_timeout_ms: 60000 }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }
    return originalFetch(input as any, init as any);
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {
  (globalThis.fetch as any).mockRestore?.();
});


