import { afterAll, afterEach, beforeAll, vi } from 'vitest';

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


