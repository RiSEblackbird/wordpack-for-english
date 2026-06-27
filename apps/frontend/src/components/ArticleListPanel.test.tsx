import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { ArticleListPanel } from './ArticleListPanel';
import { guestLockMessage } from './GuestLock';

const mockFetchJson = vi.hoisted(() => vi.fn());
const authState = vi.hoisted(() => ({ isGuest: true }));

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
  useAuth: () => ({ isGuest: authState.isGuest }),
}));

describe('ArticleListPanel', () => {
  beforeEach(() => {
    mockFetchJson.mockReset();
    authState.isGuest = true;
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
    expect(window.getComputedStyle(selectAllButton).backgroundColor).toBe('rgb(229, 231, 235)');
    expect(window.getComputedStyle(selectAllButton).color).toBe('rgb(55, 65, 81)');

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
    expect(screen.getByRole('tooltip')).toHaveTextContent(guestLockMessage);

    act(() => {
      fireEvent.mouseLeave(wrapper);
    });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it('lets authenticated users toggle Reader article guest public visibility', async () => {
    authState.isGuest = false;
    mockFetchJson
      .mockResolvedValueOnce({
        items: [
          {
            id: 'art:1',
            title_en: 'Article A',
            created_at: '2024-05-01T09:00:00+09:00',
            updated_at: '2024-05-01T09:10:00+09:00',
            guest_public: false,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      })
      .mockResolvedValueOnce({ article_id: 'art:1', guest_public: true });

    render(<ArticleListPanel />);

    await screen.findByText('Article A');

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '公開にする' }));
    });

    expect(mockFetchJson).toHaveBeenCalledWith(
      '/api/article/art%3A1/guest-public',
      {
        method: 'POST',
        body: { guest_public: true },
      },
    );
    expect(screen.getByText('Reader記事をゲスト公開しました')).toBeInTheDocument();
  });

  it('shows a page-empty state when the current Reader page is out of range', async () => {
    authState.isGuest = false;
    const firstPage = {
      items: [
        {
          id: 'art:1',
          title_en: 'Article A',
          created_at: '2024-05-01T09:00:00+09:00',
          updated_at: '2024-05-01T09:10:00+09:00',
          guest_public: true,
        },
      ],
      total: 21,
      limit: 20,
      offset: 0,
    };
    mockFetchJson
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce({
        items: [],
        total: 21,
        limit: 20,
        offset: 20,
      })
      .mockResolvedValueOnce(firstPage);

    render(<ArticleListPanel />);

    await screen.findByText('Article A');

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: '次へ' }));
    });

    expect(await screen.findByText('このページに表示できるReader記事がありません。')).toBeInTheDocument();
    expect(screen.queryByText('インポート済み文章はまだありません。')).not.toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: '前のページへ戻る' }));
    });

    expect(await screen.findByText('Article A')).toBeInTheDocument();
  });
});
