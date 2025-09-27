import React from 'react';

function escapeRegExp(input: string): string {
  return input.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

interface HighlightOptions {
  spanProps?: React.HTMLAttributes<HTMLSpanElement>;
}

export function highlightLemma(text: string, lemma: string, options: HighlightOptions = {}): React.ReactNode {
  if (!text || !lemma) return text;
  // Allow flexible whitespace for multi-word lemmas
  const tokens = lemma.trim().split(/\s+/).map(escapeRegExp);
  const pattern = tokens.join('\\s+');
  const re = new RegExp(pattern, 'gi');
  const isWordChar = (ch: string) => /[A-Za-z0-9_]/.test(ch);
  const { spanProps } = options;
  const { className: customClassName, ...restSpanProps } = spanProps ?? {};
  const combinedClassName = ['lemma-highlight', customClassName].filter(Boolean).join(' ');

  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let anyHighlighted = false;
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    const before = start > 0 ? text[start - 1] : '';
    const after = end < text.length ? text[end] : '';
    const isStartBoundary = before === '' || !isWordChar(before);
    const isEndBoundary = after === '' || !isWordChar(after);
    if (isStartBoundary && isEndBoundary) {
      if (lastIndex < start) nodes.push(text.slice(lastIndex, start));
      nodes.push(
        <span key={nodes.length} className={combinedClassName} {...restSpanProps}>
          {match[0]}
        </span>
      );
      anyHighlighted = true;
      lastIndex = end;
    }
  }
  if (!anyHighlighted) return text;
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}


