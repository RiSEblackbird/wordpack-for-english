import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { highlightLemma } from './highlight';

describe('highlightLemma', () => {
  it('wraps lemma occurrences with a span (case-insensitive, word boundary)', () => {
    const lemma = 'delta';
    const text = 'Delta paths may DELTA at the main square.';
    render(<p>{highlightLemma(text, lemma)}</p>);
    const spans = screen.getAllByText(/delta/i, { selector: 'span.lemma-highlight' });
    expect(spans.length).toBe(2);
    expect(spans[0]).toHaveClass('lemma-highlight');
  });

  it('does not highlight partial matches', () => {
    const lemma = 'delta';
    const text = 'deltaX and Xdelta are not full-word matches.';
    render(<p>{highlightLemma(text, lemma)}</p>);
    const highlighted = document.querySelectorAll('span.lemma-highlight');
    expect(highlighted.length).toBe(0);
  });

  it('highlights lemmas with trailing symbols like C++', () => {
    const lemma = 'C++';
    const text = 'I love C++ and also enjoy C but not Cplusplus.';
    render(<p>{highlightLemma(text, lemma)}</p>);
    const spans = screen.getAllByText('C++', { selector: 'span.lemma-highlight' });
    expect(spans.length).toBe(1);
  });

  it('highlights lemmas with trailing symbols like C#', () => {
    const lemma = 'C#';
    const text = 'Learning C# is fun. Csharp is different from C#.';
    render(<p>{highlightLemma(text, lemma)}</p>);
    const spans = screen.getAllByText('C#', { selector: 'span.lemma-highlight' });
    expect(spans.length).toBe(2);
  });
});


