const SENSITIVE_TELEMETRY_KEYS = new Set(['access_token', 'id_token', 'refresh_token', 'code', 'credential']);

export const sanitizeSecretForTelemetry = (value: string): string => {
  if (!value) return '***';
  if (value.length <= 4) return '***';
  return `${value.slice(0, 2)}…${value.slice(-1)}`;
};

export const sanitizeEmailForTelemetry = (value: string): string => {
  const [local, domain] = value.split('@');
  if (!domain) {
    return sanitizeSecretForTelemetry(value);
  }
  if (local.length <= 2) {
    return `${local.charAt(0) || '*'}***@${domain}`;
  }
  return `${local.charAt(0)}***${local.charAt(local.length - 1)}@${domain}`;
};

export const sanitizeTelemetryPayload = (
  payload: Record<string, unknown> | null | undefined,
): Record<string, unknown> => {
  if (!payload) {
    return {};
  }
  return Object.entries(payload).reduce<Record<string, unknown>>((acc, [key, value]) => {
    if (typeof value === 'string') {
      if (SENSITIVE_TELEMETRY_KEYS.has(key)) {
        acc[key] = sanitizeSecretForTelemetry(value);
      } else if (value.includes('@')) {
        acc[key] = sanitizeEmailForTelemetry(value);
      } else {
        acc[key] = value;
      }
    } else {
      acc[key] = value as unknown;
    }
    return acc;
  }, {});
};
