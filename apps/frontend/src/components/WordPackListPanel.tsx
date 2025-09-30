import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSettings } from '../SettingsContext';
import { useModal } from '../ModalContext';
import { useConfirmDialog } from '../ConfirmDialogContext';
import { useNotifications } from '../NotificationsContext';
import { fetchJson, ApiError } from '../lib/fetcher';
import { regenerateWordPackRequest } from '../lib/wordpack';
import { useAbortableAsync, AbortError } from '../lib/hooks';
import { loadSessionState, saveSessionState } from '../lib/storage';
import { assignSetValues, retainSetValues, toggleSetValue } from '../lib/set';
import { Modal } from './Modal';
import { ListControls } from './ListControls';
import { WordPackPanel } from './WordPackPanel';
import { LoadingIndicator } from './LoadingIndicator';
import { TTSButton } from './TTSButton';
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
        padding: '0.1rem 0.4rem',
        fontSize: '0.55em',
        border: '1px solid #d32f2f',
        borderRadius: '4px',
        background: 'rgb(234, 230, 217)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        color: '#d32f2f',
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
  sense_title?: string;
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
  checked_only_count: number;
  learned_count: number;
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
  showAllSense: boolean;
};

const STORAGE_KEY = 'wp.list.ui_state.v1';
const PAGE_LIMIT = 200;
const MIN_COLUMN_WIDTH = 320;

const DEFAULT_PERSISTED_STATE: PersistedState = {
  sortKey: 'updated_at',
  sortOrder: 'desc',
  viewMode: 'card',
  generationFilter: 'all',
  searchMode: 'contains',
  searchInput: '',
  appliedSearch: null,
  offset: 0,
  showAllSense: false,
};

const getFallbackColumnCount = (width: number): number => {
  if (width >= 900) return 2;
  return 1;
};

