import React, { useMemo, useState } from 'react';
import { WordPackPreviewModal } from '../../components/WordPackPreviewModal';
import { Badge, Button, EmptyState, SearchBox, SegmentedControl } from '../../shared/ui';
import { attachRelationStatus, buildExploreRelations, filterExploreRelations, type ExploreMode, type ExploreRelation } from './exploreRelations';
import { useExploreData } from './useExploreData';

const modeOptions: { value: ExploreMode; label: string }[] = [
  { value: 'related', label: 'Related' },
  { value: 'collocations', label: 'Collocations' },
  { value: 'contrast', label: 'Contrast' },
  { value: 'examples', label: 'Examples' },
  { value: 'unknown', label: 'Empty / Unknown' },
];

const statusLabel = (relation: ExploreRelation): string => {
  if (relation.status === 'existing') return '開く';
  if (relation.status === 'empty') return '空WordPack';
  return '未作成';
};

export const ExplorePage: React.FC = () => {
  const [mode, setMode] = useState<ExploreMode>('related');
  const [previewWordPackId, setPreviewWordPackId] = useState<string | null>(null);
  const {
    applyStudyProgress,
    detailLoading,
    detailMessage,
    filteredWordPacks,
    loading,
    message,
    query,
    reload,
    selectedDetail,
    selectedWordPack,
    selectedWordPackId,
    setQuery,
    setSelectedWordPackId,
    wordPacks,
  } = useExploreData();

  const relations = useMemo(() => {
    if (!selectedDetail) return [];
    return attachRelationStatus(buildExploreRelations(selectedDetail), wordPacks, selectedDetail.lemma);
  }, [selectedDetail, wordPacks]);
  const visibleRelations = useMemo(() => filterExploreRelations(relations, mode), [mode, relations]);

  return (
    <div className="dictionary-main">
      <div className="dictionary-page-heading">
        <div className="dictionary-page-title">
          <h2>Explore</h2>
          <p>保存済みWordPackから、共起・対比・語義・例文のつながりを読む。</p>
        </div>
        <div className="dictionary-top-actions">
          <SearchBox
            label="探索する lemma を検索"
            placeholder="Search lemma..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Button variant="subtle" onClick={() => { void reload(); }} disabled={loading}>
            更新
          </Button>
        </div>
      </div>
      <section className="dictionary-section explore-browser">
        <div className="dictionary-section-header">
          <SegmentedControl<ExploreMode>
            label="Explore relation mode"
            value={mode}
            onChange={setMode}
            options={modeOptions}
          />
          <Badge variant="accent">{selectedWordPack?.lemma ?? '未選択'}</Badge>
        </div>
        <div className="explore-layout">
          <div className="explore-list" aria-label="探索候補">
            {message ? <div role="alert" className="dictionary-empty compact">{message.text}</div> : null}
            {!message && filteredWordPacks.length === 0 ? (
              <EmptyState>一致するWordPackがありません。</EmptyState>
            ) : null}
            {filteredWordPacks.map((wordPack) => (
              <button
                key={wordPack.id}
                type="button"
                className="explore-list-item"
                aria-pressed={selectedWordPackId === wordPack.id}
                onClick={() => setSelectedWordPackId(wordPack.id)}
              >
                <strong>{wordPack.lemma}</strong>
                <span>{wordPack.sense_title || '語義タイトル未設定'}</span>
              </button>
            ))}
          </div>
          <div className="explore-connections" aria-label="接続カード">
            {detailLoading ? <EmptyState>接続を読み込んでいます。</EmptyState> : null}
            {detailMessage ? <div role="alert" className="dictionary-empty">{detailMessage}</div> : null}
            {!detailLoading && !detailMessage && visibleRelations.length === 0 ? (
              <EmptyState>このモードで表示できる接続はまだありません。</EmptyState>
            ) : null}
            {!detailLoading && !detailMessage && visibleRelations.map((relation) => (
              <article key={relation.id} className="explore-connection-card">
                <div>
                  <div className="dictionary-meta-row">
                    <Badge>{relation.source}</Badge>
                    <Badge variant={relation.status === 'existing' ? 'accent' : 'default'}>{relation.status}</Badge>
                  </div>
                  <h3>{relation.label}</h3>
                  {relation.description ? <p>{relation.description}</p> : null}
                </div>
                <Button
                  variant="subtle"
                  disabled={!relation.targetWordPack}
                  onClick={() => {
                    if (relation.targetWordPack) {
                      setPreviewWordPackId(relation.targetWordPack.id);
                    }
                  }}
                >
                  {statusLabel(relation)}
                </Button>
              </article>
            ))}
          </div>
          <aside className="explore-side">
            <h3>{selectedWordPack?.lemma ?? 'No WordPack'}</h3>
            <p>{selectedWordPack?.sense_title || 'WordPackを選ぶと接続を表示します。'}</p>
            <div className="dictionary-chip-list">
              <Badge>{relations.length} connections</Badge>
              <Badge>{relations.filter((relation) => relation.status === 'unknown').length} unknown</Badge>
              {selectedWordPack?.is_empty ? <Badge>empty</Badge> : null}
            </div>
            <Button
              variant="subtle"
              disabled={!selectedWordPackId}
              onClick={() => setPreviewWordPackId(selectedWordPackId)}
            >
              プレビューを開く
            </Button>
          </aside>
        </div>
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
