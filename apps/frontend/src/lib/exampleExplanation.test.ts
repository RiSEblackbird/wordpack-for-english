import { describe, expect, it } from 'vitest';
import { splitExampleExplanation } from './exampleExplanation';

describe('splitExampleExplanation', () => {
  it('separates summary and part-of-speech details from numbered explanation text', () => {
    const result = splitExampleExplanation(
      '1) 品詞分解: The app 【名/主語】 / uses 【動詞】 / authentication 【名/目的語】。\n\n2) 解説: 文の核はSVOで、目的を表すto不定詞が続きます。',
    );

    expect(result.summary).toBe('文の核はSVOで、目的を表すto不定詞が続きます。');
    expect(result.details).toContain('The app');
    expect(result.structure).toBeNull();
  });

  it('treats an unlabeled first grammar paragraph as details when followed by explanation', () => {
    const result = splitExampleExplanation(
      'The app 【名/主語】 / uses 【動詞】 / authentication 【名/目的語】。\n\n文の核はSVOで、authentication が目的語です。',
    );

    expect(result.summary).toBe('文の核はSVOで、authentication が目的語です。');
    expect(result.details).toContain('authentication');
  });
});
