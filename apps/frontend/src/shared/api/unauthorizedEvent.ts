export const dispatchUnauthorizedEvent = (url: string, status: number, body: unknown): void => {
  try {
    window.dispatchEvent(
      new CustomEvent('auth:unauthorized', {
        detail: {
          url,
          status,
          body: body ?? null,
        },
      }),
    );
  } catch {
    // Browser外環境では何もしない。
  }
};
