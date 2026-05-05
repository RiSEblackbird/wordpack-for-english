import type { CredentialResponse } from '@react-oauth/google';
import { sanitizeTelemetryPayload } from './sanitizeTelemetry';

const OAUTH_TELEMETRY_ENDPOINT = '/api/diagnostics/oauth-telemetry';

export const sendMissingIdTokenTelemetry = async (
  googleClientId: string,
  credentialResponse: CredentialResponse | null | undefined,
): Promise<void> => {
  if (typeof fetch !== 'function') {
    return;
  }
  try {
    await fetch(OAUTH_TELEMETRY_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'google_login_missing_id_token',
        googleClientId,
        errorCategory: 'missing_id_token',
        tokenResponse: sanitizeTelemetryPayload(credentialResponse as Record<string, unknown> | undefined),
      }),
    });
  } catch (error) {
    console.warn('Failed to send OAuth telemetry for missing ID token', error);
  }
};
