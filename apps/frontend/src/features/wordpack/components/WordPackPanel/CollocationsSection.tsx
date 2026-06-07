import React from 'react';
import type { WordPack } from '../../../../hooks/useWordPack';

interface CollocationsSectionProps {
  collocations: WordPack['collocations'];
  onSelectLemma: (lemma: string) => void;
  sectionId?: string;
}

const CollocationLinks: React.FC<{
  items: string[] | undefined;
  onSelectLemma: (lemma: string) => void;
}> = ({ items, onSelectLemma }) => {
  if (!items?.length) return <>-</>;
  return (
    <>
      {items.map((text, index) => (
        <React.Fragment key={text}>
          <a
            href="#"
            onClick={(event) => {
              event.preventDefault();
              onSelectLemma(text.split(' ').pop() || text);
            }}
          >
            {text}
          </a>
          {index < items.length - 1 ? ', ' : ''}
        </React.Fragment>
      ))}
    </>
  );
};

export const CollocationsSection: React.FC<CollocationsSectionProps> = ({
  collocations,
  onSelectLemma,
  sectionId = 'collocations',
}) => (
  <section id={sectionId} className="wp-section">
    <h3>共起</h3>
    <div>
      <h4>一般</h4>
      <div className="mono">VO: <CollocationLinks items={collocations?.general?.verb_object} onSelectLemma={onSelectLemma} /></div>
      <div className="mono">Adj+N: <CollocationLinks items={collocations?.general?.adj_noun} onSelectLemma={onSelectLemma} /></div>
      <div className="mono">Prep+N: <CollocationLinks items={collocations?.general?.prep_noun} onSelectLemma={onSelectLemma} /></div>
    </div>
    <div>
      <h4>アカデミック</h4>
      <div className="mono">VO: <CollocationLinks items={collocations?.academic?.verb_object} onSelectLemma={onSelectLemma} /></div>
      <div className="mono">Adj+N: <CollocationLinks items={collocations?.academic?.adj_noun} onSelectLemma={onSelectLemma} /></div>
      <div className="mono">Prep+N: <CollocationLinks items={collocations?.academic?.prep_noun} onSelectLemma={onSelectLemma} /></div>
    </div>
  </section>
);
