import { describe, expect, it } from 'vitest';
import { buildExampleTranslationPairs, splitExampleExplanation } from './exampleExplanation';

describe('buildExampleTranslationPairs', () => {
  it('pairs English and Japanese sentences by position when sentence counts match', () => {
    const result = buildExampleTranslationPairs(
      'The cache serves fresh data. The platform keeps latency low.',
      'キャッシュは新しいデータを提供します。プラットフォームは低遅延を保ちます。',
    );

    expect(result).toEqual([
      {
        index: 1,
        en: 'The cache serves fresh data.',
        ja: 'キャッシュは新しいデータを提供します。',
      },
      {
        index: 2,
        en: 'The platform keeps latency low.',
        ja: 'プラットフォームは低遅延を保ちます。',
      },
    ]);
  });

  it('falls back to one full-text pair when sentence counts do not match', () => {
    const result = buildExampleTranslationPairs(
      'The cache serves fresh data. The platform keeps latency low.',
      'キャッシュは新しいデータを提供し、プラットフォームは低遅延を保ちます。',
    );

    expect(result).toEqual([
      {
        index: 1,
        en: 'The cache serves fresh data. The platform keeps latency low.',
        ja: 'キャッシュは新しいデータを提供し、プラットフォームは低遅延を保ちます。',
      },
    ]);
  });
});

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

  it('splits inline breakdown and explanation when they share one paragraph', () => {
    const result = splitExampleExplanation(
      'The cache 【名/主語】 / serves 【動詞】 / fresh data 【名/目的語】。\n文の核はSVOで、fresh data が目的語です。',
    );

    expect(result.summary).toBe('文の核はSVOで、fresh data が目的語です。');
    expect(result.details).toBe('The cache 【名/主語】 / serves 【動詞】 / fresh data 【名/目的語】。');
  });
});
