import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { Modal } from './Modal';
import { ListControls } from './ListControls';
import { WordPackPanel } from './WordPackPanel';
import { LoadingIndicator } from './LoadingIndicator';
import { formatDateJst } from '../lib/date';

// 削除ボタンの共通コンポーネント
interface DeleteButtonProps {
  onClick: (e: React.MouseEvent) => void;
  disabled?: boolean;
}

const DeleteButton: React.FC<DeleteButtonProps> = ({ onClick, disabled = false }) => {
  return (
    <button 
      className="danger" 
      onClick={onClick}
      disabled={disabled}
      style={{ 
        padding: '0.04rem 0.07rem', 
        fontSize: '0.40em', 
        border: '1px solid #d32f2f', 
        borderRadius: '4px', 
        background: 'rgb(234, 230, 217)', 
        cursor: disabled ? 'not-allowed' : 'pointer',
        color: '#d32f2f',
        marginLeft: 'auto',
        opacity: disabled ? 0.6 : 1
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = '#ffebee';
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = 'rgb(234, 230, 217)';
        }
      }}
    >
      削除
    </button>
  );
};

interface WordPackListItem {
  id: string;
  lemma: string;
  created_at: string;
  updated_at: string;
  is_empty?: boolean;
  examples_count?: {
    Dev: number;
    CS: number;
    LLM: number;
    Business: number;
    Common: number;
  };
}

type SortKey = 'created_at' | 'updated_at' | 'lemma' | 'total_examples';
type SortOrder = 'asc' | 'desc';
type ViewMode = 'card' | 'list';
type GenerationFilter = 'all' | 'generated' | 'not_generated';
type SearchMode = 'prefix' | 'suffix' | 'contains';

interface WordPackListItemWithTotal extends WordPackListItem {
  totalExamples: number;
}

type PersistedState = {
  sortKey: SortKey;
  sortOrder: SortOrder;
  viewMode: ViewMode;
  generationFilter: GenerationFilter;
  searchMode: SearchMode;
  searchInput: string;
  appliedSearch: { mode: SearchMode; value: string } | null;
  offset: number;
};

const STORAGE_KEY = 'wp.list.ui_state.v1';
const PAGE_LIMIT = 200;
const MIN_COLUMN_WIDTH = 320;

const getFallbackColumnCount = (width: number): number => {
  if (width >= 1600) return 4;
  if (width >= 1200) return 3;
  if (width >= 900) return 2;
  return 1;
};

const computeColumnCount = (width: number): number => {
  const count = Math.floor(width / MIN_COLUMN_WIDTH);
  return Math.min(4, Math.max(1, count));
};

const sumExamples = (counts?: WordPackListItem['examples_count']): number => {
  if (!counts) return 0;
  return Object.values(counts).reduce((sum, count) => sum + count, 0);
};

const matchString = (text: string, query: string, mode: SearchMode): boolean => {
  if (!query) return true;
  if (mode === 'prefix') return text.startsWith(query);
  if (mode === 'suffix') return text.endsWith(query);
  return text.includes(query);
};

interface WordPackListResponse {
  items: WordPackListItem[];
  total: number;
  limit: number;
  offset: number;
}

