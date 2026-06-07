import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationsProvider } from '../../NotificationsContext';
import { ShelvesPage } from './index';

vi.mock('../../SettingsContext', () => ({
  useSettings: () => ({
    settings: {
      apiBase: '/api',
      requestTimeoutMs: 60000,
    },
  }),
  useOptionalSettings: () => ({
    settings: {
      apiBase: '/api',
      requestTimeoutMs: 60000,
    },
  }),
}));

const setupFetch = () => {
  const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.startsWith('/api/word/packs?')) {
      return Promise.resolve(
        new Response(JSON.stringify({
          items: [
            {
              id: 'wp:robust',
              lemma: 'robust',
              sense_title: '壊れにくい',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-03T00:00:00Z',
              is_empty: false,
              guest_public: true,
              examples_count: { Dev: 3, CS: 0, LLM: 0, Business: 2, Common: 1 },
              checked_only_count: 2,
              learned_count: 1,
            },
            {
              id: 'wp:stale',
              lemma: 'stale',
              sense_title: '',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-02T00:00:00Z',
              is_empty: true,
              guest_public: false,
              examples_count: { Dev: 0, CS: 0, LLM: 0, Business: 0, Common: 0 },
              checked_only_count: 0,
              learned_count: 0,
            },
          ],
          total: 2,
          limit: 200,
          offset: 0,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      );
    }
    return Promise.resolve(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
  });
  (globalThis as any).fetch = fetchMock;
  return fetchMock;
};

describe('ShelvesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    setupFetch();
  });

  it('builds smart shelves from existing WordPacks and switches the active shelf', async () => {
    render(
      <NotificationsProvider persist={false}>
        <ShelvesPage />
      </NotificationsProvider>,
    );

    expect(screen.getByRole('heading', { name: 'Shelves' })).toBeInTheDocument();
    expect((await screen.findAllByText('最近更新')).length).toBeGreaterThan(0);
    expect(screen.getByText('未生成')).toBeInTheDocument();

    const user = userEvent.setup();
    const emptyShelf = screen.getByText('未生成').closest('article') as HTMLElement;
    await act(async () => {
      await user.click(within(emptyShelf).getByRole('button', { name: '開く' }));
    });

    expect(screen.getAllByRole('heading', { name: '未生成' }).length).toBeGreaterThan(0);
    expect(screen.getByText('stale')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'プレビュー' })).toBeEnabled();
    expect(localStorage.getItem('wp.localShelves.v1')).toBeNull();
  });
});
