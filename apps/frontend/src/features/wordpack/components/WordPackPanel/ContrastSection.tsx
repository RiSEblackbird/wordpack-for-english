import React from 'react';
import type { WordPack } from '../../../../hooks/useWordPack';

interface ContrastSectionProps {
  contrast: WordPack['contrast'];
  onSelectLemma: (lemma: string) => void;
  sectionId?: string;
}

export const ContrastSection: React.FC<ContrastSectionProps> = ({
  contrast,
  onSelectLemma,
  sectionId = 'contrast',
}) => (
  <section id={sectionId} className="wp-section">
    <h3>対比</h3>
    {contrast?.length ? (
      <ul>
        {contrast.map((item, index) => (
          <li key={`${item.with}-${index}`}>
            <a
              href="#"
              onClick={(event) => {
                event.preventDefault();
                onSelectLemma(item.with);
              }}
              className="mono"
            >
              {item.with}
            </a>
            {' — '}
            {item.diff_ja}
          </li>
        ))}
      </ul>
    ) : (
      <p>なし</p>
    )}
  </section>
);
