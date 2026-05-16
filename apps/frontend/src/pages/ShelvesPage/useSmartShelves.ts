import { useMemo } from 'react';
import { buildSmartShelves } from './smartShelfRules';
import type { WordPackListItem } from '../../features/wordpack/types';

export const useSmartShelves = (wordPacks: WordPackListItem[]) =>
  useMemo(() => buildSmartShelves(wordPacks), [wordPacks]);
