import React from 'react';
import type { WordPack } from '../../../../hooks/useWordPack';

interface ConfidenceSectionProps {
  confidence: WordPack['confidence'];
}

export const ConfidenceSection: React.FC<ConfidenceSectionProps> = ({ confidence }) => (
  <section id="confidence" className="wp-section">
    <h3>信頼度</h3>
    <p>{confidence}</p>
  </section>
);
