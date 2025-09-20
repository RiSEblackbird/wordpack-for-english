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
      let message = `Request failed: ${res.status}`;
      // FastAPI の detail は任意型。 {message, hint, reason_code} を優先
      if (data && typeof data === 'object' && 'detail' in (data as any)) {
        const d = (data as any).detail;
        if (Array.isArray(d)) {
          // 422のバリデーションエラー配列を可読な1行へ
          const parts = d.map((e) => {
            try {
              const loc = Array.isArray(e.loc) ? e.loc.join('.') : e.loc;
              return `${loc}: ${e.msg}`;
            } catch {
              return JSON.stringify(e);
            }
          });
          message = parts.join('; ');
        } else if (d && typeof d === 'object') {
          const m = typeof (d as any).message === 'string' ? (d as any).message : undefined;
          const hint = typeof (d as any).hint === 'string' ? (d as any).hint : undefined;
          const rc = typeof (d as any).reason_code === 'string' ? (d as any).reason_code : undefined;
          const diag = (d as any).diagnostics ? ` diagnostics=${JSON.stringify((d as any).diagnostics)}` : '';
          message = [m || JSON.stringify(d), rc ? `(code=${rc})` : null, hint ? `hint: ${hint}` : null, diag]
            .filter(Boolean)
            .join(' ');
        } else {
          message = String(d);
        }
      }
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


