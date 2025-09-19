import React, { useEffect, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { useNotifications } from '../NotificationsContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { regenerateWordPackRequest } from '../lib/wordpack';
import { Modal } from './Modal';
import { WordPackPanel } from './WordPackPanel';
import ArticleDetailModal, { ArticleDetailData } from './ArticleDetailModal';

interface ArticleWordPackLink {
  word_pack_id: string;
  lemma: string;
  status: 'existing' | 'created';
  is_empty?: boolean;
}

type ArticleDetailResponse = ArticleDetailData;

export const ArticleImportPanel: React.FC = () => {
  const { settings, setSettings } = useSettings();
  const { setModalOpen } = useModal();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [genRunning, setGenRunning] = useState(0);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [article, setArticle] = useState<ArticleDetailResponse | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [wpPreviewOpen, setWpPreviewOpen] = useState(false);
  const [wpPreviewId, setWpPreviewId] = useState<string | null>(null);
  const [category, setCategory] = useState<'Dev'|'CS'|'LLM'|'Business'|'Common'>('Common');
  const abortRef = useRef<AbortController | null>(null);

  const [model, setModel] = useState<string>(settings.model || 'gpt-5-mini');

  const importArticle = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    setArticle(null);
    const notifId = addNotification({ title: '文章インポート中...', message: 'LLMで要約と語彙抽出を実行しています', status: 'progress' });
    try {
      const body: any = { text: text.trim() };
      // WordPackPanel と同様のモデル選択ロジック
      body.model = model;
      if ((model || '').toLowerCase() === 'gpt-5-mini' || (model || '').toLowerCase() === 'gpt-5-nano') {
        body.reasoning = { effort: settings.reasoningEffort || 'minimal' };
        body.text_opts = { verbosity: settings.textVerbosity || 'medium' };
      } else {
        body.temperature = settings.temperature;
      }
      const res = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/import`, {
        method: 'POST',
        body,
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      // 一覧カードと同じ導線: GET の結果のみで表示（フォールバックしない）
      const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${res.id}`, {
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      setArticle(refreshed);
      setMsg({ kind: 'status', text: '文章をインポートしました' });
      updateNotification(notifId, { title: '文章インポート完了', status: 'success', message: '詳細を表示します' });
      // グローバルに記事更新イベントを通知（一覧の自動更新用）
      try { window.dispatchEvent(new CustomEvent('article:updated')); } catch {}
      setDetailOpen(true);
      try { setModalOpen(true); } catch {}
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '文章インポートに失敗しました';
      setMsg({ kind: 'alert', text: m });
      updateNotification(notifId, { title: '文章インポート失敗', status: 'error', message: m });
    } finally {
      setLoading(false);
    }
  };

  const regenerateWordPack = async (wordPackId: string) => {
    if (!article) return;
    const lemma = (() => {
      try { return article.related_word_packs.find((l) => l.word_pack_id === wordPackId)?.lemma || 'WordPack'; } catch { return 'WordPack'; }
    })();
    const ctrl = new AbortController();
    try {
      await regenerateWordPackRequest({
        apiBase: settings.apiBase,
        wordPackId,
        settings: {
          pronunciationEnabled: settings.pronunciationEnabled,
          regenerateScope: settings.regenerateScope,
          requestTimeoutMs: settings.requestTimeoutMs,
          temperature: settings.temperature,
          reasoningEffort: settings.reasoningEffort,
          textVerbosity: settings.textVerbosity,
        },
        model,
        lemma,
        notify: { add: addNotification, update: updateNotification },
        abortSignal: ctrl.signal,
        messages: {
          progress: 'WordPackを再生成しています',
          success: '再生成が完了しました',
          failure: undefined, // ApiError.message を優先
        },
      });
      const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${article.id}`);
      setArticle(refreshed);
    } catch {
      // 通知は内部で完結
    }
  };

  const deleteWordPack = async (wordPackId: string) => {
    if (!article) return;
    if (!confirm('このWordPackを削除しますか？')) return;
    const ctrl = new AbortController();
    setLoading(true);
    setMsg(null);
    try {
      await fetchJson(`${settings.apiBase}/word/packs/${wordPackId}`, {
        method: 'DELETE',
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      // 記事詳細を再取得して関連WordPack一覧を最新化
      const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${article.id}`);
      setArticle(refreshed);
      setMsg({ kind: 'status', text: 'WordPackを削除しました' });
      try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'WordPackの削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <style>{`
        .ai-grid { display: grid; grid-template-columns: 1fr; gap: 0.75rem; }
        .ai-textarea { width: 60%; min-height: 5rem; padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 6px; }
        .ai-wp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.5rem; }
        .ai-card { border: 1px solid var(--color-border); border-radius: 6px; padding: 0.5rem; background: var(--color-surface); }
        .ai-badge { font-size: 0.75em; padding: 0.1rem 0.4rem; border-radius: 999px; border: 1px solid var(--color-border); }
      `}</style>

      <h2>文章インポート</h2>
      <div className="ai-grid">
        <textarea
          className="ai-textarea"
          placeholder="文章を貼り付け（日本語/英語）"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading}
        />
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button onClick={importArticle} disabled={loading || !text.trim()}>インポート</button>
          <select value={category} onChange={(e) => setCategory(e.target.value as any)}>
            <option value="Dev">Dev</option>
            <option value="CS">CS</option>
            <option value="LLM">LLM</option>
            <option value="Business">Business</option>
            <option value="Common">Common</option>
          </select>
          <button
            onClick={async () => {
              setMsg(null);
              setArticle(null);
              setGenRunning((n) => n + 1);
              const notifId = addNotification({ title: `【${category}】について例文生成&インポートを開始します`, message: '関連語を選定し、例文を生成して記事化します', status: 'progress' });
              try {
                const reqBody: any = { category };
                // generate_and_import は text キーで受け取る
                reqBody.model = model;
                if ((model || '').toLowerCase() === 'gpt-5-mini' || (model || '').toLowerCase() === 'gpt-5-nano') {
                  reqBody.reasoning = { effort: settings.reasoningEffort || 'minimal' };
                  reqBody.text = { verbosity: settings.textVerbosity || 'medium' };
                } else {
                  reqBody.temperature = settings.temperature;
                }
                const res = await fetchJson<{ lemma: string; word_pack_id: string; category: string; generated_examples: number; article_ids: string[] }>(`${settings.apiBase}/article/generate_and_import`, {
                  method: 'POST',
                  body: reqBody,
                  // サーバの LLM_TIMEOUT_MS と厳密に一致させる（/api/config 同期値）
                  timeoutMs: settings.requestTimeoutMs,
                });
                updateNotification(notifId, { title: '生成＆インポート完了', status: 'success', message: `【${res.lemma}】${res.generated_examples}件の例文から記事を作成しました` });
                try { window.dispatchEvent(new CustomEvent('article:updated')); } catch {}
                setMsg({ kind: 'status', text: '生成＆インポートを実行しました' });
              } catch (e) {
                const m = e instanceof ApiError ? e.message : '生成＆インポートに失敗しました';
                setMsg({ kind: 'alert', text: m });
                updateNotification(notifId, { title: '生成＆インポート失敗', status: 'error', message: m });
              } finally {
                setGenRunning((n) => Math.max(0, n - 1));
              }
            }}
          >
            生成＆インポート{genRunning > 0 ? `（実行中 ${genRunning}）` : ''}
          </button>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            モデル
            <select
              value={model}
              onChange={(e) => { const v = e.target.value; setModel(v); setSettings({ ...settings, model: v }); }}
              disabled={loading}
            >
              <option value="gpt-5-mini">gpt-5-mini</option>
              <option value="gpt-5-nano">gpt-5-nano</option>
              <option value="gpt-4.1-mini">gpt-4.1-mini</option>
              <option value="gpt-4o-mini">gpt-4o-mini</option>
            </select>
          </label>
          {(((model || '').toLowerCase() === 'gpt-5-mini') || ((model || '').toLowerCase() === 'gpt-5-nano')) && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                reasoning.effort
                <select
                  aria-label="reasoning.effort"
                  value={settings.reasoningEffort || 'minimal'}
                  onChange={(e) => setSettings({ ...settings, reasoningEffort: e.target.value as any })}
                  disabled={loading}
                >
                  <option value="minimal">minimal</option>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                text.verbosity
                <select
                  aria-label="text.verbosity"
                  value={settings.textVerbosity || 'medium'}
                  onChange={(e) => setSettings({ ...settings, textVerbosity: e.target.value as any })}
                  disabled={loading}
                >
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </label>
            </div>
          )}
        </div>
        {msg && <div role={msg.kind}>{msg.text}</div>}
      </div>

      <ArticleDetailModal
        isOpen={!!article && detailOpen}
        onClose={() => { setDetailOpen(false); try { setModalOpen(false); } catch {} }}
        article={article}
        title="インポート結果"
        onRegenerateWordPack={regenerateWordPack}
        onOpenWordPackPreview={(id) => { setWpPreviewId(id); setWpPreviewOpen(true); try { setModalOpen(true); } catch {} }}
        onDeleteWordPack={deleteWordPack}
      />

      <Modal
        isOpen={!!wpPreviewId && wpPreviewOpen}
        onClose={() => { setWpPreviewOpen(false); setWpPreviewId(null); try { setModalOpen(false); } catch {} }}
        title="WordPack プレビュー"
      >
        {wpPreviewId ? (
          <div>
            <WordPackPanel
              focusRef={useRef<HTMLElement>(null)}
              selectedWordPackId={wpPreviewId}
              onWordPackGenerated={async () => {
                // 詳細で再生成などがあったら記事詳細を更新
                if (article) {
                  const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${article.id}`);
                  setArticle(refreshed);
                }
                try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
              }}
            />
          </div>
        ) : null}
      </Modal>
    </section>
  );
};


