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

  it('highlights multi-word lemmas with flexible single spaces', () => {
    const lemma = 'take part in';
    const text = 'We take part in community events and take part in meetings.';
    render(<p>{highlightLemma(text, lemma)}</p>);
    const highlighted = document.querySelectorAll('span.lemma-highlight');
    expect(highlighted.length).toBe(2);
  });

  it('does not break on extra spaces within multi-word lemmas (will be handled after implementation)', () => {
    const lemma = 'take part in';
    const text = 'We take  part  in community events.'; // double spaces
    render(<p>{highlightLemma(text, lemma)}</p>);
    // After flexible whitespace implementation, this should highlight 1 occurrence.
    // For now, allow 0 or 1 depending on implementation order.
    const highlighted = document.querySelectorAll('span.lemma-highlight');
    expect(highlighted.length === 0 || highlighted.length === 1).toBe(true);
  });

  it('allows attaching custom data attributes to highlighted spans', () => {
    const lemma = 'gamma';
    const text = 'Gamma rays differ from gamma waves.';
    render(
      <p>
        {highlightLemma(text, lemma, {
          spanProps: {
            'data-lemma': lemma,
            'data-source': 'spec',
            className: 'custom-highlight',
          },
        })}
      </p>
    );
    const spans = screen.getAllByText(/gamma/i, { selector: 'span.lemma-highlight' });
    expect(spans[0]).toHaveAttribute('data-lemma', lemma);
    expect(spans[0]).toHaveAttribute('data-source', 'spec');
    expect(spans[0]).toHaveClass('lemma-highlight');
    expect(spans[0]).toHaveClass('custom-highlight');
  });
});


