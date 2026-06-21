import type { ExampleCategory, Examples, WordPack, WordPackListItem } from '../../features/wordpack/types';

export type ExploreMode = 'related' | 'collocations' | 'contrast' | 'examples' | 'unknown';
export type ExploreRelationKind = Exclude<ExploreMode, 'unknown'>;
export type ExploreRelationStatus = 'existing' | 'empty' | 'unknown';

export interface RawExploreRelation {
  id: string;
  kind: ExploreRelationKind;
  label: string;
  source: string;
  description?: string;
}

export interface ExploreRelation extends RawExploreRelation {
  status: ExploreRelationStatus;
  targetWordPack?: WordPackListItem;
}

const EXAMPLE_CATEGORIES: ExampleCategory[] = ['Dev', 'CS', 'LLM', 'Business', 'Common'];

const toText = (value: unknown): string => (typeof value === 'string' ? value.trim() : '');

const toTextList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value.map(toText).filter(Boolean);
};

const normalize = (value: unknown): string => toText(value).toLowerCase();

const compactUnique = (items: RawExploreRelation[]): RawExploreRelation[] => {
  const seen = new Set<string>();
  const result: RawExploreRelation[] = [];
  items.forEach((item) => {
    const label = toText(item.label);
    if (!label) return;
    const source = toText(item.source) || item.kind;
    const description = toText(item.description);
    const key = `${item.kind}:${normalize(label)}:${normalize(source)}`;
    if (seen.has(key)) return;
    seen.add(key);
    result.push({
      ...item,
      label,
      source,
      ...(description ? { description } : {}),
    });
  });
  return result;
};

const flattenCollocationGroup = (
  groupName: 'general' | 'academic',
  lists: Partial<WordPack['collocations']['general']> | undefined,
): RawExploreRelation[] =>
  Object.entries(lists ?? {}).flatMap(([listName, values]) =>
    toTextList(values).map((value, index) => ({
      id: `collocation-${groupName}-${listName}-${index}`,
      kind: 'collocations' as const,
      label: value,
      source: `${groupName} / ${listName}`,
    })),
  );

const flattenExamples = (examples: Partial<Examples> | undefined): RawExploreRelation[] =>
  EXAMPLE_CATEGORIES.flatMap((category) =>
    (Array.isArray(examples?.[category]) ? examples[category] : []).flatMap((example, index) => {
      const label = toText(example?.en);
      if (!label) return [];
      return [{
        id: `example-${category}-${index}`,
        kind: 'examples' as const,
        label,
        description: toText(example?.ja),
        source: category,
      }];
    }),
  );

export const buildExploreRelations = (wordPack: WordPack): RawExploreRelation[] => {
  const senses = Array.isArray(wordPack.senses) ? wordPack.senses : [];
  const related = senses.flatMap((sense: unknown, senseIndex) => {
    if (!sense || typeof sense !== 'object') return [];
    const senseRecord = sense as {
      antonyms?: unknown;
      gloss_ja?: unknown;
      patterns?: unknown;
      synonyms?: unknown;
    };
    return [
      ...toTextList(senseRecord.synonyms).map((label, index) => ({
        id: `synonym-${senseIndex}-${index}`,
        kind: 'related' as const,
        label,
        source: 'synonym',
      })),
      ...toTextList(senseRecord.antonyms).map((label, index) => ({
        id: `antonym-${senseIndex}-${index}`,
        kind: 'related' as const,
        label,
        source: 'antonym',
      })),
      ...toTextList(senseRecord.patterns).map((label, index) => ({
        id: `pattern-${senseIndex}-${index}`,
        kind: 'related' as const,
        label,
        source: 'pattern',
        description: toText(senseRecord.gloss_ja),
      })),
    ];
  });

  const collocations = [
    ...flattenCollocationGroup('general', wordPack.collocations?.general),
    ...flattenCollocationGroup('academic', wordPack.collocations?.academic),
  ];

  const contrasts = (Array.isArray(wordPack.contrast) ? wordPack.contrast : []).flatMap((item, index) => {
    if (!item || typeof item !== 'object') return [];
    const itemRecord = item as { with?: unknown; with_?: unknown; diff_ja?: unknown };
    const label = toText(itemRecord.with ?? itemRecord.with_);
    if (!label) return [];
    return [{
      id: `contrast-${index}`,
      kind: 'contrast' as const,
      label,
      description: toText(itemRecord.diff_ja),
      source: 'contrast',
    }];
  });

  return compactUnique([...related, ...collocations, ...contrasts, ...flattenExamples(wordPack.examples)]);
};

const findWordPackForRelation = (
  label: string,
  wordPacks: WordPackListItem[],
  currentLemma: string,
): WordPackListItem | undefined => {
  const normalizedCurrent = normalize(currentLemma);
  const byLemma = new Map(
    wordPacks
      .map((wordPack) => [normalize(wordPack.lemma), wordPack] as const)
      .filter(([lemma]) => Boolean(lemma)),
  );
  const exact = byLemma.get(normalize(label));
  if (exact && normalize(exact.lemma) !== normalizedCurrent) return exact;

  const tokens = normalize(label)
    .split(/[^a-z0-9'-]+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 3 && token !== normalizedCurrent);
  return tokens.map((token) => byLemma.get(token)).find(Boolean);
};

export const attachRelationStatus = (
  relations: RawExploreRelation[],
  wordPacks: WordPackListItem[],
  currentLemma: string,
): ExploreRelation[] =>
  relations.map((relation) => {
    const targetWordPack = findWordPackForRelation(relation.label, wordPacks, currentLemma);
    if (!targetWordPack) return { ...relation, status: 'unknown' };
    return {
      ...relation,
      targetWordPack,
      status: targetWordPack.is_empty ? 'empty' : 'existing',
    };
  });

export const filterExploreRelations = (
  relations: ExploreRelation[],
  mode: ExploreMode,
): ExploreRelation[] => {
  if (mode === 'unknown') {
    return relations.filter((relation) => relation.status === 'unknown');
  }
  return relations.filter((relation) => relation.kind === mode);
};
