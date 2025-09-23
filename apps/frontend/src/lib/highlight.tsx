import React from 'react';

function escapeRegExp(input: string): string {
  return input.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function highlightLemma(text: string, lemma: string): React.ReactNode {
  if (!text || !lemma) return text;
  const escaped = escapeRegExp(lemma);
  const re = new RegExp(`\\b(${escaped})\\b`, 'gi');
  const parts = text.split(re);
  if (parts.length === 1) return text;
  return parts.map((part, idx) => (idx % 2 === 1
    ? <span key={idx} className="lemma-highlight">{part}</span>
    : part
  ));
}


