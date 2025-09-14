import React, { useEffect, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { useNotifications } from '../NotificationsContext';
import { fetchJson, ApiError } from '../lib/fetcher';
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
  const { settings } = useSettings();
  const { setModalOpen } = useModal();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [article, setArticle] = useState<ArticleDetailResponse | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [wpPreviewOpen, setWpPreviewOpen] = useState(false);
  const [wpPreviewId, setWpPreviewId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

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
    const ctrl = new AbortController();
    const notifId = addNotification({ title: 'WordPack生成中...', message: '内容を生成しています', status: 'progress' });
    try {
      await fetchJson(`${settings.apiBase}/word/packs/${wordPackId}/regenerate`, {
        method: 'POST',
        body: {},
        signal: ctrl.signal,
        timeoutMs: settings.requestTimeoutMs,
      });
      // 生成完了後、記事詳細を再取得して最新の is_empty 状態に更新
      const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${article.id}`);
      setArticle(refreshed);
      updateNotification(notifId, { title: '生成完了', status: 'success', message: 'WordPackを更新しました' });
      // グローバル更新イベントを発火（WordPack一覧が開いていれば反映用）
      try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'WordPackの生成に失敗しました';
      updateNotification(notifId, { title: '生成失敗', status: 'error', message: m });
    }
  };

  return (
    <section>
      <style>{`
        .ai-grid { display: grid; grid-template-columns: 1fr; gap: 0.75rem; }
        .ai-textarea { width: 100%; min-height: 10rem; padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 6px; }
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
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={importArticle} disabled={loading || !text.trim()}>インポート</button>
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


