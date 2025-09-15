import { fetchJson, ApiError } from './fetcher';

export interface RegenerateSettings {
  pronunciationEnabled: boolean;
  regenerateScope: 'all' | 'examples' | 'collocations';
  requestTimeoutMs: number;
  temperature: number;
  reasoningEffort?: 'minimal' | 'low' | 'medium' | 'high';
  textVerbosity?: 'low' | 'medium' | 'high';
}

export interface NotificationsAdapter {
  add: (input: { title: string; message?: string; status?: 'progress' | 'success' | 'error'; id?: string }) => string;
  update: (id: string, patch: { title?: string; message?: string; status?: 'progress' | 'success' | 'error' }) => void;
}

export interface RegenerateWordPackMessages {
  // Body text shown while processing (beneath the title)
  progress?: string; // e.g. "WordPackを再生成しています"
  // Body text shown on success (beneath the title)
  success?: string; // e.g. "再生成が完了しました"
  // Body text shown on failure (beneath the title). If omitted, error.message (if ApiError) is used
  failure?: string; // e.g. "WordPackの再生成に失敗しました"
}

export async function regenerateWordPackRequest(params: {
  apiBase: string;
  wordPackId: string;
  settings: RegenerateSettings;
  model?: string;
  lemma?: string;
  notify: NotificationsAdapter;
  abortSignal?: AbortSignal;
  messages?: RegenerateWordPackMessages;
}): Promise<void> {
  const { apiBase, wordPackId, settings, model = 'gpt-5-mini', lemma = 'WordPack', notify, abortSignal, messages } = params;

  const notifId = notify.add({
    title: `【${lemma}】の生成処理中...`,
    message: messages?.progress || '処理を実行しています（LLM応答の受信と解析を待機中）',
    status: 'progress',
  });

  try {
    const body: any = {
      pronunciation_enabled: settings.pronunciationEnabled,
      regenerate_scope: settings.regenerateScope,
      model,
    };
    if ((model || '').toLowerCase() === 'gpt-5-mini') {
      body.reasoning = { effort: settings.reasoningEffort || 'minimal' };
      body.text = { verbosity: settings.textVerbosity || 'medium' };
    } else {
      body.temperature = settings.temperature;
    }

    await fetchJson(`${apiBase}/word/packs/${wordPackId}/regenerate`, {
      method: 'POST',
      body,
      signal: abortSignal,
      timeoutMs: Math.max(settings.requestTimeoutMs, 300000),
    });

    notify.update(notifId, { title: `【${lemma}】の生成完了！`, status: 'success', message: messages?.success || '処理が完了しました' });
    try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
  } catch (e) {
    const m = messages?.failure || (e instanceof ApiError ? e.message : '処理に失敗しました');
    notify.update(notifId, { title: `【${lemma}】の生成失敗`, status: 'error', message: m });
    throw e;
  }
}


