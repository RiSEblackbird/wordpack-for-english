import React, { useEffect, useState, useRef } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { Modal } from './Modal';
import { WordPackPanel } from './WordPackPanel';

interface Props {
  onSelectWordPack: (wordPackId: string) => void;
  onRegenerateWordPack: (wordPackId: string) => void;
}

interface WordPackListItem {
  id: string;
  lemma: string;
  created_at: string;
  updated_at: string;
}

interface WordPackListResponse {
  items: WordPackListItem[];
  total: number;
  limit: number;
  offset: number;
}

export const WordPackListPanel: React.FC<Props> = ({ onSelectWordPack, onRegenerateWordPack }) => {
  const { settings } = useSettings();
  const [wordPacks, setWordPacks] = useState<WordPackListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const abortRef = useRef<AbortController | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewWordPackId, setPreviewWordPackId] = useState<string | null>(null);
  const modalFocusRef = useRef<HTMLElement>(null);

  const loadWordPacks = async (newOffset: number = 0) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    
    try {
      const res = await fetchJson<WordPackListResponse>(`${settings.apiBase}/word/packs?limit=${limit}&offset=${newOffset}`, {
        signal: ctrl.signal,
      });
      setWordPacks(res.items);
      setTotal(res.total);
      setOffset(newOffset);
      setMsg({ kind: 'status', text: `${res.items.length}件のWordPackを読み込みました` });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPack一覧の読み込みに失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  const deleteWordPack = async (wordPackId: string) => {
    if (!confirm('このWordPackを削除しますか？')) return;
    
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    
    try {
      await fetchJson(`${settings.apiBase}/word/packs/${wordPackId}`, {
        method: 'DELETE',
        signal: ctrl.signal,
      });
      setMsg({ kind: 'status', text: 'WordPackを削除しました' });
      // 一覧を再読み込み
      await loadWordPacks(offset);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPackの削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWordPacks();
    return () => abortRef.current?.abort();
  }, []);

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('ja-JP');
    } catch {
      return dateStr;
    }
  };

  const hasNext = offset + limit < total;
  const hasPrev = offset > 0;

  return (
    <section>
      <style>{`
        .wp-list-container { max-width: 100%; }
        .wp-list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .wp-list-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .wp-card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .wp-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
        .wp-card-title { font-size: 1.2em; font-weight: bold; color: #333; margin: 0; }
        .wp-card-meta { font-size: 0.85em; color: #666; margin: 0.25rem 0; }
        .wp-card-actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
        .wp-card-actions button { padding: 0.25rem 0.5rem; font-size: 0.85em; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-card-actions button:hover { background: #f5f5f5; }
        .wp-card-actions button.danger { color: #d32f2f; border-color: #d32f2f; }
        .wp-card-actions button.danger:hover { background: #ffebee; }
        .wp-pagination { display: flex; justify-content: center; gap: 0.5rem; margin-top: 1rem; }
        .wp-pagination button { padding: 0.5rem 1rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
        .wp-pagination button:hover:not(:disabled) { background: #f5f5f5; }
        .wp-empty { text-align: center; color: #666; padding: 2rem; }
        @media (max-width: 640px) { 
          .wp-list-grid { grid-template-columns: 1fr; }
          .wp-card-header { flex-direction: column; align-items: flex-start; }
        }
      `}</style>

      <div className="wp-list-container">
        <div className="wp-list-header">
          <h2>保存済みWordPack一覧</h2>
          <button onClick={() => loadWordPacks(offset)} disabled={loading}>
            更新
          </button>
        </div>

        {loading && <div role="status">読み込み中…</div>}
        {msg && <div role={msg.kind}>{msg.text}</div>}

        {wordPacks.length === 0 && !loading ? (
          <div className="wp-empty">
            <p>保存済みのWordPackがありません。</p>
            <p>新しいWordPackを生成してください。</p>
          </div>
        ) : (
          <>
            <div className="wp-list-grid">
              {wordPacks.map((wp) => (
                <div key={wp.id} className="wp-card">
                  <div className="wp-card-header">
                    <h3 className="wp-card-title">{wp.lemma}</h3>
                  </div>
                  <div className="wp-card-meta">
                    <div>作成: {formatDate(wp.created_at)}</div>
                    <div>更新: {formatDate(wp.updated_at)}</div>
                  </div>
                  <div className="wp-card-actions">
                    <button onClick={() => { setPreviewWordPackId(wp.id); setPreviewOpen(true); }}>
                      表示
                    </button>
                    <button onClick={() => onRegenerateWordPack(wp.id)}>
                      再生成
                    </button>
                    <button 
                      className="danger" 
                      onClick={() => deleteWordPack(wp.id)}
                    >
                      削除
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {(hasPrev || hasNext) && (
              <div className="wp-pagination">
                <button 
                  onClick={() => loadWordPacks(offset - limit)} 
                  disabled={!hasPrev || loading}
                >
                  前へ
                </button>
                <span>
                  {offset + 1}-{Math.min(offset + limit, total)} / {total}件
                </span>
                <button 
                  onClick={() => loadWordPacks(offset + limit)} 
                  disabled={!hasNext || loading}
                >
                  次へ
                </button>
              </div>
            )}
          </>
        )}
      </div>
      <Modal isOpen={previewOpen} onClose={() => setPreviewOpen(false)} title="WordPack プレビュー">
        {previewWordPackId ? (
          <WordPackPanel
            focusRef={modalFocusRef}
            selectedWordPackId={previewWordPackId}
          />
        ) : null}
      </Modal>
    </section>
  );
};
