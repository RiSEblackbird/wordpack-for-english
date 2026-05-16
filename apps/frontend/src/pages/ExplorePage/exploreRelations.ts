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

const normalize = (value: string): string => value.trim().toLowerCase();

const compactUnique = (items: RawExploreRelation[]): RawExploreRelation[] => {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.kind}:${normalize(item.label)}:${item.source}`;
    if (!item.label.trim() || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const flattenCollocationGroup = (
  groupName: 'general' | 'academic',
  lists: WordPack['collocations']['general'],
): RawExploreRelation[] =>
  (Object.entries(lists) as [string, string[]][]).flatMap(([listName, values]) =>
    values.map((value, index) => ({
      id: `collocation-${groupName}-${listName}-${index}`,
      kind: 'collocations' as const,
      label: value,
      source: `${groupName} / ${listName}`,
    })),
  );

const flattenExamples = (examples: Examples): RawExploreRelation[] =>
  EXAMPLE_CATEGORIES.flatMap((category) =>
    (examples[category] ?? []).map((example, index) => ({
      id: `example-${category}-${index}`,
      kind: 'examples' as const,
      label: example.en,
      description: example.ja,
      source: category,
    })),
  );

export const buildExploreRelations = (wordPack: WordPack): RawExploreRelation[] => {
  const related = wordPack.senses.flatMap((sense, senseIndex) => [
    ...(sense.synonyms ?? []).map((label, index) => ({
      id: `synonym-${senseIndex}-${index}`,
      kind: 'related' as const,
      label,
      source: 'synonym',
    })),
    ...(sense.antonyms ?? []).map((label, index) => ({
      id: `antonym-${senseIndex}-${index}`,
      kind: 'related' as const,
      label,
      source: 'antonym',
    })),
    ...(sense.patterns ?? []).map((label, index) => ({
      id: `pattern-${senseIndex}-${index}`,
      kind: 'related' as const,
      label,
      source: 'pattern',
      description: sense.gloss_ja,
    })),
  ]);

  const collocations = [
    ...flattenCollocationGroup('general', wordPack.collocations.general),
    ...flattenCollocationGroup('academic', wordPack.collocations.academic),
  ];

  const contrasts = wordPack.contrast.map((item, index) => ({
    id: `contrast-${index}`,
    kind: 'contrast' as const,
    label: item.with,
    description: item.diff_ja,
    source: 'contrast',
  }));

  return compactUnique([...related, ...collocations, ...contrasts, ...flattenExamples(wordPack.examples)]);
};

const findWordPackForRelation = (
  label: string,
  wordPacks: WordPackListItem[],
  currentLemma: string,
): WordPackListItem | undefined => {
  const normalizedCurrent = normalize(currentLemma);
  const byLemma = new Map(wordPacks.map((wordPack) => [normalize(wordPack.lemma), wordPack]));
  const exact = byLemma.get(normalize(label));
  if (exact && normalize(exact.lemma) !== normalizedCurrent) return exact;

  const tokens = label
    .toLowerCase()
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
