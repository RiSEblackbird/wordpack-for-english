import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';

describe('WordPackListPanel card actions layout (two rows)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).fetch = vi.fn();
    try { sessionStorage.clear(); } catch {}
    try {
      localStorage.setItem(
        'wordpack.auth.v1',
        JSON.stringify({
          user: { google_sub: 'tester', email: 'tester@example.com', display_name: 'Tester' },
          token: 'token',
        }),
      );
    } catch {}
  });

  afterEach(() => {
    try {
      localStorage.removeItem('wordpack.auth.v1');
    } catch {}
  });

  function renderWithAuth() {
    return render(
      <AppProviders googleClientId="test-client">
        <App />
      </AppProviders>,
    );
  }

  function setupFetchMocks() {
    const mock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: any) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      const method = init?.method ?? 'GET';

      if (url.endsWith('/api/config') && method === 'GET') {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.startsWith('/api/word/packs?') && method === 'GET') {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        return new Response(
          JSON.stringify({
            items: [
              { id: 'wp:test:1', lemma: 'delta', sense_title: 'デルタ概説', created_at: now.toISOString(), updated_at: yesterday.toISOString(), is_empty: true, checked_only_count: 0, learned_count: 0 },
              { id: 'wp:test:2', lemma: 'alpha', sense_title: 'アルファ概説', created_at: now.toISOString(), updated_at: now.toISOString(), is_empty: false, examples_count: { Dev: 1, CS: 0, LLM: 0, Business: 0, Common: 0 }, checked_only_count: 0, learned_count: 0 },
            ],
            total: 2,
            limit: 20,
            offset: 0,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      if (url.endsWith('/api/word/packs/wp:test:1/regenerate') && method === 'POST') {
        return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (url.startsWith('/api/word/packs/wp:test:') && method === 'DELETE') {
        return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (url.endsWith('/api/word/packs/wp:test:1') && method === 'GET') {
        return new Response(JSON.stringify({ lemma: 'delta', sense_title: 'デルタ概説', pronunciation: null, senses: [], examples: {}, collocations: {}, contrast: [], etymology: { note: '-', confidence: 'low' }, study_card: '', citations: [], confidence: 'low' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.endsWith('/api/word/packs/wp:test:2') && method === 'GET') {
        return new Response(JSON.stringify({ lemma: 'alpha', sense_title: 'アルファ概説', pronunciation: null, senses: [], examples: {}, collocations: {}, contrast: [], etymology: { note: '-', confidence: 'low' }, study_card: '', citations: [], confidence: 'low' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('カード右上の操作が2行: 上段=音声/削除, 下段=生成/語義(右寄せ)', async () => {
    setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();

    // WordPackタブ（既定）を表示
    await waitFor(() => expect(screen.getByText('保存済みWordPack一覧')).toBeInTheDocument());
    const cards = await screen.findAllByTestId('wp-card');
    expect(cards.length).toBeGreaterThanOrEqual(2);

    // is_empty の delta カードを対象に検証
    const target = cards.find((el) => /delta/.test(el.textContent || ''))!;

    // 上段グループ: 音声 / 削除
    const upper = within(target).getByRole('group', { name: 'カード操作 上段' });
    const upperButtons = within(upper).getAllByRole('button');
    expect(upperButtons.map((b) => b.textContent)).toEqual(['音声', '削除']);

    // 下段グループ: 右寄せで 生成 / 語義（is_empty のため生成あり）
    const lower = within(target).getByRole('group', { name: 'カード操作 下段' });
    const lowerButtons = within(lower).getAllByRole('button');
    expect(lowerButtons.map((b) => b.textContent)).toEqual(['生成', '語義']);

    // 非 empty カードでは下段が「語義」のみであること
    const nonEmpty = cards.find((el) => /alpha/.test(el.textContent || ''))!;
    const lower2 = within(nonEmpty).getByRole('group', { name: 'カード操作 下段' });
    const lower2Buttons = within(lower2).getAllByRole('button');
    expect(lower2Buttons.map((b) => b.textContent)).toEqual(['語義']);

    // 動作確認（語義をクリックしてもカードが開かない＝イベント停止）
    const senseBtn = within(lower).getByRole('button', { name: '語義' });
    await act(async () => { await user.click(senseBtn); });
    expect(screen.queryByRole('dialog', { name: 'WordPack プレビュー' })).not.toBeInTheDocument();
  });
});


