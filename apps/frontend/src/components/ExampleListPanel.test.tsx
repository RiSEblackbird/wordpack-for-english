import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { ExampleListPanel } from './ExampleListPanel';
import { guestLockMessage } from './GuestLock';

const mockFetchJson = vi.hoisted(() => vi.fn());

vi.mock('../lib/fetcher', () => {
  class MockApiError extends Error {}
  return {
    fetchJson: mockFetchJson,
    ApiError: MockApiError,
  };
});

vi.mock('../SettingsContext', () => ({
  useSettings: () => ({ settings: { apiBase: '/api' } }),
}));

vi.mock('../ConfirmDialogContext', () => ({
  useConfirmDialog: () => async () => true,
}));

vi.mock('../AuthContext', () => ({
  useAuth: () => ({ isGuest: true }),
}));

describe('ExampleListPanel', () => {
  beforeEach(() => {
    mockFetchJson.mockReset();
  });

  it('locks selection controls and shows tooltip for guests', async () => {
    mockFetchJson.mockResolvedValueOnce({
      items: [
        {
          id: 1,
          word_pack_id: 'wp:test',
          lemma: 'alpha',
          category: 'Dev',
          en: 'Sample example',
          ja: 'サンプル',
          created_at: '2024-05-01T09:00:00+09:00',
          checked_only_count: 0,
          learned_count: 0,
          transcription_typing_count: 0,
        },
      ],
      total: 1,
      limit: 200,
      offset: 0,
    });

    render(<ExampleListPanel />);

    await screen.findByTestId('example-card');

    vi.useFakeTimers();

    const selectAllButton = screen.getByRole('button', { name: '表示中を全選択' });
    expect(selectAllButton).toBeDisabled();
    expect(selectAllButton).toHaveAttribute('aria-disabled', 'true');

    const checkbox = screen.getByRole('checkbox', { name: '例文 Sample example を選択' });
    expect(checkbox).toBeDisabled();
    expect(checkbox).toHaveAttribute('aria-disabled', 'true');

    const wrapper = selectAllButton.parentElement as HTMLElement;
    act(() => {
      fireEvent.mouseEnter(wrapper);
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(screen.getByText(guestLockMessage)).toBeInTheDocument();

    act(() => {
      fireEvent.mouseLeave(wrapper);
    });
    expect(screen.queryByText(guestLockMessage)).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
