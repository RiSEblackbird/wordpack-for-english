import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { LoadingIndicator } from './LoadingIndicator';
import { ListControls } from './ListControls';
import { ExampleDetailModal, ExampleItemData } from './ExampleDetailModal';

type SortKey = 'created_at' | 'pack_updated_at' | 'lemma' | 'category';
type SortOrder = 'asc' | 'desc';
type SearchMode = 'prefix' | 'suffix' | 'contains';
type ViewMode = 'card' | 'list';

interface ExampleListResponse {
  items: ExampleItemData[];
  total: number;
  limit: number;
  offset: number;
}

const CATEGORY_OPTIONS: Array<{ value: ExampleItemData['category'] | 'all'; label: string }> = [
  { value: 'all', label: '-' },
  { value: 'Dev', label: 'Dev' },
  { value: 'CS', label: 'CS' },
  { value: 'LLM', label: 'LLM' },
  { value: 'Business', label: 'Business' },
  { value: 'Common', label: 'Common' },
];

export const ExampleListPanel: React.FC = () => {
  const { settings } = useSettings();
  const STORAGE_KEY = 'examples.list.ui_state.v1';
  const [items, setItems] = useState<ExampleItemData[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(200);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [searchMode, setSearchMode] = useState<SearchMode>('contains');
  const [searchInput, setSearchInput] = useState('');
  const [appliedSearch, setAppliedSearch] = useState<{ mode: SearchMode; value: string } | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<ExampleItemData['category'] | 'all'>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('card');
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewItem, setPreviewItem] = useState<ExampleItemData | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  type PersistedState = {
    sortKey: SortKey;
    sortOrder: SortOrder;
    searchMode: SearchMode;
    searchInput: string;
    appliedSearch: { mode: SearchMode; value: string } | null;
    categoryFilter: ExampleItemData['category'] | 'all';
    viewMode: ViewMode;
    offset: number;
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const s = JSON.parse(raw) as Partial<PersistedState>;
      if (s.sortKey) setSortKey(s.sortKey);
      if (s.sortOrder) setSortOrder(s.sortOrder);
      if (s.searchMode) setSearchMode(s.searchMode);
      if (typeof s.searchInput === 'string') setSearchInput(s.searchInput);
      if (s.appliedSearch) setAppliedSearch(s.appliedSearch);
      if (s.categoryFilter) setCategoryFilter(s.categoryFilter);
      if (s.viewMode) setViewMode(s.viewMode);
      if (typeof s.offset === 'number' && Number.isFinite(s.offset) && s.offset >= 0) setOffset(s.offset);
    } catch {}
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const p: PersistedState = { sortKey, sortOrder, searchMode, searchInput, appliedSearch, categoryFilter, viewMode, offset };
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(p)); } catch {}
  }, [sortKey, sortOrder, searchMode, searchInput, appliedSearch, categoryFilter, viewMode, offset]);

  const handleApplySearch = () => setAppliedSearch({ mode: searchMode, value: searchInput.trim() });
  const handleToggleExpand = (id: number) => setExpandedIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const buildQuery = (o: number) => {
    const sp = new URLSearchParams();
    sp.set('limit', String(limit));
    sp.set('offset', String(o));
    sp.set('order_by', sortKey);
    sp.set('order_dir', sortOrder);
    if (appliedSearch && appliedSearch.value) {
      sp.set('search', appliedSearch.value);
      sp.set('search_mode', appliedSearch.mode);
    }
    if (categoryFilter !== 'all') sp.set('category', categoryFilter);
    return sp.toString();
  };

  const load = async (newOffset: number = offset) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      const q = buildQuery(newOffset);
      const res = await fetchJson<ExampleListResponse>(`${settings.apiBase}/word/examples?${q}`, { signal: ctrl.signal });
      setItems(res.items);
      setTotal(res.total);
      setOffset(newOffset);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const m = e instanceof ApiError ? e.message : '例文一覧の読み込みに失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(offset);
    return () => abortRef.current?.abort();
  }, [appliedSearch, sortKey, sortOrder, categoryFilter]);

  const hasNext = offset + limit < total;
  const hasPrev = offset > 0;

  const sortOptions = useMemo(() => ([
    { value: 'created_at', label: '作成日時(例文)' },
    { value: 'pack_updated_at', label: '更新日時(WordPack)' },
    { value: 'lemma', label: '単語名' },
    { value: 'category', label: 'カテゴリ' },
  ] as const), []);

  return (
    <section>
      <style>{`
        .ex-list-container { max-width: 100%; }
        .ex-list-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; }
        @media (max-width: 768px) {
          .ex-list-grid { grid-template-columns: 1fr; }
        }
        .ex-card { border: 1px solid #e5e7eb; border-radius: 6px; padding: 0.6rem; background:rgb(224, 183, 112); cursor: pointer; color: #111827; }
        .ex-card h4 { margin: 0 0 0.25rem 0; font-size: 1.0em; }
        .ex-meta { font-size: 0.75em; color: #6b7280; }
        .ex-actions { display: flex; gap: 0.5rem; margin-top: 0.4rem; }
        .ex-list-item { display: flex; align-items: start; gap: 0.5rem; padding: 0.4rem; border-bottom: 1px solid #eee; cursor: pointer; }
        .ex-en { font-weight: 600; }
        .ex-ja { margin-top: 0.3rem; }
        /* view-specific text colors */
        .ex-list-container[data-view="card"] .ex-en { color: #111827; }
        .ex-list-container[data-view="card"] .ex-ja { color: #374151; }
        .ex-list-container[data-view="list"] .ex-en { color:rgb(240, 230, 245); }
        .ex-list-container[data-view="list"] .ex-ja { color: #334155; }
        .wp-view-toggle { display: flex; gap: 0.3rem; align-items: center; margin-bottom: 0.5rem; }
        .wp-toggle-btn { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-toggle-btn[aria-pressed="true"] { background: #e3f2fd; border-color: #2196f3; }
        .wp-pagination { display: flex; justify-content: center; gap: 0.5rem; margin-top: 1rem; }
      `}</style>

      <div className="ex-list-container" data-view={viewMode}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>例文一覧</h2>
          <button onClick={() => load(offset)} disabled={loading}>更新</button>
        </div>

        <div className="wp-view-toggle" role="group" aria-label="表示モード">
          <button type="button" className="wp-toggle-btn" aria-pressed={viewMode === 'card'} onClick={() => setViewMode('card')}>カード</button>
          <button type="button" className="wp-toggle-btn" aria-pressed={viewMode === 'list'} onClick={() => setViewMode('list')}>リスト</button>
        </div>

        <ListControls<SortKey>
          sortKey={sortKey}
          sortOptions={sortOptions as any}
          onChangeSortKey={setSortKey}
          sortOrder={sortOrder}
          onChangeSortOrder={setSortOrder}
          searchMode={searchMode}
          onChangeSearchMode={setSearchMode}
          searchInput={searchInput}
          onChangeSearchInput={setSearchInput}
          onApplySearch={handleApplySearch}
          filtersRight={(
            <>
              <label htmlFor="ex-cat" style={{ marginLeft: '0.5rem' }}>カテゴリ:</label>
              <select id="ex-cat" className="wp-filter-select" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value as any)}>
                {CATEGORY_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </>
          )}
        />

        {loading && (
          <LoadingIndicator label="一覧を取得中" subtext="保存済みの例文メタデータを取得しています…" />
        )}
        {msg && <div role={msg.kind}>{msg.text}</div>}

        {items.length === 0 && !loading ? (
          <div style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>保存済みの例文がありません。</div>
        ) : (
          <>
            {viewMode === 'card' ? (
              <div className="ex-list-grid">
                {items.map((it) => (
                  <div key={it.id} className="ex-card" onClick={() => { setPreviewItem(it); setPreviewOpen(true); }}>
                    <div className="ex-meta" style={{ marginBottom: 4 }}>{it.lemma} / {it.category}</div>
                    <h4 className="ex-en">{it.en}</h4>
                    <div className="ex-actions">
                      <button type="button" onClick={(e) => { e.stopPropagation(); handleToggleExpand(it.id); }}>
                        訳表示
                      </button>
                    </div>
                    {expandedIds.has(it.id) && (
                      <div className="ex-ja">{it.ja}</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div>
                {items.map((it) => (
                  <div key={it.id} className="ex-list-item" onClick={() => { setPreviewItem(it); setPreviewOpen(true); }}>
                    <div style={{ flex: 1 }}>
                      <div className="ex-meta" style={{ marginBottom: 4 }}>{it.lemma} / {it.category}</div>
                      <div className="ex-en">{it.en}</div>
                      <div className="ex-actions">
                        <button type="button" onClick={(e) => { e.stopPropagation(); handleToggleExpand(it.id); }}>訳表示</button>
                      </div>
                      {expandedIds.has(it.id) && <div className="ex-ja">{it.ja}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {(hasPrev || hasNext) && (
              <div className="wp-pagination">
                <button onClick={() => load(offset - limit)} disabled={!hasPrev || loading}>前へ</button>
                <span>{offset + 1}-{Math.min(offset + limit, total)} / {total}件</span>
                <button onClick={() => load(offset + limit)} disabled={!hasNext || loading}>次へ</button>
              </div>
            )}
          </>
        )}
      </div>

      <ExampleDetailModal isOpen={previewOpen} onClose={() => setPreviewOpen(false)} item={previewItem} />
    </section>
  );
};


