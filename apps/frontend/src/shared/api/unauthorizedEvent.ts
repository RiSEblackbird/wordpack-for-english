import { APP_EVENTS, dispatchAppEvent } from '../events/appEvents';

export const dispatchUnauthorizedEvent = (url: string, status: number, body: unknown): void => {
  dispatchAppEvent(APP_EVENTS.authUnauthorized, {
    url,
    status,
    body: body ?? null,
  });
};