const computeColumnCount = (width: number): number => {
  const count = Math.floor(width / MIN_COLUMN_WIDTH);
  return Math.min(2, Math.max(1, count));
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
  const { settings } = useSettings();
  const {
    apiBase,
    pronunciationEnabled,
    regenerateScope,
    requestTimeoutMs,
    temperature,
    reasoningEffort,
    textVerbosity,
    model,
    userRole,
  } = settings;
  const { setModalOpen } = useModal();
  const confirmDialog = useConfirmDialog();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const [wordPacks, setWordPacks] = useState<WordPackListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const [total, setTotal] = useState(0);
  const persistedState = useMemo(() => loadSessionState<PersistedState>(STORAGE_KEY, DEFAULT_PERSISTED_STATE), []);
  const [offset, setOffset] = useState(() => persistedState.offset);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewWordPackId, setPreviewWordPackId] = useState<string | null>(null);
  const modalFocusRef = useRef<HTMLElement>(null);
  const [sortKey, setSortKey] = useState<SortKey>(persistedState.sortKey);
  const [sortOrder, setSortOrder] = useState<SortOrder>(persistedState.sortOrder);
  const [viewMode, setViewMode] = useState<ViewMode>(persistedState.viewMode);
  const [generationFilter, setGenerationFilter] = useState<GenerationFilter>(persistedState.generationFilter);
  const [searchMode, setSearchMode] = useState<SearchMode>(persistedState.searchMode);
  const [searchInput, setSearchInput] = useState(persistedState.searchInput);
  const [appliedSearch, setAppliedSearch] = useState<{ mode: SearchMode; value: string } | null>(persistedState.appliedSearch);
  const [senseOpenIds, setSenseOpenIds] = useState<Set<string>>(() => new Set());
  const [showAllSense, setShowAllSense] = useState(persistedState.showAllSense);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [generatingIds, setGeneratingIds] = useState<Set<string>>(() => new Set());
  const { run: runAbortable } = useAbortableAsync();
  const aiFeaturesDisabled = userRole === 'viewer';
  const aiUnavailableMessage = '閲覧ユーザーはAI生成機能を利用できません';
  const aiDisabledStyle: React.CSSProperties | undefined = aiFeaturesDisabled
    ? { opacity: 0.5, cursor: 'not-allowed' }
    : undefined;
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);
  // グリッドの可視幅に基づき列数を算出（最大2列）
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

  useEffect(() => {
    const stateToPersist: PersistedState = {
      sortKey,
      sortOrder,
      viewMode,
      generationFilter,
      searchMode,
      searchInput,
      appliedSearch,
      offset,
      showAllSense,
    };
    saveSessionState(STORAGE_KEY, stateToPersist);
  }, [sortKey, sortOrder, viewMode, generationFilter, searchMode, searchInput, appliedSearch, offset, showAllSense]);

  // 一覧の取得は他のフィルタ操作と競合するため、AbortController を共通化して最新の結果のみを反映させる。
  const loadWordPacks = useCallback(
    async (newOffset: number = 0) => {
      setLoading(true);
      setMsg(null);

      try {
        const res = await runAbortable((signal) =>
          fetchJson<WordPackListResponse>(`${apiBase}/word/packs?limit=${PAGE_LIMIT}&offset=${newOffset}`, {
            signal,
          }),
        );
        setWordPacks(
          res.items.map((item) => ({
            ...item,
            checked_only_count: item.checked_only_count ?? 0,
            learned_count: item.learned_count ?? 0,
          })),
        );
        setTotal(res.total);
        setOffset((prev) => (prev === newOffset ? prev : newOffset));
      } catch (e) {
        if (e instanceof AbortError) return;
        const m = e instanceof ApiError ? e.message : 'WordPack一覧の読み込みに失敗しました';
        setMsg({ kind: 'alert', text: m });
      } finally {
        setLoading(false);
      }
    },
    [apiBase, runAbortable],
  );

  const applyStudyProgress = useCallback(
    (payload: { wordPackId: string; checked_only_count: number; learned_count: number }) => {
      if (!payload?.wordPackId) return;
      setWordPacks((prev) =>
        prev.map((wp) =>
          wp.id === payload.wordPackId
            ? { ...wp, checked_only_count: payload.checked_only_count, learned_count: payload.learned_count }
            : wp,
        ),
      );
    },
    [],
  );

  const generateWordPack = useCallback(async (wordPack: WordPackListItem) => {
    if (aiFeaturesDisabled) {
      setMsg({ kind: 'alert', text: aiUnavailableMessage });
      return;
    }
    const id = wordPack.id;
    const lemmaLabel = (wordPack.lemma ?? '').trim() || 'WordPack';
    setGeneratingIds((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    setMsg(null);
    try {
      await regenerateWordPackRequest({
        apiBase,
        wordPackId: id,
        settings: {
          pronunciationEnabled,
          regenerateScope,
          requestTimeoutMs,
          temperature,
          reasoningEffort,
          textVerbosity,
        },
        model,
        lemma: lemmaLabel,
        notify: { add: addNotification, update: updateNotification },
        messages: {
          progress: 'WordPackを生成しています',
          success: '生成が完了しました',
          failure: 'WordPackの生成に失敗しました',
        },
      });
      setMsg({ kind: 'status', text: `【${lemmaLabel}】の例文生成が完了しました` });
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'WordPackの生成に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setGeneratingIds((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, [
    addNotification,
    apiBase,
    model,
    pronunciationEnabled,
    regenerateScope,
    requestTimeoutMs,
    temperature,
    textVerbosity,
    reasoningEffort,
    updateNotification,
    aiFeaturesDisabled,
  ]);

  const deleteWordPack = useCallback(async (wordPack: WordPackListItem) => {
    const targetLabel = wordPack.lemma?.trim() || 'WordPack';
    const confirmed = await confirmDialog(targetLabel);
    if (!confirmed) return;

    setLoading(true);
    setMsg(null);

    try {
      await fetchJson(`${apiBase}/word/packs/${wordPack.id}`, {
        method: 'DELETE',
      });
      setMsg({ kind: 'status', text: 'WordPackを削除しました' });
      await loadWordPacks(offset);
      setSelectedIds((prev) => (prev.has(wordPack.id) ? toggleSetValue(prev, wordPack.id) : prev));
    } catch (e) {
      const m = e instanceof ApiError ? e.message : 'WordPackの削除に失敗しました';
      setMsg({ kind: 'alert', text: m });
    } finally {
      setLoading(false);
    }
  }, [apiBase, confirmDialog, loadWordPacks, offset]);

  useEffect(() => {
    loadWordPacks();
  }, [loadWordPacks]);

  useEffect(() => {
    const onUpdated = () => { loadWordPacks(offset); };
    try { window.addEventListener('wordpack:updated', onUpdated as EventListener); } catch {}
    return () => {
      try { window.removeEventListener('wordpack:updated', onUpdated as EventListener); } catch {}
    };
  }, [loadWordPacks, offset]);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ wordPackId?: string; checked_only_count?: number; learned_count?: number }>).detail;
      if (!detail || typeof detail !== 'object' || !detail.wordPackId) return;
      applyStudyProgress({
        wordPackId: detail.wordPackId,
        checked_only_count: typeof detail.checked_only_count === 'number' ? detail.checked_only_count : 0,
        learned_count: typeof detail.learned_count === 'number' ? detail.learned_count : 0,
      });
    };
    try { window.addEventListener('wordpack:study-progress', handler as EventListener); } catch {}
    return () => {
      try { window.removeEventListener('wordpack:study-progress', handler as EventListener); } catch {}
    };
  }, [applyStudyProgress]);

  useEffect(() => {
    setSenseOpenIds((prev) => {
      if (prev.size === 0) return prev;
      const next = retainSetValues(prev, wordPacks.map((wp) => wp.id));
      return next.size === prev.size ? prev : next;
    });
  }, [wordPacks]);

  useEffect(() => {
    setSelectedIds((prev) => {
      if (prev.size === 0) return prev;
      const next = retainSetValues(prev, wordPacks.map((wp) => wp.id));
      return next.size === prev.size ? prev : next;
    });
  }, [wordPacks]);

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

  const visibleWordPackIds = useMemo(() => sortedWordPacks.map((wp) => wp.id), [sortedWordPacks]);
  const selectedCount = selectedIds.size;
  const visibleSelectedCount = useMemo(
    () => sortedWordPacks.reduce((sum, wp) => (selectedIds.has(wp.id) ? sum + 1 : sum), 0),
    [sortedWordPacks, selectedIds]
  );
  const allVisibleSelected = sortedWordPacks.length > 0 && visibleSelectedCount === sortedWordPacks.length;

  const toggleVisibleSelection = useCallback(() => {
    setSelectedIds((prev) => assignSetValues(prev, visibleWordPackIds, !allVisibleSelected));
  }, [allVisibleSelected, visibleWordPackIds]);

  const deleteSelectedWordPacks = useCallback(async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    const confirmed = await confirmDialog(`選択中のWordPack（${ids.length}件）`);
    if (!confirmed) return;

    setLoading(true);
    setMsg(null);
    let deleted = 0;
    let failure: string | null = null;
    try {
      for (const id of ids) {
        try {
          await fetchJson(`${apiBase}/word/packs/${id}`, { method: 'DELETE' });
          deleted += 1;
        } catch (error) {
          const err = error instanceof ApiError ? error.message : 'WordPackの削除に失敗しました';
          failure = err;
          break;
        }
      }
      if (deleted > 0) {
        await loadWordPacks(offset);
        clearSelection();
      }
      if (failure) {
        const text = deleted > 0
          ? `WordPackを${deleted}件削除しましたが一部失敗しました: ${failure}`
          : `WordPackの削除に失敗しました: ${failure}`;
        setMsg({ kind: 'alert', text });
      } else if (deleted > 0) {
        setMsg({ kind: 'status', text: `WordPackを${deleted}件削除しました` });
      } else {
        setMsg({ kind: 'alert', text: '削除対象がありません' });
      }
    } finally {
      setLoading(false);
    }
  }, [selectedIds, confirmDialog, apiBase, loadWordPacks, offset, clearSelection]);

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

  const toggleSenseOpen = useCallback((id: string) => {
    setSenseOpenIds((prev) => toggleSetValue(prev, id));
  }, []);

  const toggleAllSense = useCallback(() => {
    setShowAllSense((prev) => {
      const next = !prev;
      setSenseOpenIds(next ? new Set(wordPacks.map((wp) => wp.id)) : new Set());
      return next;
    });
  }, [wordPacks]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => toggleSetValue(prev, id));
  }, []);

  useEffect(() => {
    if (showAllSense) {
      setSenseOpenIds(new Set(wordPacks.map((wp) => wp.id)));
    }
  }, [showAllSense, wordPacks]);

  const resolveSenseTitle = useCallback((title?: string) => {
    const trimmed = (title ?? '').trim();
    return trimmed || '語義タイトル未設定';
  }, []);

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
        .wp-card { border: 1px solid #ddd; border-radius: 5px; padding: 0.2rem; background:rgb(173, 159, 211); box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor: pointer; }
        .wp-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem; gap: 0.5rem; }
        .wp-card-actions { display: grid; grid-template-rows: auto auto; gap: 0.15rem; margin-left: auto; }
        .wp-card-actions-upper { display: flex; gap: 0.15rem; align-items: center; }
        .wp-card-actions-lower { display: flex; gap: 0.15rem; align-items: center; justify-content: flex-end; }
        .wp-card-tts-btn { font-size: 0.55em; padding: 0.1rem 0.4rem; border-radius: 4px; }
        .wp-card-title { font-size: 0.8em; font-weight: bold; color: #333; margin: 0; }
        .wp-card-meta { font-size: 0.50em; color: #666; margin: 0.25rem 0; }
        .wp-progress-badges { display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.35rem; }
        .wp-progress-badge { display: inline-flex; align-items: center; gap: 0.2rem; padding: 0.15rem 0.45rem; border-radius: 999px; font-size: 0.65em; font-weight: bold; border: 1px solid transparent; }
        .wp-progress-badge.learned { background: #e8f5e9; border-color: #81c784; color: #1b5e20; }
        .wp-progress-badge.checked { background: #fff3e0; border-color: #ffcc80; color: #ef6c00; }
        .wp-progress-badge.small { font-size: 0.55em; padding: 0.1rem 0.35rem; }
        .wp-index-progress { display: inline-flex; gap: 0.25rem; align-items: center; }
        .wp-card-header-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
        .wp-sense-btn { font-size: 0.55em; padding: 0.1rem 0.4rem; border-radius: 4px; border: 1px solid #5c6bc0; background: #f5f7ff; color: #3f51b5; cursor: pointer; }
        .wp-sense-btn[aria-pressed="true"] { background: #e8eaf6; border-color: #3f51b5; color: #283593; }
        .wp-generate-btn { font-size: 0.55em; padding: 0.1rem 0.4rem; border-radius: 4px; border: 1px solid #2e7d32; background: #e8f5e9; color: #1b5e20; cursor: pointer; }
        .wp-generate-btn:hover:not(:disabled) { background: #d0f0d5; }
        .wp-generate-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .wp-card-sense-title { margin: 0.35rem 0 0.2rem; font-size: 0.70em; color: #2f2f2f; background: rgba(255,255,255,0.86); padding: 0.25rem 0.35rem; border-left: 3px solid #5c6bc0; border-radius: 4px; line-height: 1.4; }
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
        .wp-index-title-row { display: flex; align-items: baseline; gap: 0.4rem; flex: 1; min-width: 0; }
        .wp-index-actions { margin-left: auto; display: flex; gap: 0.25rem; align-items: center; }
        .wp-index-tts-btn { font-size: 0.55em; padding: 0.05rem 0.3rem; border-radius: 4px; }
        .wp-index-title { font-size: 0.75em; font-weight: bold; color:rgb(233, 233, 233); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .wp-index-sense { font-size: 0.55em; color: #212121; background: rgba(255,255,255,0.85); padding: 0.05rem 0.35rem; border-radius: 4px; max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .wp-index-meta { font-size: 0.10em; color: #666; }
        .wp-selection-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; font-size: 0.85em; }
        .wp-selection-bar button { padding: 0.25rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; }
        .wp-selection-bar button:disabled { opacity: 0.6; cursor: not-allowed; }
        .wp-select-checkbox { display: inline-flex; align-items: center; justify-content: center; }
        .wp-select-checkbox input { width: 1rem; height: 1rem; cursor: pointer; }
        @media (max-width: 640px) { 
          .wp-list-grid { grid-template-columns: 1fr; }
          .wp-card-header { flex-direction: column; align-items: flex-start; }
          .wp-card-actions { margin-left: 0; margin-top: 0.3rem; }
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
        {aiFeaturesDisabled && (
          <p
            style={{
              margin: '0 0 0.75rem',
              padding: '0.5rem',
              borderRadius: 6,
              background: 'var(--color-neutral-surface)',
              color: 'var(--color-muted)',
              fontSize: '0.9em',
            }}
          >
            閲覧ユーザーは生成系操作が無効化されています
          </p>
        )}

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

        <div className="wp-selection-bar" role="group" aria-label="WordPack選択操作">
          <span>選択中: {selectedCount}件</span>
          <button type="button" onClick={toggleVisibleSelection} disabled={sortedWordPacks.length === 0}>
            {allVisibleSelected ? '表示中を選択解除' : '表示中を全選択'}
          </button>
          <button type="button" onClick={clearSelection} disabled={selectedCount === 0}>
            全選択解除
          </button>
          <button
            type="button"
            onClick={deleteSelectedWordPacks}
            disabled={selectedCount === 0 || loading}
          >選択したWordPackを削除</button>
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
          filtersLeft={(
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', marginLeft: '0.5rem' }}>
              <input
                type="checkbox"
                role="switch"
                aria-label="語義一括表示"
                checked={showAllSense}
                onChange={toggleAllSense}
              />
              語義一括表示
            </label>
          )}
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
                      <label
                        className="wp-select-checkbox"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.has(wp.id)}
                          onChange={() => toggleSelect(wp.id)}
                          aria-label={`WordPack ${wp.lemma} を選択`}
                        />
                      </label>
                      <div className="wp-card-header-main">
                        <h3 className="wp-card-title">{wp.lemma}</h3>
                      </div>
                      <div className="wp-card-actions" onClick={(e) => e.stopPropagation()}>
                        <div className="wp-card-actions-upper" role="group" aria-label="カード操作 上段">
                          <TTSButton text={wp.lemma} className="wp-card-tts-btn" />
                          <DeleteButton
                            onClick={(e) => { e.stopPropagation(); deleteWordPack(wp); }}
                            disabled={loading}
                          />
                        </div>
                        <div className="wp-card-actions-lower" role="group" aria-label="カード操作 下段">
                          {wp.is_empty && (
                            <button
                              type="button"
                              className="wp-generate-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                generateWordPack(wp);
                              }}
                              disabled={loading || generatingIds.has(wp.id) || aiFeaturesDisabled}
                              title={aiFeaturesDisabled ? aiUnavailableMessage : undefined}
                              style={aiDisabledStyle}
                            >生成</button>
                          )}
                          <button
                            type="button"
                            className="wp-sense-btn"
                            aria-pressed={showAllSense || senseOpenIds.has(wp.id)}
                            disabled={showAllSense}
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleSenseOpen(wp.id);
                            }}
                          >語義</button>
                        </div>
                      </div>
                    </div>
                    {(showAllSense || senseOpenIds.has(wp.id)) && (
                      <div className="wp-card-sense-title" data-testid="wp-card-sense-title">
                        {resolveSenseTitle(wp.sense_title)}
                      </div>
                    )}
                    <div className="wp-card-meta">
                      <div>作成: {formatDate(wp.created_at)} / 更新: {formatDate(wp.updated_at)}</div>
                      <div className="wp-progress-badges" aria-label="学習状況">
                        <span className="wp-progress-badge learned">学 {wp.learned_count}</span>
                        <span className="wp-progress-badge checked">確 {wp.checked_only_count}</span>
                      </div>
                      {wp.is_empty ? (
                        <div style={{ marginTop: '0.3rem', fontSize: '0.7em' }}>
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
                    <label className="wp-select-checkbox" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(wp.id)}
                        onChange={() => toggleSelect(wp.id)}
                        aria-label={`WordPack ${wp.lemma} を選択`}
                      />
                    </label>
                    <div className="wp-index-title-row" data-testid="wp-index-title-row">
                      <span className="wp-index-title">{wp.lemma}</span>
                      {(showAllSense || senseOpenIds.has(wp.id)) && (
                        <span className="wp-index-sense">{resolveSenseTitle(wp.sense_title)}</span>
                      )}
                      <span className="wp-index-meta">{wp.is_empty ? ' / 未' : ` / 例文: ${wp.totalExamples}件`}</span>
                      <span className="wp-index-progress" aria-label="学習状況">
                        <span className="wp-progress-badge small learned">学 {wp.learned_count}</span>
                        <span className="wp-progress-badge small checked">確 {wp.checked_only_count}</span>
                      </span>
                    </div>
                    <div className="wp-index-actions" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="wp-sense-btn"
                        aria-pressed={showAllSense || senseOpenIds.has(wp.id)}
                        disabled={showAllSense}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSenseOpen(wp.id);
                        }}
                      >語義</button>
                      {wp.is_empty && (
                        <button
                          type="button"
                          className="wp-generate-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            generateWordPack(wp);
                          }}
                          disabled={loading || generatingIds.has(wp.id) || aiFeaturesDisabled}
                          title={aiFeaturesDisabled ? aiUnavailableMessage : undefined}
                          style={aiDisabledStyle}
                        >生成</button>
                      )}
                      <TTSButton text={wp.lemma} className="wp-index-tts-btn" />
                      <DeleteButton
                        onClick={(e) => { e.stopPropagation(); deleteWordPack(wp); }}
                        disabled={loading}
                      />
                    </div>
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
              onStudyProgressRecorded={applyStudyProgress}
            />
          </div>
        ) : null}
      </Modal>
    </section>
  );
};
