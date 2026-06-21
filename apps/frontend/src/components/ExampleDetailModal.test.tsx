import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { ExampleDetailModal, type ExampleItemData } from './ExampleDetailModal';
import { SettingsProvider } from '../SettingsContext';
import type { ReactNode } from 'react';
import * as AuthContext from '../AuthContext';
import { guestLockMessage } from './GuestLock';

const mockFetchJson = vi.hoisted(() => vi.fn());

vi.mock('../lib/fetcher', () => {
  class MockApiError extends Error {}
  return {
    fetchJson: mockFetchJson,
    ApiError: MockApiError,
  };
});

vi.mock('../SettingsContext', () => {
  const settings = {
    apiBase: '/api',
    pronunciationEnabled: true,
    regenerateScope: 'all',
    autoAdvanceAfterGrade: false,
    requestTimeoutMs: 60000,
    model: 'gpt-5.4-mini',
    reasoningEffort: 'minimal' as const,
    textVerbosity: 'medium' as const,
    theme: 'dark' as const,
    ttsPlaybackRate: 1,
    ttsVolume: 1,
  };
  return {
    useSettings: () => ({ settings, setSettings: () => {} }),
    SettingsProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  };
});

describe('ExampleDetailModal', () => {
  const item: ExampleItemData = {
    id: 101,
    word_pack_id: 'wp:test',
    lemma: 'alpha',
    category: 'Dev',
    en: 'Test sentence in English.',
    ja: '英語の例文です。',
    created_at: '2024-05-01T09:00:00+09:00',
  };

  beforeEach(() => {
    mockFetchJson.mockReset();
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({ isGuest: false } as any);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders TTS buttons for original and translated texts', () => {
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    expect(screen.getByRole('button', { name: '原文の音声' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '日本語訳の音声' })).toBeInTheDocument();
    expect(screen.getByText(item.en)).toBeInTheDocument();
    expect(screen.getByText(item.ja)).toBeInTheDocument();
  });

  it('aligns original and translated sentences in matching rows', () => {
    const enriched: ExampleItemData = {
      ...item,
      en: 'The cache serves fresh data. The platform keeps latency low.',
      ja: 'キャッシュは新しいデータを提供します。プラットフォームは低遅延を保ちます。',
    };
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={enriched} />
      </SettingsProvider>
    );

    const pairs = within(screen.getByRole('list', { name: '原文と日本語訳の対応' })).getAllByRole('listitem');
    expect(pairs).toHaveLength(2);
    expect(pairs[0]).toHaveTextContent('The cache serves fresh data.');
    expect(pairs[0]).toHaveTextContent('キャッシュは新しいデータを提供します。');
    expect(pairs[1]).toHaveTextContent('The platform keeps latency low.');
    expect(pairs[1]).toHaveTextContent('プラットフォームは低遅延を保ちます。');
  });

  it('shows study progress buttons with counts', () => {
    const enriched: ExampleItemData = { ...item, checked_only_count: 2, learned_count: 1 };
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={enriched} />
      </SettingsProvider>
    );

    expect(screen.getByRole('button', { name: '確認済みにする (2)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '学習済みにする (1)' })).toBeInTheDocument();
  });

  it('groups long grammar explanation into summary and collapsible details', () => {
    const enriched: ExampleItemData = {
      ...item,
      grammar_ja: '1) 品詞分解: The app 【名/主語】 / uses 【動詞】 / authentication 【名/目的語】。\n\n2) 解説: 文の核はSVOで、authentication が目的語です。',
    };
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={enriched} />
      </SettingsProvider>
    );

    expect(screen.getByRole('heading', { name: '解説' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '要点' })).toBeInTheDocument();
    expect(screen.getByText(/文の核はSVO/)).toBeInTheDocument();
    expect(screen.getByText('品詞分解を表示')).toBeInTheDocument();
  });

  it('keeps inline part-of-speech breakdown out of the explanation summary', () => {
    const enriched: ExampleItemData = {
      ...item,
      grammar_ja:
        'The cache 【名/主語】 / serves 【動詞】 / fresh data 【名/目的語】。\n文の核はSVOで、fresh data が目的語です。',
    };
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={enriched} />
      </SettingsProvider>
    );

    const summaryCard = screen.getByRole('heading', { name: '要点' }).closest('article');
    expect(summaryCard).not.toBeNull();
    expect(summaryCard as HTMLElement).toHaveTextContent('文の核はSVO');
    expect(summaryCard as HTMLElement).not.toHaveTextContent('The cache 【名/主語】');
    expect(screen.getByText('品詞分解を表示')).toBeInTheDocument();
  });

  it('toggles transcription typing form', async () => {
    const user = userEvent.setup();
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    const toggleButton = screen.getByRole('button', { name: '文字起こしタイピングを開く (0文字)' });
    await act(async () => {
      await user.click(toggleButton);
    });

    expect(screen.getByLabelText('文字起こしタイピング入力')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '文字起こしを記録' })).toBeDisabled();
    expect(screen.getByText(/原文と同じ英文を入力してください/)).toBeInTheDocument();
  });

  it('enforces transcription length tolerance', async () => {
    const user = userEvent.setup();
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '文字起こしタイピングを開く (0文字)' }));
    });
    const textarea = screen.getByLabelText('文字起こしタイピング入力');
    await act(async () => {
      await user.clear(textarea);
      await user.type(textarea, 'short');
    });

    const recordButton = screen.getByRole('button', { name: '文字起こしを記録' });
    expect(recordButton).toBeDisabled();
    expect(screen.getByText(/入力文字数差:/)).toHaveTextContent(/10文字以内/);

    await act(async () => {
      await user.clear(textarea);
      await user.type(textarea, 'Test sentence in English.');
    });
    expect(recordButton).toBeEnabled();
  });

  it('sends transcription typing record to API and notifies parent', async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    mockFetchJson.mockResolvedValueOnce({
      id: 101,
      word_pack_id: 'wp:test',
      transcription_typing_count: 5,
    });

    render(
      <SettingsProvider>
        <ExampleDetailModal
          isOpen
          onClose={() => {}}
          item={{ ...item, transcription_typing_count: 2 }}
          onTranscriptionTypingRecorded={handler}
        />
      </SettingsProvider>
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '文字起こしタイピングを開く (2文字)' }));
    });
    const textarea = screen.getByLabelText('文字起こしタイピング入力');
    await act(async () => {
      await user.clear(textarea);
      await user.type(textarea, item.en);
    });

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '文字起こしを記録' }));
    });

    await waitFor(() => {
      expect(mockFetchJson).toHaveBeenCalledWith(
        '/api/word/examples/101/transcription-typing',
        expect.objectContaining({
          method: 'POST',
          body: { input_length: item.en.length },
        })
      );
    });
    expect(handler).toHaveBeenCalledWith({
      id: 101,
      word_pack_id: 'wp:test',
      transcription_typing_count: 5,
    });
    expect(screen.getByRole('button', { name: '文字起こしタイピングを閉じる (5文字)' })).toBeInTheDocument();
    expect(screen.getByText('タイピング記録を保存しました')).toBeInTheDocument();
  });

  it('locks study actions and shows tooltip in guest mode', async () => {
    vi.useFakeTimers();
    vi.mocked(AuthContext.useAuth).mockReturnValue({ isGuest: true } as any);

    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>,
    );

    const studyButton = screen.getByRole('button', { name: '確認済みにする (0)' });
    expect(studyButton).toBeDisabled();
    expect(studyButton).toHaveAttribute('aria-disabled', 'true');

    const wrapper = studyButton.parentElement as HTMLElement;
    act(() => {
      fireEvent.mouseEnter(wrapper);
    });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(screen.getByRole('tooltip')).toHaveTextContent(guestLockMessage);

    act(() => {
      fireEvent.mouseLeave(wrapper);
    });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
