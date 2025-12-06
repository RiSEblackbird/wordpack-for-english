import React from 'react';
import { Sense } from '../../hooks/useWordPack';

interface SensesSectionProps {
  senses: Sense[];
}

/**
 * 語義一覧を責務として切り出したセクション。
 */
export const SensesSection: React.FC<SensesSectionProps> = ({ senses }) => (
  <section id="senses" className="wp-section">
    <h3>語義</h3>
    {senses?.length ? (
      <ol>
        {senses.map((sense) => (
          <li key={sense.id}>
            <div><strong>{sense.gloss_ja}</strong></div>
            {sense.term_core_ja ? (
              <div style={{ marginTop: 4, fontWeight: 600 }}>{sense.term_core_ja}</div>
            ) : null}
            {sense.term_overview_ja ? (
              <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{sense.term_overview_ja}</div>
            ) : null}
            {sense.definition_ja ? (
              <div style={{ marginTop: 4 }}>{sense.definition_ja}</div>
            ) : null}
            {sense.nuances_ja ? (
              <div style={{ marginTop: 4, color: '#555' }}>{sense.nuances_ja}</div>
            ) : null}
            {sense.patterns?.length ? (
              <div className="mono" style={{ marginTop: 4 }}>{sense.patterns.join(' | ')}</div>
            ) : null}
            {(sense.synonyms && sense.synonyms.length) || (sense.antonyms && sense.antonyms.length) ? (
              <div style={{ marginTop: 4 }}>
                {sense.synonyms?.length ? (
                  <div><span style={{ color: '#555' }}>類義:</span> {sense.synonyms.join(', ')}</div>
                ) : null}
                {sense.antonyms?.length ? (
                  <div><span style={{ color: '#555' }}>反義:</span> {sense.antonyms.join(', ')}</div>
                ) : null}
              </div>
            ) : null}
            {sense.register ? (
              <div style={{ marginTop: 4 }}><span style={{ color: '#555' }}>レジスター:</span> {sense.register}</div>
            ) : null}
            {sense.notes_ja ? (
              <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{sense.notes_ja}</div>
            ) : null}
          </li>
        ))}
      </ol>
    ) : (
      <p>なし</p>
    )}
  </section>
);
