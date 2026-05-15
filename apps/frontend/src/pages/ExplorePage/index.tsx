import React, { useState } from 'react';
import { Badge, Button, SearchBox, SegmentedControl } from '../../shared/ui';

type ExploreMode = 'collocations' | 'contrast' | 'article-links' | 'unknown';

const relationNodes = [
  { lemma: 'robust', className: 'center', status: '中心ノード' },
  { lemma: 'fallback', className: 'purple', status: 'existing' },
  { lemma: 'parser', className: 'green', status: 'existing' },
  { lemma: 'resilient', className: 'yellow', status: 'related' },
  { lemma: 'brittle', className: 'rose', status: 'contrast' },
  { lemma: 'stale', className: 'empty', status: 'empty' },
];

export const ExplorePage: React.FC = () => {
  const [mode, setMode] = useState<ExploreMode>('collocations');
  const [selected, setSelected] = useState('robust');
  return (
    <div className="dictionary-main">
      <div className="dictionary-page-heading">
        <div className="dictionary-page-title">
          <h2>Explore</h2>
          <p>関連語、共起、対比、未生成語へ自由に脱線する。</p>
        </div>
        <div className="dictionary-top-actions">
          <SearchBox label="探索する lemma を検索" placeholder="Search lemma..." />
        </div>
      </div>
      <section className="dictionary-section explore-browser">
        <div className="dictionary-section-header">
          <SegmentedControl<ExploreMode>
            label="Explore relation mode"
            value={mode}
            onChange={setMode}
            options={[
              { value: 'collocations', label: 'collocations' },
              { value: 'contrast', label: 'contrast' },
              { value: 'article-links', label: 'article links' },
              { value: 'unknown', label: 'unknown lemmas' },
            ]}
          />
          <Badge variant="accent">{selected}</Badge>
        </div>
        <div className="explore-layout">
          <div className="explore-graph" aria-label="関連語ブラウザ">
            {relationNodes.map((node) => (
              <button
                key={node.lemma}
                type="button"
                className={`explore-node ${node.className}`}
                aria-pressed={selected === node.lemma}
                onClick={() => setSelected(node.lemma)}
              >
                <strong>{node.lemma}</strong>
                <span>{node.status}</span>
              </button>
            ))}
          </div>
          <aside className="explore-side">
            <h3>{selected}</h3>
            <p>中心ノード。ここから関連へ飛ぶ。</p>
            <h4>Collocations</h4>
            <ul>
              <li>robust fallback</li>
              <li>robust parser</li>
              <li>robust evidence</li>
            </ul>
            <h4>Contrast</h4>
            <ul>
              <li>brittle</li>
              <li>fragile</li>
              <li>ad hoc</li>
            </ul>
            <Button variant="subtle">Side Peekで開く</Button>
          </aside>
        </div>
      </section>
    </div>
  );
};