export const WordPackListPanel: React.FC = () => {
  const { settings: { apiBase } } = useSettings();
  const { setModalOpen } = useModal();
  const [wordPacks, setWordPacks] = useState<WordPackListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewWordPackId, setPreviewWordPackId] = useState<string | null>(null);
  const modalFocusRef = useRef<HTMLElement>(null);
  const [sortKey, setSortKey] = useState<SortKey>('updated_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [viewMode, setViewMode] = useState<ViewMode>('card');
  const [generationFilter, setGenerationFilter] = useState<GenerationFilter>('all');
  const [searchMode, setSearchMode] = useState<SearchMode>('contains');
  const [searchInput, setSearchInput] = useState('');
  const [appliedSearch, setAppliedSearch] = useState<{ mode: SearchMode; value: string } | null>(null);
  // グリッドの可視幅に基づき列数を算出（最大4列）
  const gridRef = useRef<HTMLDivElement | null>(null);
  const [columnCount, setColumnCount] = useState<number>(() =>
    typeof window === 'undefined' ? 1 : getFallbackColumnCount(window.innerWidth)
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const el = gridRef.current;
    const fallbackUpdate = () => setColumnCount(getFallbackColumnCount(window.innerWidth));
    if (!el) {
      requestAnimationFrame(() => {
        const next = gridRef.current;
        if (next) {
          setColumnCount(computeColumnCount(next.clientWidth));
        } else {
          fallbackUpdate();
        }
      });
      return;
    }
    const update = () => setColumnCount(computeColumnCount(el.clientWidth));
    update();
    let ro: ResizeObserver | null = null;
    if ('ResizeObserver' in window) {
      ro = new ResizeObserver(() => update());
      ro.observe(el);
    }
    window.addEventListener('resize', update);
    return () => {
      if (ro) ro.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [viewMode]);

  // --- UI状態の保存/復元（sessionStorage） ---
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const s = JSON.parse(raw) as Partial<PersistedState>;
      if (s.sortKey) setSortKey(s.sortKey);
      if (s.sortOrder) setSortOrder(s.sortOrder);
      if (s.viewMode) setViewMode(s.viewMode);
      if (s.generationFilter) setGenerationFilter(s.generationFilter);
      if (s.searchMode) setSearchMode(s.searchMode);
      if (typeof s.searchInput === 'string') setSearchInput(s.searchInput);
      if (s.appliedSearch) setAppliedSearch(s.appliedSearch);
      if (typeof s.offset === 'number' && Number.isFinite(s.offset) && s.offset >= 0) setOffset(s.offset);
    } catch {
      // ignore parse errors
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const p: PersistedState = {
      sortKey,
      sortOrder,
      viewMode,
      generationFilter,
      searchMode,
      searchInput,
      appliedSearch,
      offset,
    };
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(p)); } catch {}
  }, [sortKey, sortOrder, viewMode, generationFilter, searchMode, searchInput, appliedSearch, offset]);

  const loadWordPacks = useCallback(async (newOffset: number = 0) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);

    try {
      const res = await fetchJson<WordPackListResponse>(`${apiBase}/word/packs?limit=${PAGE_LIMIT}&offset=${newOffset}`, {
        signal: ctrl.signal,
      });
      setWordPacks(res.items);
      setTotal(res.total);
      setOffset(newOffset);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPack一覧の読み込みに失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  const deleteWordPack = useCallback(async (wordPackId: string) => {
    if (!confirm('このWordPackを削除しますか？')) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);

    try {
      await fetchJson(`${apiBase}/word/packs/${wordPackId}`, {
        method: 'DELETE',
        signal: ctrl.signal,
      });
      setMsg({ kind: 'status', text: 'WordPackを削除しました' });
      await loadWordPacks(offset);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : 'WordPackの削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  }, [apiBase, loadWordPacks, offset]);

  useEffect(() => {
    loadWordPacks();
    return () => abortRef.current?.abort();
  }, [loadWordPacks]);

  useEffect(() => {
    const onUpdated = () => { loadWordPacks(offset); };
    try { window.addEventListener('wordpack:updated', onUpdated as EventListener); } catch {}
    return () => {
      try { window.removeEventListener('wordpack:updated', onUpdated as EventListener); } catch {}
    };
  }, [loadWordPacks, offset]);

  const formatDate = (dateStr: string) => formatDateJst(dateStr);

  const normalizedSearch = useMemo(() => {
    if (!appliedSearch) return null;
    const value = appliedSearch.value.trim().toLowerCase();
    if (!value) return null;
    return { mode: appliedSearch.mode, value };
  }, [appliedSearch]);

  const normalizedWordPacks = useMemo<WordPackListItemWithTotal[]>(
    () =>
      wordPacks.map((wp) => ({
        ...wp,
        totalExamples: sumExamples(wp.examples_count),
      })),
    [wordPacks]
  );

  const filteredWordPacks = useMemo(() => {
    return normalizedWordPacks.filter((wp) => {
      if (generationFilter === 'generated' && wp.totalExamples <= 0) return false;
      if (generationFilter === 'not_generated' && wp.totalExamples > 0) return false;
      if (normalizedSearch) {
        const lemma = (wp.lemma || '').toLowerCase();
        if (!matchString(lemma, normalizedSearch.value, normalizedSearch.mode)) return false;
      }
      return true;
    });
  }, [normalizedWordPacks, generationFilter, normalizedSearch]);

  const sortedWordPacks = useMemo(() => {
    return [...filteredWordPacks].sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortKey) {
        case 'created_at':
        case 'updated_at':
          aValue = new Date(a[sortKey]).getTime();
          bValue = new Date(b[sortKey]).getTime();
          break;
        case 'lemma':
          aValue = a.lemma.toLowerCase();
          bValue = b.lemma.toLowerCase();
          break;
        case 'total_examples':
          aValue = a.totalExamples;
          bValue = b.totalExamples;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredWordPacks, sortKey, sortOrder]);

  const handleApplySearch = useCallback(() => {
    setAppliedSearch({ mode: searchMode, value: searchInput.trim() });
  }, [searchMode, searchInput]);

  const handleSortChange = useCallback(
    (newSortKey: SortKey) => {
      if (sortKey === newSortKey) {
        setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(newSortKey);
        setSortOrder('desc');
      }
    },
    [sortKey]
  );

  const hasNext = offset + PAGE_LIMIT < total;
  const hasPrev = offset > 0;

  return (
    <section>
      <style>{`
        .wp-list-container { max-width: 100%; }
        .wp-list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; max-height: 40px; }
        .wp-sort-controls { display: flex; align-items: center; gap: 0.3rem; margin-bottom: 0.5rem; }
        .wp-sort-select { padding: 0.25rem; border: 1px solid #ccc; border-radius: 4px; background: white; }
        .wp-sort-button { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; display: flex; align-items: center; gap: 0.25rem; }
        .wp-sort-button:hover { background: #f5f5f5; }
        .wp-sort-button.active { background: #e3f2fd; border-color: #2196f3; }
        .wp-filter-select { padding: 0.25rem; border: 1px solid #ccc; border-radius: 4px; background: white; }
        .wp-search-input { padding: 0.25rem; border: 1px solid #ccc; border-radius: 4px; }
        .wp-search-button { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-search-button:hover { background: #f5f5f5; }
        .wp-list-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .wp-card { border: 1px solid #ddd; border-radius: 6px; padding: 0.4rem; background:rgb(173, 159, 211); box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor: pointer; }
        .wp-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.2rem; }
        .wp-card-title { font-size: 1.0em; font-weight: bold; color: #333; margin: 0; }
        .wp-card-meta { font-size: 0.50em; color: #666; margin: 0.25rem 0; }
        .wp-badge { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 999px; font-size: 0.75em; margin-left: 0.5rem; }
        .wp-badge.empty { background: #fff3cd; color: #7a5b00; border: 1px solid #ffe08a; }
        .wp-pagination { display: flex; justify-content: center; gap: 0.5rem; margin-top: 1rem; }
        .wp-pagination button { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
        .wp-pagination button:hover:not(:disabled) { background: #f5f5f5; }
        .wp-empty { text-align: center; color: #666; padding: 2rem; }
        .wp-view-toggle { display: flex; gap: 0.3rem; align-items: center; margin-bottom: 0.5rem; }
        .wp-toggle-btn { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-toggle-btn[aria-pressed="true"] { background: #e3f2fd; border-color: #2196f3; }
        .wp-index-grid { display: grid; grid-template-columns: 1fr; gap: 0.55rem; padding: 0.5rem 0.0rem; }
        @media (min-width: 900px) and (max-width: 1199px) {
          .wp-index-grid { grid-template-columns: 1fr 1fr; }
        }
        @media (min-width: 1200px) and (max-width: 1599px) {
          .wp-index-grid { grid-template-columns: 1fr 1fr 1fr; }
        }
        @media (min-width: 1600px) {
          .wp-index-grid { grid-template-columns: 1fr 1fr 1fr 1fr; }
        }
        .wp-index-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.2rem 0.3rem; border-bottom: 1px solid #eee; cursor: pointer; background: transparent; border-radius: 4px; }
        .wp-index-title { font-size: 0.75em; font-weight: bold; color:rgb(233, 233, 233); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .wp-index-meta { font-size: 0.10em; color: #666; }
        @media (max-width: 640px) { 
          .wp-list-grid { grid-template-columns: 1fr; }
          .wp-card-header { flex-direction: column; align-items: flex-start; }
          .wp-sort-controls { flex-direction: column; align-items: stretch; }
        }
      `}</style>

      <div className="wp-list-container">
        <div className="wp-list-header">
          <h2>保存済みWordPack一覧</h2>
          <button onClick={() => loadWordPacks(offset)} disabled={loading}>
            更新
          </button>
        </div>

        <div className="wp-view-toggle" role="group" aria-label="表示モード">
          <button
            type="button"
            className="wp-toggle-btn"
            aria-pressed={viewMode === 'card'}
            onClick={() => setViewMode('card')}
            title="カード表示"
          >カード</button>
          <button
            type="button"
            className="wp-toggle-btn"
            aria-pressed={viewMode === 'list'}
            onClick={() => setViewMode('list')}
            title="リスト表示（索引）"
          >リスト</button>
        </div>

        <ListControls<SortKey>
          sortKey={sortKey}
          sortOptions={[
            { value: 'updated_at', label: '更新日時' },
            { value: 'created_at', label: '作成日時' },
            { value: 'lemma', label: '単語名' },
            { value: 'total_examples', label: '例文数' },
          ]}
          onChangeSortKey={(key) => handleSortChange(key)}
          sortOrder={sortOrder}
          onChangeSortOrder={setSortOrder}
          searchMode={searchMode}
          onChangeSearchMode={setSearchMode as any}
          searchInput={searchInput}
          onChangeSearchInput={setSearchInput}
          onApplySearch={handleApplySearch}
          filtersRight={(
            <>
              <label htmlFor="gen-filter" style={{ marginLeft: '0.5rem' }}>表示絞り込み:</label>
              <select
                id="gen-filter"
                className="wp-filter-select"
                value={generationFilter}
                onChange={(e) => setGenerationFilter(e.target.value as any)}
                aria-label="例文生成状況で絞り込み"
              >
                <option value="all">-</option>
                <option value="generated">生成済</option>
                <option value="not_generated">未生成</option>
              </select>
            </>
          )}
        />

        {loading && (
          <LoadingIndicator
            label="一覧を取得中"
            subtext="保存済みのWordPackメタデータを取得しています…"
          />
        )}
        {msg && <div role={msg.kind}>{msg.text}</div>}

        {wordPacks.length === 0 && !loading ? (
          <div className="wp-empty">
            <p>保存済みのWordPackがありません。</p>
            <p>新しいWordPackを生成してください。</p>
          </div>
        ) : (
          <>
            {viewMode === 'card' ? (
              <div className="wp-list-grid">
                {sortedWordPacks.map((wp) => (
                  <div
                    key={wp.id}
                    className="wp-card"
                    data-testid="wp-card"
                    onClick={() => { 
                      setPreviewWordPackId(wp.id); 
                      setPreviewOpen(true);
                      setModalOpen(true);
                    }}
                  >
                    <div className="wp-card-header">
                      <h3 className="wp-card-title">
                        {wp.lemma}
                      </h3>
                      <DeleteButton 
                        onClick={(e) => { e.stopPropagation(); deleteWordPack(wp.id); }}
                        disabled={loading}
                      />
                    </div>
                    <div className="wp-card-meta">
                      <div>作成: {formatDate(wp.created_at)} / 更新: {formatDate(wp.updated_at)}</div>
                      {wp.is_empty ? (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8em' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.1rem 0.3rem',
                            backgroundColor: '#fff3cd',
                            color: '#7a5b00',
                            borderRadius: '3px',
                            border: '1px solid #ffe08a',
                            fontSize: '0.75em'
                          }}>
                            例文未生成
                          </span>
                        </div>
                      ) : wp.examples_count && (
                        <div style={{ marginTop: '0.3rem', fontSize: '0.2em' }}>
                          <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                            {Object.entries(wp.examples_count).map(([category, count]) => (
                              <span key={category} style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.10rem',
                                padding: '0.1rem 0.2rem',
                                backgroundColor: count > 0 ? '#e3f2fd' : '#f5f5f5',
                                color: count > 0 ? '#1565c0' : '#666',
                                borderRadius: '3px',
                                border: `1px solid ${count > 0 ? '#1565c0' : '#ddd'}`,
                                fontSize: '0.40em'
                              }}>
                                <span style={{ fontWeight: 'bold' }}>{category}</span>
                                <span>{count}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div
                ref={gridRef}
                className="wp-index-grid"
                style={{
                  gridTemplateColumns: `repeat(${Math.max(1, columnCount)}, 1fr)`,
                  ...(columnCount > 1 ? {
                    gridAutoFlow: 'column',
                    gridTemplateRows: `repeat(${Math.max(1, Math.ceil(sortedWordPacks.length / Math.max(1, columnCount)))}, auto)`,
                  } : {}),
                }}
              >
                {sortedWordPacks.map((wp) => (
                  <div
                    key={wp.id}
                    className="wp-index-item"
                    data-testid="wp-index-item"
                    onClick={() => { 
                      setPreviewWordPackId(wp.id); 
                      setPreviewOpen(true);
                      setModalOpen(true);
                    }}
                  >
                    <span className="wp-index-title">{wp.lemma}</span>
                    <span className="wp-index-meta">{wp.is_empty ? ' / 未' : ` / 例文: ${wp.totalExamples}件`}</span>
                    <DeleteButton 
                      onClick={(e) => { e.stopPropagation(); deleteWordPack(wp.id); }}
                      disabled={loading}
                    />
                  </div>
                ))}
              </div>
            )}

            {(hasPrev || hasNext) && (
              <div className="wp-pagination">
                <button
                  onClick={() => loadWordPacks(Math.max(0, offset - PAGE_LIMIT))}
                  disabled={!hasPrev || loading}
                >
                  前へ
                </button>
                <span>
                  {offset + 1}-{Math.min(offset + PAGE_LIMIT, total)} / {total}件
                </span>
                <button
                  onClick={() => loadWordPacks(offset + PAGE_LIMIT)}
                  disabled={!hasNext || loading}
                >
                  次へ
                </button>
              </div>
            )}
          </>
        )}
      </div>
      <Modal 
        isOpen={previewOpen} 
        onClose={() => { 
          setPreviewOpen(false);
          setModalOpen(false);
        }} 
        title="WordPack プレビュー"
      >
        {previewWordPackId ? (
          <div data-testid="modal-wordpack-content">
            <WordPackPanel
              focusRef={modalFocusRef}
              selectedWordPackId={previewWordPackId}
              selectedMeta={(() => {
                const m = wordPacks.find(w => w.id === previewWordPackId);
                return m ? { created_at: m.created_at, updated_at: m.updated_at } : null;
              })()}
              onWordPackGenerated={async () => {
                // 再生成後に一覧を最新化（更新日時の整合）
                await loadWordPacks(offset);
              }}
            />
          </div>
        ) : null}
      </Modal>
    </section>
  );
};
