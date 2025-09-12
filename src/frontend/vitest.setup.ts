import { afterAll, afterEach, beforeAll, vi } from 'vitest';

// Ensure global fetch exists without external deps
if (!(globalThis as any).fetch) {
  (globalThis as any).fetch = ((): any => {
    throw new Error('global fetch is not available. Provide a mock in tests.');
  }) as any;
}

// Base mock for /api/config so SettingsContext doesn't 404 in tests
const originalFetch = (globalThis.fetch as any).bind(globalThis);

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


