import React from 'react';
import { Pronunciation } from '../../hooks/useWordPack';

interface PronunciationSectionProps {
  pronunciation: Pronunciation;
}

/**
 * 発音に関する情報のみを表示する専用セクション。
 */
export const PronunciationSection: React.FC<PronunciationSectionProps> = ({ pronunciation }) => (
  <section id="pronunciation" className="wp-section">
    <h3>発音</h3>
    <div className="kv mono">
      <div>IPA (GA)</div><div>{pronunciation?.ipa_GA ?? '-'}</div>
      <div>IPA (RP)</div><div>{pronunciation?.ipa_RP ?? '-'}</div>
      <div>音節数</div><div>{pronunciation?.syllables ?? '-'}</div>
      <div>強勢インデックス</div><div>{pronunciation?.stress_index ?? '-'}</div>
      <div>リンキング</div><div>{pronunciation?.linking_notes?.join('、') || '-'}</div>
    </div>
  </section>
);
