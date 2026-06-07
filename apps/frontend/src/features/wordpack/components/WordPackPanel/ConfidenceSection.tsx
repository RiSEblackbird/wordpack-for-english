import React from 'react';
import type { WordPack } from '../../../../hooks/useWordPack';

interface ConfidenceSectionProps {
  confidence: WordPack['confidence'];
  sectionId?: string;
}

export const ConfidenceSection: React.FC<ConfidenceSectionProps> = ({ confidence, sectionId = 'confidence' }) => (
  <section id={sectionId} className="wp-section">
    <h3>信頼度</h3>
    <p>{confidence}</p>
  </section>
);
