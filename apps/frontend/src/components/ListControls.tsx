import React from 'react';

type SortOrder = 'asc' | 'desc';

export interface SortOption<T extends string> { value: T; label: string }

interface ListControlsProps<TSortKey extends string> {
  className?: string;
  sortKey: TSortKey;
  sortOptions: Array<SortOption<TSortKey>>;
  onChangeSortKey: (key: TSortKey) => void;
  sortOrder: SortOrder;
  onChangeSortOrder: (order: SortOrder) => void;
  filtersLeft?: React.ReactNode;
  filtersRight?: React.ReactNode;
  searchMode: 'prefix' | 'suffix' | 'contains';
  onChangeSearchMode: (mode: 'prefix' | 'suffix' | 'contains') => void;
  searchInput: string;
  onChangeSearchInput: (value: string) => void;
  onApplySearch: () => void;
}

export function ListControls<TSortKey extends string>(props: ListControlsProps<TSortKey>) {
  const {
    className,
    sortKey,
    sortOptions,
    onChangeSortKey,
    sortOrder,
    onChangeSortOrder,
    filtersLeft,
    filtersRight,
    searchMode,
    onChangeSearchMode,
    searchInput,
    onChangeSearchInput,
    onApplySearch,
  } = props;

  return (
    <div
      className={`wp-sort-controls${className ? ` ${className}` : ''}`}
      style={{ flexWrap: 'wrap' }}
    >
      <label htmlFor="sort-select">並び順:</label>
      <select
        id="sort-select"
        className="wp-sort-select"
        value={sortKey}
        onChange={(e) => onChangeSortKey(e.target.value as TSortKey)}
      >
        {sortOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <button
        className={`wp-sort-button ${sortOrder === 'desc' ? 'active' : ''}`}
        onClick={() => onChangeSortOrder('desc')}
        title="降順"
        type="button"
      >
        ↓
      </button>
      <button
        className={`wp-sort-button ${sortOrder === 'asc' ? 'active' : ''}`}
        onClick={() => onChangeSortOrder('asc')}
        title="昇順"
        type="button"
      >
        ↑
      </button>

      {filtersLeft}

      {filtersRight}

      <label htmlFor="search-mode" style={{ marginLeft: '0.5rem' }}>検索:</label>
      <select
        id="search-mode"
        className="wp-filter-select"
        value={searchMode}
        onChange={(e) => onChangeSearchMode(e.target.value as any)}
        aria-label="検索方法"
      >
        <option value="prefix">前方一致</option>
        <option value="suffix">後方一致</option>
        <option value="contains">部分一致</option>
      </select>
      <input
        type="text"
        className="wp-search-input"
        value={searchInput}
        onChange={(e) => onChangeSearchInput(e.target.value)}
        placeholder="検索する文字列"
        aria-label="検索文字列"
        onKeyDown={(e) => { if (e.key === 'Enter') onApplySearch(); }}
      />
      <button
        type="button"
        className="wp-search-button"
        onClick={onApplySearch}
        title="検索"
      >検索</button>
    </div>
  );
}


