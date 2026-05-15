import React, { useMemo, useState } from 'react';
import { Badge, Button, Input, SearchBox, Tag } from '../../shared/ui';

interface ShelfDraft {
  name: string;
  description: string;
}

const defaultShelves = [
  { name: 'LLMまわり', description: 'prompt, context, latent, entail', count: 32, color: 'sky' },
  { name: '仕事で使う', description: 'friction, robust, alignment', count: 18, color: 'yellow' },
  { name: '似ていて混乱', description: 'brittle / fragile / delicate', count: 11, color: 'rose' },
  { name: '文章から拾った', description: 'API reliability notes', count: 24, color: 'green' },
  { name: '音が好き', description: 'curious, mellow, crisp', count: 7, color: 'purple' },
  { name: 'まだ掴めてない', description: 'granular, elusive', count: 9, color: 'gold' },
];

export const ShelvesPage: React.FC = () => {
  const [draft, setDraft] = useState<ShelfDraft>({ name: '', description: '' });
  const [customShelves, setCustomShelves] = useState<typeof defaultShelves>(() => {
    try {
      const raw = localStorage.getItem('wp.localShelves.v1');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const shelves = useMemo(() => [...defaultShelves, ...customShelves], [customShelves]);
  const addShelf = () => {
    const name = draft.name.trim();
    if (!name) return;
    const next = [...customShelves, { name, description: draft.description.trim() || '自由分類', count: 0, color: 'sky' }];
    setCustomShelves(next);
    setDraft({ name: '', description: '' });
    try { localStorage.setItem('wp.localShelves.v1', JSON.stringify(next)); } catch {}
  };
  return (
    <div className="dictionary-main">
      <div className="dictionary-page-heading">
        <div className="dictionary-page-title">
          <h2>Shelves</h2>
          <p>単元ではなく、自分で作る棚・タグ・ブックマーク。</p>
        </div>
        <div className="dictionary-top-actions">
          <SearchBox label="棚、タグ、メモを検索" placeholder="Search shelves, tags, notes" shortcut="⌘K" />
        </div>
      </div>
      <section className="dictionary-section shelf-create">
        <div className="dictionary-section-header">
          <div>
            <h3>棚を作る</h3>
            <p>ローカルの下書き棚です。WordPack API 追加までは分類の入口として扱います。</p>
          </div>
        </div>
        <div className="shelf-create-row">
          <Input
            aria-label="棚名"
            placeholder="棚名"
            value={draft.name}
            onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))}
          />
          <Input
            aria-label="棚の説明"
            placeholder="説明や語のメモ"
            value={draft.description}
            onChange={(event) => setDraft((prev) => ({ ...prev, description: event.target.value }))}
          />
          <Button onClick={addShelf}>追加</Button>
        </div>
      </section>
      <section className="shelf-grid" aria-label="棚一覧">
        {shelves.map((shelf) => (
          <article key={`${shelf.name}-${shelf.description}`} className={`shelf-card ${shelf.color}`}>
            <h3>{shelf.name}</h3>
            <p>{shelf.description}</p>
            <div className="shelf-card-footer">
              <span>{shelf.count} entries</span>
              <Button variant="subtle">Open →</Button>
            </div>
          </article>
        ))}
      </section>
      <section className="dictionary-section">
        <div className="dictionary-section-header">
          <div>
            <h3>Tag cloud</h3>
          </div>
        </div>
        <div className="dictionary-chip-list">
          {['nuance', 'dev', 'business', 'formal', 'article-source', 'audio-good', 'compare', 'empty', 'guest-public', 'note'].map((tag) => (
            <Tag key={tag}>{tag}</Tag>
          ))}
        </div>
      </section>
    </div>
  );
};

