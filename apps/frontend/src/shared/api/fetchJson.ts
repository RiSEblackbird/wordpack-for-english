import { ApiError } from './ApiError';
import { parseApiErrorMessage } from './parseApiErrorMessage';
import { dispatchUnauthorizedEvent } from './unauthorizedEvent';

export interface FetchJsonOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
  credentials?: RequestCredentials;
}

export async function fetchJson<T = any>(url: string, options: FetchJsonOptions = {}): Promise<T> {
  const {
    method = 'GET',
    headers = {},
    body,
    signal,
    timeoutMs = 15000,
    credentials = 'include',
  } = options;

  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort();
  if (signal) {
    if (signal.aborted) ctrl.abort();
    else signal.addEventListener('abort', onAbort, { once: true });
  }

  const timer = window.setTimeout(() => {
    try {
      ctrl.abort();
    } catch {}
  }, timeoutMs);

  try {
    const res = await fetch(url, {
      method,
      headers: body
        ? { 'Content-Type': 'application/json', 'Cache-Control': 'no-store, no-cache', Pragma: 'no-cache', ...headers }
        : { 'Cache-Control': 'no-store, no-cache', Pragma: 'no-cache', ...headers },
      cache: 'no-store',
      credentials,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });

    window.clearTimeout(timer);

    const contentType = res.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined);

    if (!res.ok) {
      const status = res.status;
      const message = parseApiErrorMessage(status, data);
      if (status === 401) {
        dispatchUnauthorizedEvent(url, status, data);
      }
      throw new ApiError(message, status, data);
    }

    return data as T;
  } catch (err: any) {
    if (ctrl.signal.aborted) {
      throw new ApiError('Request aborted or timed out', 0);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(err?.message || 'Network error', 0);
  } finally {
    if (signal) signal.removeEventListener('abort', onAbort as any);
    window.clearTimeout(timer);
  }
}
