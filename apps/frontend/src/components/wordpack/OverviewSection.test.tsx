import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { OverviewSection } from './OverviewSection';
import * as AuthContext from '../../AuthContext';
import type { WordPack } from '../../hooks/useWordPack';

describe('OverviewSection', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({ isGuest: false } as any);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('keeps the "再生成" button right-aligned when wrapped by GuestLock', () => {
    vi.useFakeTimers();

    const data: WordPack = {
      lemma: 'alpha',
      sense_title: 'title',
      pronunciation: { linking_notes: [] },
      senses: [],
      collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
      contrast: [],
      examples: { Dev: [], CS: [], LLM: [], Business: [], Common: [] },
      etymology: { note: '', confidence: 'low' },
      study_card: 'study',
      citations: [],
      confidence: 'low',
    };

    render(
      <OverviewSection
        data={data}
        selectedMeta={null}
        aiMeta={null}
        exampleStats={{ counts: [], total: 0 }}
        currentWordPackId="wp:1"
        isActionLoading={false}
        guestPublic={false}
        guestPublicUpdating={false}
        onGuestPublicChange={() => {}}
        packCheckedCount={0}
        packLearnedCount={0}
        onRecordStudyProgress={() => {}}
        onRegenerate={() => {}}
        formatDate={() => '2024/01/01 00:00'}
      />,
    );

    const button = screen.getByRole('button', { name: '再生成' });
    const wrapper = button.parentElement as HTMLElement;
    // GuestLock wrapper が flex item になるため、autoマージンは wrapper 側に必要
    expect(wrapper).toHaveStyle({ marginLeft: 'auto' });
  });
});
