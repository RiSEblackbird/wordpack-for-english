import React, { useEffect, useMemo, useState } from 'react';
import { WordPackPreviewModal } from '../../components/WordPackPreviewModal';
import { useWordPackList } from '../../features/wordpack/hooks/useWordPackList';
import { Badge, Button, EmptyState, SearchBox } from '../../shared/ui';
import { ShelfWordPackList } from './ShelfWordPackList';
import { useSmartShelves } from './useSmartShelves';

export const ShelvesPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [activeShelfId, setActiveShelfId] = useState('recent');
  const [previewWordPackId, setPreviewWordPackId] = useState<string | null>(null);
  const { applyStudyProgress, loading, message, reload, wordPacks } = useWordPackList();
  const shelves = useSmartShelves(wordPacks);
  const normalizedQuery = query.trim().toLowerCase();
  const visibleShelves = useMemo(() => {
    if (!normalizedQuery) return shelves;
    return shelves.filter((shelf) => (
      shelf.title.toLowerCase().includes(normalizedQuery) ||
      shelf.description.toLowerCase().includes(normalizedQuery) ||
      shelf.items.some((wordPack) =>
        wordPack.lemma.toLowerCase().includes(normalizedQuery) ||
        (wordPack.sense_title ?? '').toLowerCase().includes(normalizedQuery)
      )
    ));
  }, [normalizedQuery, shelves]);
  const activeShelf = shelves.find((shelf) => shelf.id === activeShelfId) ?? shelves[0];
  const activeItems = useMemo(() => {
    if (!activeShelf) return [];
    if (!normalizedQuery) return activeShelf.items;
    return activeShelf.items.filter((wordPack) =>
      wordPack.lemma.toLowerCase().includes(normalizedQuery) ||
      (wordPack.sense_title ?? '').toLowerCase().includes(normalizedQuery)
    );
  }, [activeShelf, normalizedQuery]);

  useEffect(() => {
    if (shelves.length === 0) return;
    if (!shelves.some((shelf) => shelf.id === activeShelfId)) {
      setActiveShelfId(shelves[0].id);
    }
  }, [activeShelfId, shelves]);

  return (
    <div className="dictionary-main">
      <div className="dictionary-page-heading">
        <div className="dictionary-page-title">
          <h2>Shelves</h2>
          <p>保存済みWordPackを条件別に自動分類して眺める。</p>
        </div>
        <div className="dictionary-top-actions">
          <SearchBox
            label="棚とWordPackを検索"
            placeholder="Search shelves and entries"
            shortcut="⌘K"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Button variant="subtle" onClick={() => { void reload(); }} disabled={loading}>
            更新
          </Button>
        </div>
      </div>
      <section className="dictionary-section">
        <div className="dictionary-section-header">
          <div>
            <h3>Smart Shelves</h3>
            <p>一覧レスポンスだけを使い、保存や更新を行わずに自動分類します。</p>
          </div>
          <Badge variant="accent">{wordPacks.length} entries</Badge>
        </div>
        {message ? <div role="alert" className="dictionary-empty compact">{message.text}</div> : null}
        {!message && visibleShelves.length === 0 ? <EmptyState>表示できる棚がありません。</EmptyState> : null}
        <div className="shelf-grid" aria-label="棚一覧">
          {visibleShelves.map((shelf) => (
            <article key={shelf.id} className={`shelf-card ${shelf.accent}`} aria-current={activeShelfId === shelf.id ? 'true' : undefined}>
              <h3>{shelf.title}</h3>
              <p>{shelf.description}</p>
              <div className="shelf-card-footer">
                <span>{shelf.items.length} entries</span>
                <Button variant="subtle" onClick={() => setActiveShelfId(shelf.id)}>Open</Button>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="dictionary-section">
        <div className="dictionary-section-header">
          <div>
            <h3>{activeShelf?.title ?? '選択中の棚'}</h3>
            <p>{activeShelf?.description ?? '棚を選ぶとWordPackを表示します。'}</p>
          </div>
          {activeShelf ? <Badge variant="accent">{activeItems.length} shown</Badge> : null}
        </div>
        {activeShelf ? (
          <ShelfWordPackList items={activeItems} onOpenPreview={setPreviewWordPackId} />
        ) : (
          <EmptyState>棚データを読み込んでいます。</EmptyState>
        )}
      </section>
      <WordPackPreviewModal
        isOpen={Boolean(previewWordPackId)}
        onClose={() => setPreviewWordPackId(null)}
        wordPackId={previewWordPackId}
        wordPacks={wordPacks}
        onWordPackUpdated={() => { void reload(); }}
        onStudyProgressRecorded={applyStudyProgress}
      />
    </div>
  );
};
