import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { ExamplesSection } from './ExamplesSection';
import * as AuthContext from '../../AuthContext';
import type { WordPack } from '../../hooks/useWordPack';

describe('ExamplesSection', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({ isGuest: false } as any);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('keeps copy available for unsaved generated WordPacks', async () => {
    const onCopyExampleText = vi.fn().mockResolvedValue(undefined);
    const data: WordPack = {
      lemma: 'alpha',
      sense_title: '初期検証版',
      pronunciation: { linking_notes: [] },
      senses: [],
      collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
      contrast: [],
      examples: {
        Dev: [
          {
            en: 'The alpha build exposed navigation issues before the public beta started.',
            ja: 'アルファ版は公開ベータが始まる前にナビゲーション上の問題を明らかにした。',
            grammar_ja: '解説：exposed は問題発見の文脈に合います。',
          },
        ],
        CS: [],
        LLM: [],
        Business: [],
        Common: [],
      },
      etymology: { note: '', confidence: 'medium' },
      study_card: 'alpha release は初期検証版。',
      citations: [],
      confidence: 'medium',
    };

    render(
      <ExamplesSection
        data={data}
        currentWordPackId={null}
        isActionLoading={false}
        onGenerateExamples={vi.fn()}
        onDeleteExample={vi.fn()}
        onImportArticleFromExample={vi.fn()}
        onCopyExampleText={onCopyExampleText}
        onLemmaOpen={vi.fn()}
        lookupLemmaMetadata={vi.fn()}
        triggerUnknownLemmaGeneration={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: 'alphaのDev例文1を削除' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'alphaのDev例文1から記事を作成' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'alphaのDev例文1をコピー' }));

    expect(onCopyExampleText).toHaveBeenCalledWith('Dev', 0);
  });
});
