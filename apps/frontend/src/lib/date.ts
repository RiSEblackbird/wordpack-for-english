export function formatDateJst(dateStr: string): string {
  try {
    const hasTimezone = /[Zz]|[+\-]\d{2}:?\d{2}$/.test(dateStr);
    const normalized = hasTimezone ? dateStr : `${dateStr}Z`;
    const date = new Date(normalized);
    if (isNaN(date.getTime())) return dateStr;
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


