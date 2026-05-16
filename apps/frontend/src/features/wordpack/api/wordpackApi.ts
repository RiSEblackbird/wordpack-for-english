import { fetchJson } from '../../../lib/fetcher';
import {
  composeModelRequestFields,
  regenerateWordPackRequest,
  updateGuestPublicFlag,
} from '../../../lib/wordpack';
import type { WordPack } from '../types';

export { composeModelRequestFields, regenerateWordPackRequest, updateGuestPublicFlag };

export const fetchWordPack = (
  apiBase: string,
  wordPackId: string,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<WordPack> => (
  fetchJson<WordPack>(`${apiBase}/word/packs/${wordPackId}`, options)
);

export const createEmptyWordPackRequest = (
  apiBase: string,
  lemma: string,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<{ id: string }> => (
  fetchJson<{ id: string }>(`${apiBase}/word/packs`, {
    method: 'POST',
    body: { lemma },
    signal: options?.signal,
    timeoutMs: options?.timeoutMs,
  })
);

export const generateWordPackRequest = (
  apiBase: string,
  body: Record<string, unknown>,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<WordPack> => (
  fetchJson<WordPack>(`${apiBase}/word/pack`, {
    method: 'POST',
    body,
    signal: options?.signal,
    timeoutMs: options?.timeoutMs,
  })
);

export const updateGuestPublicRequest = updateGuestPublicFlag;
