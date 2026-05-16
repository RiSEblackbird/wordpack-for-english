interface FastApiValidationErrorItem {
  loc?: unknown;
  msg?: unknown;
}

export interface FastApiDetailObject {
  message?: unknown;
  hint?: unknown;
  reason_code?: unknown;
  diagnostics?: unknown;
}

const isRecord = (value: unknown): value is Record<string, unknown> => (
  Boolean(value) && typeof value === 'object'
);

export const getFastApiDetail = (data: unknown): unknown => {
  if (!isRecord(data) || !('detail' in data)) {
    return undefined;
  }
  return data.detail;
};

export const formatValidationDetail = (detail: FastApiValidationErrorItem[]): string => (
  detail.map((item) => {
    const loc = Array.isArray(item.loc) ? item.loc.join('.') : item.loc;
    return `${loc}: ${String(item.msg ?? '')}`;
  }).join('; ')
);

export const formatObjectDetail = (detail: FastApiDetailObject): string => {
  const message = typeof detail.message === 'string' ? detail.message : undefined;
  const hint = typeof detail.hint === 'string' ? detail.hint : undefined;
  const reasonCode = typeof detail.reason_code === 'string' ? detail.reason_code : undefined;
  const diagnostics = detail.diagnostics
    ? ` diagnostics=${JSON.stringify(detail.diagnostics)}`
    : '';
  return [
    message || JSON.stringify(detail),
    reasonCode ? `(code=${reasonCode})` : null,
    hint ? `hint: ${hint}` : null,
    diagnostics,
  ]
    .filter(Boolean)
    .join(' ');
};

export const isProviderAuthenticationDetail = (data: unknown): boolean => {
  const detail = getFastApiDetail(data);
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) {
    return false;
  }
  const { message, reason_code: reasonCode } = detail as FastApiDetailObject;
  return (
    reasonCode === 'AUTH'
    && typeof message === 'string'
    && message.toLowerCase().includes('llm provider')
  );
};
