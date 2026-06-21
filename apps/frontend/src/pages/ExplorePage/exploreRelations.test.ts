import { describe, expect, it } from 'vitest';
import type { WordPack, WordPackListItem } from '../../features/wordpack/types';
import {
  attachRelationStatus,
  buildExploreRelations,
  filterExploreRelations,
} from './exploreRelations';

const baseWordPack: WordPack = {
  lemma: 'alpha',
  sense_title: '初期検証版',
  pronunciation: { linking_notes: [] },
  senses: [],
  collocations: {
    general: { verb_object: [], adj_noun: [], prep_noun: [] },
    academic: { verb_object: [], adj_noun: [], prep_noun: [] },
  },
  contrast: [],
  examples: {
    Dev: [],
    CS: [],
    LLM: [],
    Business: [],
    Common: [],
  },
  etymology: { note: '', confidence: 'low' },
  study_card: '',
  citations: [],
  confidence: 'low',
};

const savedWordPacks: WordPackListItem[] = [
  {
    id: 'wp:preview',
    lemma: 'preview',
    sense_title: '試作版',
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-02T00:00:00Z',
    is_empty: false,
    guest_public: true,
    examples_count: { Dev: 0, CS: 0, LLM: 0, Business: 0, Common: 0 },
    checked_only_count: 0,
    learned_count: 0,
  },
  {
    id: 'wp:beta',
    lemma: 'beta',
    sense_title: 'ベータ版',
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-02T00:00:00Z',
    is_empty: true,
    guest_public: false,
    examples_count: { Dev: 0, CS: 0, LLM: 0, Business: 0, Common: 0 },
    checked_only_count: 0,
    learned_count: 0,
  },
];

describe('exploreRelations', () => {
  it('keeps valid relations and status labels from a normal WordPack detail', () => {
    const relations = attachRelationStatus(
      buildExploreRelations({
        ...baseWordPack,
        senses: [
          {
            id: 's1',
            gloss_ja: '検証版',
            patterns: ['alpha build'],
            synonyms: ['preview'],
            antonyms: ['stable'],
          },
        ],
        collocations: {
          general: { verb_object: ['ship an alpha'], adj_noun: [], prep_noun: [] },
          academic: { verb_object: [], adj_noun: [], prep_noun: [] },
        },
        contrast: [{ with: 'beta', diff_ja: 'beta は利用者を広げた検証段階。' }],
        examples: {
          ...baseWordPack.examples,
          Dev: [{ en: 'This feature is still in alpha.', ja: 'この機能はまだアルファ段階です。' }],
        },
      }),
      savedWordPacks,
      'alpha',
    );

    expect(relations.map((relation) => relation.label)).toEqual(
      expect.arrayContaining(['preview', 'stable', 'ship an alpha', 'beta', 'This feature is still in alpha.']),
    );
    expect(relations.find((relation) => relation.label === 'preview')?.status).toBe('existing');
    expect(relations.find((relation) => relation.label === 'beta')?.status).toBe('empty');
    expect(filterExploreRelations(relations, 'unknown').some((relation) => relation.label === 'stable')).toBe(true);
  });

  it('ignores malformed or legacy relation fields instead of throwing', () => {
    const malformedDetail = {
      ...baseWordPack,
      senses: [
        null,
        'legacy sense sentence',
        {
          id: 's1',
          gloss_ja: '検証版',
          patterns: ['alpha build', '', 42],
          synonyms: ['preview', null],
          antonyms: undefined,
        },
      ],
      collocations: {
        general: {
          verb_object: null,
          adj_noun: ['robust evidence', 123, ' '],
          prep_noun: ['in alpha'],
        },
        academic: undefined,
      },
      contrast: [
        'legacy contrast sentence',
        { with: 'beta', diff_ja: 'beta は利用者を広げた検証段階。' },
        { with_: 'stable', diff_ja: '正式利用を想定する段階。' },
        { with: '', diff_ja: 'ignored' },
      ],
      examples: {
        Dev: [
          { en: 'Valid example sentence.', ja: '有効な例文。' },
          { en: null, ja: 'ignored' },
        ],
        CS: null,
        LLM: [],
        Business: [],
        Common: [],
      },
    } as unknown as WordPack;

    const relations = buildExploreRelations(malformedDetail);
    const labels = relations.map((relation) => relation.label);

    expect(labels).toEqual(
      expect.arrayContaining([
        'alpha build',
        'preview',
        'robust evidence',
        'in alpha',
        'beta',
        'stable',
        'Valid example sentence.',
      ]),
    );
    expect(labels).not.toContain('legacy contrast sentence');
    expect(labels).not.toContain('legacy sense sentence');
    expect(labels).not.toContain('42');
    expect(labels).not.toContain('123');
  });
});
