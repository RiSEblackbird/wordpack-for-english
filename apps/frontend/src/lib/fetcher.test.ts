import { describe, expect, it, vi, afterEach } from 'vitest';
import { fetchJson } from './fetcher';

type FetchMock = ReturnType<typeof vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>>;

const buildJsonResponse = (payload: unknown = { ok: true }) => {
  return {
    ok: true,
    status: 200,
    headers: {
      get: vi.fn().mockReturnValue('application/json'),
    } as unknown as Headers,
    json: vi.fn().mockResolvedValue(payload),
    text: vi.fn().mockResolvedValue(''),
  };
};

const installFetchMock = (responsePayload?: unknown): FetchMock => {
  const mock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
  mock.mockResolvedValue(buildJsonResponse(responsePayload) as unknown as Response);
  globalThis.fetch = mock as unknown as typeof fetch;
  return mock;
};

describe('fetchJson credential behavior', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = originalFetch;
  });

  it('sends credentials=include by default', async () => {
    const fetchMock = installFetchMock({ ok: true });

    await fetchJson('/api/article/import');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/article/import',
      expect.objectContaining({
        credentials: 'include',
        cache: 'no-store',
        method: 'GET',
      }),
    );
  });

  it('allows overriding credentials option', async () => {
    const fetchMock = installFetchMock({ ok: true });

    await fetchJson('/api/article/import', { credentials: 'omit' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/article/import',
      expect.objectContaining({
        credentials: 'omit',
      }),
    );
  });
});

