import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { ExampleDetailModal, type ExampleItemData } from './ExampleDetailModal';
import { SettingsProvider } from '../SettingsContext';
import type { ReactNode } from 'react';
import { act } from 'react';

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
    model: 'gpt-5-mini',
    temperature: 0.6,
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
  });

  it('renders TTS buttons for original and translated texts', () => {
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    const ttsButtons = screen.getAllByRole('button', { name: '音声' });
    expect(ttsButtons).toHaveLength(2);
    expect(screen.getByText(item.en)).toBeInTheDocument();
    expect(screen.getByText(item.ja)).toBeInTheDocument();
  });

  it('shows study progress buttons with counts', () => {
    const enriched: ExampleItemData = { ...item, checked_only_count: 2, learned_count: 1 };
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={enriched} />
      </SettingsProvider>
    );

    expect(screen.getByRole('button', { name: '確認した (2)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '学習した (1)' })).toBeInTheDocument();
  });

  it('toggles transcription typing form', async () => {
    const user = userEvent.setup();
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    const toggleButton = screen.getByRole('button', { name: '文字起こしタイピング (0文字)' });
    await act(async () => {
      await user.click(toggleButton);
    });

    expect(screen.getByLabelText('文字起こしタイピング入力')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'タイピング記録' })).toBeDisabled();
  });

  it('enforces transcription length tolerance', async () => {
    const user = userEvent.setup();
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '文字起こしタイピング (0文字)' }));
    });
    const textarea = screen.getByLabelText('文字起こしタイピング入力');
    await act(async () => {
      await user.clear(textarea);
      await user.type(textarea, 'short');
    });

    const recordButton = screen.getByRole('button', { name: 'タイピング記録' });
    expect(recordButton).toBeDisabled();
    expect(screen.getByText(/入力文字数差:/)).toHaveTextContent(/入力文字数差: -\d+/);

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
      await user.click(screen.getByRole('button', { name: '文字起こしタイピング (2文字)' }));
    });
    const textarea = screen.getByLabelText('文字起こしタイピング入力');
    await act(async () => {
      await user.clear(textarea);
      await user.type(textarea, item.en);
    });

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'タイピング記録' }));
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
    expect(screen.getByRole('button', { name: '文字起こしタイピング (5文字)' })).toBeInTheDocument();
    expect(screen.getByText('タイピング記録を保存しました')).toBeInTheDocument();
  });
});
