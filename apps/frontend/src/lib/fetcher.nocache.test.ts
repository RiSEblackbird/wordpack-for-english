import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchJson } from './fetcher';

describe('fetchJson no-cache behavior', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('adds Cache-Control/Pragma headers and cache:no-store on GET', async () => {
    const spy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }) as any
    );

    const result = await fetchJson('/api/ping');
    expect(result).toEqual({ ok: true });

    expect(spy).toHaveBeenCalledTimes(1);
    const [, init] = spy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect((init as any).cache).toBe('no-store');
    expect(headers['Cache-Control']).toBe('no-store, no-cache');
    expect(headers['Pragma']).toBe('no-cache');
  });

  it('adds Content-Type and no-cache headers on POST with body', async () => {
    const spy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }) as any
    );

    await fetchJson('/api/echo', { method: 'POST', body: { a: 1 } });
    expect(spy).toHaveBeenCalledTimes(1);
    const [, init] = spy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
    expect(headers['Cache-Control']).toBe('no-store, no-cache');
    expect(headers['Pragma']).toBe('no-cache');
  });
});


