import React, { useEffect, useRef, useState } from 'react';
import { formatDateJst } from '../lib/date';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { useConfirmDialog } from '../ConfirmDialogContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { useNotifications } from '../NotificationsContext';
import { regenerateWordPackRequest } from '../lib/wordpack';
import { Modal } from './Modal';
import ArticleDetailModal, { ArticleDetailData } from './ArticleDetailModal';

interface ArticleListItem {
  id: string;
  title_en: string;
  created_at: string;
  updated_at: string;
}

interface ArticleListResponse {
  items: ArticleListItem[];
  total: number;
  limit: number;
  offset: number;
}

type ArticleDetailResponse = ArticleDetailData;

export const ArticleListPanel: React.FC = () => {
  const { settings } = useSettings();
  const { setModalOpen } = useModal();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const confirmDialog = useConfirmDialog();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ArticleListItem[]>([]);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [total, setTotal] = useState(0);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [preview, setPreview] = useState<ArticleDetailResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const abortRef = useRef<AbortController | null>(null);

  const load = async (newOffset = 0) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetchJson<ArticleListResponse>(`${settings.apiBase}/article?limit=${limit}&offset=${newOffset}`, { signal: ctrl.signal });
      setItems(res.items);
      setTotal(res.total);
      setOffset(newOffset);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '文章一覧の読み込みに失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelectedIds((prev) => {
      const valid = new Set(items.map((it) => it.id));
      const next = new Set<string>();
      prev.forEach((id) => {
        if (valid.has(id)) next.add(id);
      });
      if (next.size === prev.size) {
        return prev;
      }
      return next;
    });
  }, [items]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  const allVisibleSelected = items.length > 0 && items.every((it) => selectedIds.has(it.id));

  const toggleVisibleSelection = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) {
        items.forEach((it) => next.delete(it.id));
      } else {
        items.forEach((it) => next.add(it.id));
      }
      return next;
    });
  };

  const open = async (id: string) => {
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${id}`);
      setPreview(res);
      setPreviewOpen(true);
      try { setModalOpen(true); } catch {}
    } catch (e) {
      const m = e instanceof ApiError ? e.message : '文章の取得に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const del = async (item: ArticleListItem) => {
    const targetLabel = item.title_en?.trim() || '文章';
    const confirmed = await confirmDialog(targetLabel);
    if (!confirmed) return;
    setLoading(true);
    setMsg(null);
    try {
      await fetchJson(`${settings.apiBase}/article/${item.id}`, { method: 'DELETE' });
      await load(offset);
      setSelectedIds((prev) => {
        if (!prev.has(item.id)) return prev;
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
      setMsg({ kind: 'status', text: '削除しました' });
    } catch (e) {
      const m = e instanceof ApiError ? e.message : '削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const deleteWordPack = async (wordPackId: string) => {
    if (!preview) return;
    const lemmaLabel = (() => {
      try { return preview.related_word_packs.find((l) => l.word_pack_id === wordPackId)?.lemma?.trim(); }
      catch { return undefined; }
    })();
    const confirmed = await confirmDialog(lemmaLabel || 'WordPack');
    if (!confirmed) return;
    setLoading(true);
    setMsg(null);
    try {
      await fetchJson(`${settings.apiBase}/word/packs/${wordPackId}`, { method: 'DELETE' });
      const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${preview.id}`);
      setPreview(refreshed);
      setMsg({ kind: 'status', text: 'WordPackを削除しました' });
      try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'WordPackの削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const regenerateWordPack = async (wordPackId: string) => {
    if (!preview) return;
    setLoading(true);
    setMsg(null);
    const lemma = (() => {
      try { return preview.related_word_packs.find((l) => l.word_pack_id === wordPackId)?.lemma || 'WordPack'; } catch { return 'WordPack'; }
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
        // 設定からモデルを渡す（未設定ならサーバ既定に委ねる）
        model: settings.model,
        lemma,
        notify: { add: addNotification, update: updateNotification },
        abortSignal: ctrl.signal,
        messages: {
          progress: 'WordPackを再生成しています',
          success: '再生成が完了しました',
          failure: undefined, // ApiError.message を優先
        },
      });
      const refreshed = await fetchJson<ArticleDetailResponse>(`${settings.apiBase}/article/${preview.id}`);
      setPreview(refreshed);
      setMsg({ kind: 'status', text: 'WordPackを再生成しました' });
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'WordPackの再生成に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); return () => abortRef.current?.abort(); }, []);
  // インポート完了などで記事が更新されたら、現在のオフセットで再読込
  useEffect(() => {
    const onUpdated = () => { load(offset); };
    try { window.addEventListener('article:updated', onUpdated as EventListener); } catch {}
    return () => {
      try { window.removeEventListener('article:updated', onUpdated as EventListener); } catch {}
    };
  }, [offset]);

  const hasNext = offset + limit < total;
  const hasPrev = offset > 0;
  const selectedCount = selectedIds.size;

  const deleteSelectedArticles = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    const confirmed = await confirmDialog(`選択中の文章（${ids.length}件）`);
    if (!confirmed) return;
    setLoading(true);
    setMsg(null);
    let deleted = 0;
    let failure: string | null = null;
    try {
      for (const id of ids) {
        try {
          await fetchJson(`${settings.apiBase}/article/${id}`, { method: 'DELETE' });
          deleted += 1;
        } catch (error) {
          const message = error instanceof ApiError ? error.message : '削除に失敗しました';
          failure = message;
          break;
        }
      }
      if (deleted > 0) {
        await load(offset);
        setSelectedIds(new Set());
      }
      if (failure) {
        const text = deleted > 0
          ? `文章を${deleted}件削除しましたが一部失敗しました: ${failure}`
          : `文章の削除に失敗しました: ${failure}`;
        setMsg({ kind: 'alert', text });
      } else if (deleted > 0) {
        setMsg({ kind: 'status', text: `文章を${deleted}件削除しました` });
      } else {
        setMsg({ kind: 'alert', text: '削除対象がありません' });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <style>{`
        .al-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.5rem; }
        .al-card { border: 1px solid var(--color-border); border-radius: 8px; padding: 0.5rem; background: var(--color-surface); cursor: pointer; }
        .al-card-header { display: flex; align-items: center; gap: 0.5rem; }
        .al-card-title-row { display: flex; align-items: center; gap: 0.5rem; flex: 1; }
        .wp-selection-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin: 0.75rem 0; font-size: 0.9em; }
        .wp-selection-bar button { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-selection-bar button:disabled { opacity: 0.6; cursor: not-allowed; }
        .wp-select-checkbox { display: inline-flex; align-items: center; justify-content: center; }
        .wp-select-checkbox input { width: 1rem; height: 1rem; cursor: pointer; }
      `}</style>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2>インポート済み文章</h2>
        <button onClick={() => load(offset)} disabled={loading}>更新</button>
      </div>
      {msg && <div role={msg.kind}>{msg.text}</div>}
      <div className="wp-selection-bar" role="group" aria-label="文章選択操作">
        <span>選択中: {selectedCount}件</span>
        <button type="button" onClick={toggleVisibleSelection} disabled={items.length === 0}>
          {allVisibleSelected ? '表示中を選択解除' : '表示中を全選択'}
        </button>
        <button type="button" onClick={clearSelection} disabled={selectedCount === 0}>
          全選択解除
        </button>
        <button
          type="button"
          onClick={deleteSelectedArticles}
          disabled={selectedCount === 0 || loading}
        >選択した文章を削除</button>
      </div>
      <div className="al-grid">
        {items.map((it) => (
          <div key={it.id} className="al-card" onClick={() => open(it.id)}>
            <div className="al-card-header">
              <label className="wp-select-checkbox" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(it.id)}
                  onChange={() => toggleSelect(it.id)}
                  aria-label={`文章 ${it.title_en} を選択`}
                />
              </label>
              <div className="al-card-title-row">
                <strong style={{ flex: 1, fontSize: '12px' }}>{it.title_en}</strong>
                <button onClick={(e) => { e.stopPropagation(); del(it); }} aria-label={`delete-article-${it.id}`}>削除</button>
              </div>
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-subtle)' }}>更新: {formatDateJst(it.updated_at)}</div>
          </div>
        ))}
      </div>
      {(hasPrev || hasNext) && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 8 }}>
          <button onClick={() => load(offset - limit)} disabled={!hasPrev || loading}>前へ</button>
          <span>{offset + 1}-{Math.min(offset + limit, total)} / {total}件</span>
          <button onClick={() => load(offset + limit)} disabled={!hasNext || loading}>次へ</button>
        </div>
      )}

      <ArticleDetailModal
        isOpen={previewOpen}
        onClose={() => { setPreviewOpen(false); try { setModalOpen(false); } catch {} }}
        article={preview}
        title="文章プレビュー"
        onRegenerateWordPack={regenerateWordPack}
        onDeleteWordPack={deleteWordPack}
      />
    </section>
  );
};


