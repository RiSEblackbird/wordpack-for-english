export const parseApiErrorMessage = (status: number, data: unknown): string => {
  let message = `Request failed: ${status}`;
  if (data && typeof data === 'object' && 'detail' in (data as any)) {
    const d = (data as any).detail;
    if (Array.isArray(d)) {
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
  return message;
};
