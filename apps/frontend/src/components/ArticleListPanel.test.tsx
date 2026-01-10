import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { ArticleListPanel } from './ArticleListPanel';
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

vi.mock('../ModalContext', () => ({
  useModal: () => ({ setModalOpen: () => {} }),
}));

vi.mock('../NotificationsContext', () => ({
  useNotifications: () => ({ add: () => '', update: () => {} }),
}));

vi.mock('../ConfirmDialogContext', () => ({
  useConfirmDialog: () => async () => true,
}));

vi.mock('../AuthContext', () => ({
  useAuth: () => ({ isGuest: true }),
}));

describe('ArticleListPanel', () => {
  beforeEach(() => {
    mockFetchJson.mockReset();
  });

  it('locks selection UI and shows tooltip for guests', async () => {
    mockFetchJson.mockResolvedValueOnce({
      items: [
        {
          id: 'art:1',
          title_en: 'Article A',
          created_at: '2024-05-01T09:00:00+09:00',
          updated_at: '2024-05-01T09:10:00+09:00',
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    });

    render(<ArticleListPanel />);

    await screen.findByText('Article A');

    vi.useFakeTimers();

    const selectAllButton = screen.getByRole('button', { name: '表示中を全選択' });
    expect(selectAllButton).toBeDisabled();
    expect(selectAllButton).toHaveAttribute('aria-disabled', 'true');

    const checkbox = screen.getByRole('checkbox', { name: '文章 Article A を選択' });
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
