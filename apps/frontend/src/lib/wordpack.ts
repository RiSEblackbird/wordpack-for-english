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
  add: (input: { title: string; message?: string; status?: 'progress' | 'success' | 'error'; id?: string; model?: string; category?: string }) => string;
  update: (id: string, patch: { title?: string; message?: string; status?: 'progress' | 'success' | 'error'; model?: string; category?: string }) => void;
}

export interface RegenerateWordPackMessages {
  // Body text shown while processing (beneath the title)
  progress?: string; // Example: "WordPackを再生成しています"
  // Body text shown on success (beneath the title)
  success?: string; // Example: 成功時に表示するメッセージ
  // Body text shown on failure (beneath the title). If omitted, error.message (if ApiError) is used
  failure?: string; // Example: 失敗時に表示するメッセージ
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
  const { apiBase, wordPackId, settings, model, lemma = 'WordPack', notify, abortSignal, messages } = params;

  const notifId = notify.add({
    title: `【${lemma}】の生成処理中...`,
    message: messages?.progress || '処理を実行しています（LLM応答の受信と解析を待機中）',
    status: 'progress',
    model: model || undefined,
  });

  try {
    const body: any = {
      pronunciation_enabled: settings.pronunciationEnabled,
      regenerate_scope: settings.regenerateScope,
      // モデル未指定時はサーバ既定に任せる（キー自体を省略）
      ...(model ? { model } : {}),
    };
    if ((model || '').toLowerCase() === 'gpt-5-mini' || (model || '').toLowerCase() === 'gpt-5-nano') {
      body.reasoning = { effort: settings.reasoningEffort || 'minimal' };
      body.text = { verbosity: settings.textVerbosity || 'medium' };
    } else if (model) {
      body.temperature = settings.temperature;
    }

    await fetchJson(`${apiBase}/word/packs/${wordPackId}/regenerate`, {
      method: 'POST',
      body,
      signal: abortSignal,
      // サーバの LLM_TIMEOUT_MS と厳密に一致させる（/api/config 同期値）
      timeoutMs: settings.requestTimeoutMs,
    });

    notify.update(notifId, { title: `【${lemma}】の生成完了！`, status: 'success', message: messages?.success || '処理が完了しました', model: model || undefined });
    try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
  } catch (e) {
    const m = messages?.failure || (e instanceof ApiError ? e.message : '処理に失敗しました');
    notify.update(notifId, { title: `【${lemma}】の生成失敗`, status: 'error', message: m, model: model || undefined });
    throw e;
  }
}


