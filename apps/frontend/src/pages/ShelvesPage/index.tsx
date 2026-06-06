import React, { useEffect, useMemo, useState } from 'react';
import { AppRightRail, RailCard } from '../../components/AppRightRail';
import { WordPackPreviewModal } from '../../components/WordPackPreviewModal';
import { useWordPackList } from '../../features/wordpack/hooks/useWordPackList';
import { Badge, Button, EmptyState, SearchBox } from '../../shared/ui';
import { ShelfWordPackList } from './ShelfWordPackList';
import { useSmartShelves } from './useSmartShelves';

export const ShelvesPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [activeShelfId, setActiveShelfId] = useState('recent');
  const [previewWordPackId, setPreviewWordPackId] = useState<string | null>(
    null,
  );
  const { applyStudyProgress, loading, message, reload, wordPacks } =
    useWordPackList();
  const shelves = useSmartShelves(wordPacks);
  const normalizedQuery = query.trim().toLowerCase();
  const visibleShelves = useMemo(() => {
    if (!normalizedQuery) return shelves;
    return shelves.filter(
      (shelf) =>
        shelf.title.toLowerCase().includes(normalizedQuery) ||
        shelf.description.toLowerCase().includes(normalizedQuery) ||
        shelf.items.some(
          (wordPack) =>
            wordPack.lemma.toLowerCase().includes(normalizedQuery) ||
            (wordPack.sense_title ?? '')
              .toLowerCase()
              .includes(normalizedQuery),
        ),
    );
  }, [normalizedQuery, shelves]);
  const activeShelf =
    shelves.find((shelf) => shelf.id === activeShelfId) ?? shelves[0];
  const activeItems = useMemo(() => {
    if (!activeShelf) return [];
    if (!normalizedQuery) return activeShelf.items;
    return activeShelf.items.filter(
      (wordPack) =>
        wordPack.lemma.toLowerCase().includes(normalizedQuery) ||
        (wordPack.sense_title ?? '').toLowerCase().includes(normalizedQuery),
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
      <div className="dictionary-workspace">
        <div className="dictionary-primary">
          <div className="dictionary-page-heading">
            <div className="dictionary-page-title">
              <h2>Shelves</h2>
              <p>
                保存済みWordPackを条件別に自動分類し、復習する束を選びます。
              </p>
            </div>
            <div className="dictionary-top-actions">
              <SearchBox
                label="棚とWordPackを検索"
                placeholder="棚名、見出し語、語義で検索"
                shortcut="⌘K"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <Button
                variant="subtle"
                onClick={() => {
                  void reload();
                }}
                disabled={loading}
              >
                {loading ? '更新中' : '更新'}
              </Button>
            </div>
          </div>
          <section className="dictionary-section">
            <div className="dictionary-section-header">
              <div>
                <h3>Smart Shelves</h3>
                <p>
                  一覧レスポンスだけを使い、保存や更新を行わずに自動分類します。
                </p>
              </div>
              <Badge variant="accent">{wordPacks.length} entries</Badge>
            </div>
            {message ? (
              <div role="alert" className="dictionary-empty compact">
                {message.text}
              </div>
            ) : null}
            {!message && visibleShelves.length === 0 ? (
              <EmptyState>
                表示できる棚がありません。検索語を短くするか、一覧を更新してください。
              </EmptyState>
            ) : null}
            <div className="shelf-grid" aria-label="棚一覧">
              {visibleShelves.map((shelf) => (
                <article
                  key={shelf.id}
                  className={`shelf-card ${shelf.accent}`}
                  aria-current={activeShelfId === shelf.id ? 'true' : undefined}
                >
                  <h3>{shelf.title}</h3>
                  <p>{shelf.description}</p>
                  <div className="shelf-card-footer">
                    <span>{shelf.items.length} entries</span>
                    <Button
                      variant="subtle"
                      onClick={() => setActiveShelfId(shelf.id)}
                    >
                      開く
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          </section>
          <section className="dictionary-section">
            <div className="dictionary-section-header">
              <div>
                <h3>{activeShelf?.title ?? '選択中の棚'}</h3>
                <p>
                  {activeShelf?.description ??
                    '棚を選ぶとWordPackを表示します。'}
                </p>
              </div>
              {activeShelf ? (
                <Badge variant="accent">{activeItems.length} shown</Badge>
              ) : null}
            </div>
            {activeShelf ? (
              <ShelfWordPackList
                items={activeItems}
                onOpenPreview={setPreviewWordPackId}
              />
            ) : (
              <EmptyState>棚データを読み込んでいます。</EmptyState>
            )}
          </section>
        </div>
        <AppRightRail>
          <RailCard title="現在の棚" badge={activeShelf?.title ?? '未選択'}>
            <div className="dictionary-rail-metrics" aria-label="棚の集計">
              <span>
                <strong>{wordPacks.length}</strong>全体
              </span>
              <span>
                <strong>{activeItems.length}</strong>表示中
              </span>
            </div>
            <p className="dictionary-rail-copy">
              棚は自動分類です。ここでWordPackを開いても、生成状況は同じキューで確認できます。
            </p>
          </RailCard>
        </AppRightRail>
      </div>
      <WordPackPreviewModal
        isOpen={Boolean(previewWordPackId)}
        onClose={() => setPreviewWordPackId(null)}
        wordPackId={previewWordPackId}
        wordPacks={wordPacks}
        onWordPackUpdated={() => {
          void reload();
        }}
        onStudyProgressRecorded={applyStudyProgress}
      />
    </div>
  );
};
