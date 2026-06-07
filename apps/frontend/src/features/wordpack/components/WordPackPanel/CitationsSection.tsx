import React from 'react';
import type { WordPack } from '../../../../hooks/useWordPack';

interface CitationsSectionProps {
  citations: WordPack['citations'];
  sectionId?: string;
}

export const CitationsSection: React.FC<CitationsSectionProps> = ({ citations, sectionId = 'citations' }) => (
  <section id={sectionId} className="wp-section">
    <h3>引用</h3>
    {citations?.length ? (
      <ol>
        {citations.map((citation, index) => (
          <li key={`${citation.text}-${index}`}>
            <div>{citation.text}</div>
            {citation.meta ? (
              <pre className="mono wp-citation-meta">{JSON.stringify(citation.meta, null, 2)}</pre>
            ) : null}
          </li>
        ))}
      </ol>
    ) : (
      <p>なし</p>
    )}
  </section>
);
