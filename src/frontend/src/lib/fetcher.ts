export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export interface FetchJsonOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
}

export async function fetchJson<T = any>(url: string, options: FetchJsonOptions = {}): Promise<T> {
  const { method = 'GET', headers = {}, body, signal, timeoutMs = 15000 } = options;

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
      headers: body ? { 'Content-Type': 'application/json', ...headers } : headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });

    window.clearTimeout(timer);

    const contentType = res.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined);

    if (!res.ok) {
      const message = (data && typeof data === 'object' && 'detail' in (data as any))
        ? String((data as any).detail)
        : `Request failed: ${res.status}`;
      throw new ApiError(message, res.status, data);
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


