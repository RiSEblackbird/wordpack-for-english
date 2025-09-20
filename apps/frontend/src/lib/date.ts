function parseDateToMs(dateStr: string): number | null {
  try {
    const hasTimezone = /[Zz]|[+\-]\d{2}:?\d{2}$/.test(dateStr);
    const normalized = hasTimezone ? dateStr : `${dateStr}Z`;
    const date = new Date(normalized);
    const ms = date.getTime();
    if (Number.isNaN(ms)) return null;
    return ms;
  } catch {
    return null;
  }
}

export function formatDateJst(dateStr: string): string {
  const ms = parseDateToMs(dateStr);
  if (ms === null) return dateStr;
  try {
    const date = new Date(ms);
    return date.toLocaleString('ja-JP', {
      timeZone: 'Asia/Tokyo',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    } as Intl.DateTimeFormatOptions);
  } catch {
    return dateStr;
  }
}

export function calculateDurationMs(start?: string | null, end?: string | null): number | null {
  if (!start || !end) return null;
  const startMs = parseDateToMs(start);
  const endMs = parseDateToMs(end);
  if (startMs === null || endMs === null) return null;
  return Math.max(0, endMs - startMs);
}

export function formatDurationMs(durationMs: number): string {
  if (!Number.isFinite(durationMs) || durationMs < 0) return '';
  if (durationMs === 0) {
    return '0秒';
  }
  if (durationMs < 1000) {
    return `${Math.round(durationMs)}ミリ秒`;
  }
  const totalSeconds = durationMs / 1000;
  if (totalSeconds < 60) {
    if (totalSeconds < 10) {
      const rounded = Number(totalSeconds.toFixed(1));
      return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}秒`;
    }
    return `${Math.round(totalSeconds)}秒`;
  }
  const totalRoundedSeconds = Math.round(totalSeconds);
  let remaining = totalRoundedSeconds;
  const hours = Math.floor(remaining / 3600);
  remaining -= hours * 3600;
  const minutes = Math.floor(remaining / 60);
  remaining -= minutes * 60;
  let seconds = remaining;
  if (seconds === 60) {
    seconds = 0;
  }
  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}時間`);
  if (minutes > 0) parts.push(`${minutes}分`);
  if (seconds > 0) parts.push(`${seconds}秒`);
  if (parts.length === 0) {
    return `${Math.round(totalSeconds)}秒`;
  }
  return parts.join('');
}


