import { render, screen, act, waitFor, within, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { App } from './App';
import { AppProviders } from './main';

describe('WordPackPanel E2E (mocked fetch)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    (globalThis as any).fetch = vi.fn();
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
    const generated = new Set<string>();
    const mock = vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      if (url.includes('/api/word/lemma/Paths')) {
        return new Response(
          JSON.stringify({ found: true, id: 'wp:Paths:lemma', lemma: 'Paths', sense_title: '語義タイトルなし' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/word/packs') && init?.method === 'POST') {
        const body = init?.body ? JSON.parse(init.body as string) : {};
        const lemma = body.lemma || 'test';
        return new Response(
          JSON.stringify({ id: `wp:${lemma}:abcd1234` }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.startsWith('/api/word/packs/wp:') && (!init || (init && (!init.method || init.method === 'GET')))) {
        const idPart = url.split('/').pop() || '';
        const lemma = idPart.split(':')[1] || 'test';
        return new Response(
          JSON.stringify({
            lemma,
            sense_title: `${lemma}概説`,
            pronunciation: { ipa_GA: null, ipa_RP: null, syllables: null, stress_index: null, linking_notes: [] },
            senses: [{ id: 's1', gloss_ja: '意味', definition_ja: '定義', nuances_ja: 'ニュアンス', patterns: ['p1'], synonyms: ['syn'], antonyms: ['ant'], register: 'formal', notes_ja: '注意' }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: {
              Dev: [
                { en: `${lemma} dev example one with around twenty five tokens total.`, ja: `${lemma} のDev例文1`, grammar_ja: '第3文型' },
                { en: `${lemma} dev example two includes subordinate clauses and clear structure.`, ja: `${lemma} のDev例文2`, grammar_ja: '関係節' }
              ],
              CS: [
                { en: `Paths ${lemma} at the main square downtown.`, ja: `${lemma} のCS例文1`, grammar_ja: '前置詞句' }
              ],
              LLM: [],
              Business: [],
              Common: [
                { en: `Paths ${lemma} at the main square downtown.`, ja: `${lemma} のCommon例文1`, grammar_ja: '前置詞句' },
                { en: `Schedules ${lemma} around the team’s availability.`, ja: `${lemma} のCommon例文2`, grammar_ja: '三単現' },
                { en: 'Ghosts linger without a defined sense in the archive.', ja: 'Ghosts のCommon例文 (senseなし)', grammar_ja: '動詞句' }
              ]
            },
            etymology: { note: '-', confidence: 'low' },
            study_card: `study of ${lemma}`,
            citations: [],
            confidence: 'medium',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/config') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }

      if (url.endsWith('/api/word/pack') && init?.method === 'POST') {
        const body = init?.body ? JSON.parse(init.body as string) : {};
        const lemma = body.lemma || 'test';
        generated.add(lemma);
        return new Response(
          JSON.stringify({
            lemma,
            sense_title: `${lemma}概説`,
            pronunciation: { ipa_GA: null, ipa_RP: null, syllables: null, stress_index: null, linking_notes: [] },
            senses: [{ id: 's1', gloss_ja: '意味', definition_ja: '定義', nuances_ja: 'ニュアンス', patterns: ['p1'], synonyms: ['syn'], antonyms: ['ant'], register: 'formal', notes_ja: '注意' }],
            collocations: { general: { verb_object: [], adj_noun: [], prep_noun: [] }, academic: { verb_object: [], adj_noun: [], prep_noun: [] } },
            contrast: [],
            examples: {
              Dev: [
                { en: `${lemma} dev example one with around twenty five tokens total.`, ja: `${lemma} のDev例文1`, grammar_ja: '第3文型' },
                { en: `${lemma} dev example two includes subordinate clauses and clear structure.`, ja: `${lemma} のDev例文2`, grammar_ja: '関係節' },
                { en: `${lemma} dev example three demonstrates prepositional phrases effectively.`, ja: `${lemma} のDev例文3`, grammar_ja: '前置詞句' },
                { en: `${lemma} dev example four focuses on application context and clarity.`, ja: `${lemma} のDev例文4`, grammar_ja: '不定詞' },
                { en: `${lemma} dev example five reflects code-review style feedback.`, ja: `${lemma} のDev例文5`, grammar_ja: '分詞構文' },
              ],
              CS: [
                { en: `In computer science, results ${lemma} toward a coherent theory under constraints.`, ja: `${lemma} のCS例文1`, grammar_ja: '倒置' },
                { en: `As complexity grows, algorithms ${lemma} on shared invariants.`, ja: `${lemma} のCS例文2`, grammar_ja: '従属節' },
                { en: `Formal proofs ${lemma} as lemmas link foundational claims.`, ja: `${lemma} のCS例文3`, grammar_ja: '仮定法' },
                { en: `Empirical results ${lemma} across benchmarks when variables are controlled.`, ja: `${lemma} のCS例文4`, grammar_ja: '受動態' },
                { en: `Theoretical bounds ${lemma} under relaxed assumptions.`, ja: `${lemma} のCS例文5`, grammar_ja: '関係代名詞' },
              ],
              LLM: [
                { en: `LLM outputs ${lemma} with more context provided via system prompts.`, ja: `LLM例文1`, grammar_ja: '時制一致' },
                { en: `Fine-tuned models ${lemma} on domain-specific jargon effectively.`, ja: `LLM例文2`, grammar_ja: '前置詞句' },
                { en: `Safety mitigations ${lemma} as alignment objectives are strengthened.`, ja: `LLM例文3`, grammar_ja: '分詞' },
                { en: `Evaluation metrics ${lemma} when test sets reflect real usage.`, ja: `LLM例文4`, grammar_ja: '従属節' },
                { en: `Chain-of-thought traces ${lemma} with improved reasoning over steps.`, ja: `LLM例文5`, grammar_ja: '不定詞' },
              ],
              Business: [
                { en: `Under mild assumptions, iterative updates ${lemma} to a local optimum.`, ja: `Business例1`, grammar_ja: '不定詞' },
                { en: `Multiple systems ${lemma} when signals stabilize over time.`, ja: `Business例2`, grammar_ja: '関係代名詞' },
                { en: `Gradients ${lemma} as learning rates decay across epochs.`, ja: `Business例3`, grammar_ja: '分詞' },
              ],
              Common: [
                { en: `Over months, ideas ${lemma} into a clear plan.`, ja: `Common例1`, grammar_ja: '副詞句' },
                { en: `Our opinions ${lemma} after discussing the options.`, ja: `Common例2`, grammar_ja: '現在完了' },
                { en: `Paths ${lemma} at the main square downtown.`, ja: `Common例3`, grammar_ja: '前置詞句' },
                { en: `Tastes ${lemma} as people grow older and gain experience.`, ja: `Common例4`, grammar_ja: '現在形' },
                { en: `Schedules ${lemma} around the team’s availability.`, ja: `Common例5`, grammar_ja: '三単現' },
                { en: `Trains ${lemma} at this station every hour.`, ja: `Common例6`, grammar_ja: '進行形' },
                { en: `Ghosts linger without a defined sense in the archive.`, ja: `Common例Ghost`, grammar_ja: '動詞句' },
              ],
            },
            etymology: { note: '-', confidence: 'low' },
            study_card: `study of ${lemma}`,
            citations: [{ text: 'citation' }],
            confidence: 'medium',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      
      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('generates WordPack and shows examples', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(toggle);
    });
    await act(async () => {
      await user.keyboard('{Alt>}{1}{/Alt}');
    });

    const input = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    // モデルドロップダウンが表示されている
    expect(screen.getByLabelText('モデル')).toBeInTheDocument();
    // 1回目の生成は sampling 系モデルを選択（temperature を送る前提）
    await act(async () => {
      await user.selectOptions(screen.getByLabelText('モデル'), 'gpt-4o-mini');
    });
    await act(async () => {
      await user.type(input, 'delta');
      await user.click(screen.getByRole('button', { name: '生成' }));
    });

    await screen.findByText('WordPack を生成しました');
    // 自動でプレビューモーダルは開かれない
    expect(screen.queryByRole('dialog', { name: 'WordPack プレビュー' })).not.toBeInTheDocument();

    // fetch が正しいエンドポイントで呼ばれていること（採点APIは呼ばれない）
    const urls = fetchMock.mock.calls.map((c) => (typeof c[0] === 'string' ? c[0] : (c[0] as URL).toString()));
    expect(urls.some((u) => u.endsWith('/api/word/pack'))).toBe(true);
    expect(urls.some((u) => u.endsWith('/api/review/grade_by_lemma'))).toBe(false);

    // リクエストボディに model/temperature が含まれていること（非 reasoning モデルの場合）
    const bodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/pack') : ((c[0] as URL).toString().endsWith('/api/word/pack'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(bodies.some((b) => typeof b.model === 'string' && typeof b.temperature === 'number')).toBe(true);

    // gpt-5-mini を選択時は reasoning/text が入ること
    const user2 = userEvent.setup();
    await act(async () => {
      await user2.selectOptions(screen.getByLabelText('モデル'), 'gpt-5-mini');
      const lemmaInput = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
      lemmaInput.value = '';
      await user2.type(lemmaInput, 'alpha');
      await user2.click(screen.getByRole('button', { name: '生成' }));
    });
    const bodies2 = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/pack') : ((c[0] as URL).toString().endsWith('/api/word/pack'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(bodies2.some((b) => b.model === 'gpt-5-mini' && b.reasoning && b.text && !('temperature' in b))).toBe(true);

    // gpt-5-nano でも reasoning/text が入ること
    const user3 = userEvent.setup();
    await act(async () => {
      await user3.selectOptions(screen.getByLabelText('モデル'), 'gpt-5-nano');
      const lemmaInput2 = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
      lemmaInput2.value = '';
      await user3.type(lemmaInput2, 'beta');
      await user3.click(screen.getByRole('button', { name: '生成' }));
    });
    const bodies3 = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/pack') : ((c[0] as URL).toString().endsWith('/api/word/pack'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(bodies3.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('creates empty WordPack via the new button and shows it', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(toggle);
    });
    await act(async () => {
      await user.keyboard('{Alt>}{1}{/Alt}');
    });

    const input = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
    await act(async () => {
      await user.clear(input);
      await user.type(input, 'epsilon');
      await user.click(screen.getByRole('button', { name: 'WordPackのみ作成' }));
    });

    // 概要セクションが表示され、学習カードは空文字
    await waitFor(() => expect(screen.getByRole('heading', { name: '概要' })).toBeInTheDocument());
    expect(screen.getByText('学習カード要点')).toBeInTheDocument();
    // 呼び出しURL検証
    const urls = fetchMock.mock.calls.map((c) => (typeof c[0] === 'string' ? c[0] : (c[0] as URL).toString()));
    expect(urls.some((u) => u.endsWith('/api/word/packs'))).toBe(true);
    // 直後に詳細取得が走る
    expect(urls.some((u) => /\/api\/word\/packs\/wp:epsilon:/.test(u))).toBe(true);
  });

  it('warms lemma cache on hover and opens/minimizes/restores the lemma window', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(toggle);
    });
    await act(async () => {
      await user.keyboard('{Alt>}{1}{/Alt}');
    });

    const input = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
    await act(async () => {
      await user.clear(input);
      await user.type(input, 'theta');
      await user.click(screen.getByRole('button', { name: 'WordPackのみ作成' }));
    });

    const example = await screen.findByLabelText('example-Common-0');
    const englishRow = within(example).getByRole('button', { name: /英/ });
    const token = within(englishRow).getByText('Paths', { selector: 'span.lemma-token' });

    await act(async () => {
      await user.hover(token);
    });
    await waitFor(() => expect(token).toHaveClass('lemma-known'));

    await act(async () => {
      await user.click(token);
    });

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((call) => (typeof call[0] === 'string' ? call[0] : (call[0] as URL).toString()));
      expect(urls.some((u) => u.includes('/api/word/lemma/Paths'))).toBe(true);
    });
    const windowRegion = await screen.findByRole('complementary', { name: 'Paths のWordPack概要' });
    await waitFor(() => {
      const subtitle = windowRegion.querySelector('.lemma-window-subtitle');
      expect(subtitle).toBeTruthy();
      expect(subtitle).toHaveTextContent('Paths概説');
      expect(subtitle).not.toHaveTextContent('語義タイトルなし');
    });
    expect(within(windowRegion).getAllByText(/Paths概説/).length).toBeGreaterThan(0);

    const minimizeButton = within(windowRegion).getByRole('button', { name: '最小化' });
    await act(async () => {
      await user.click(minimizeButton);
    });
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Paths のWordPack概要' })).not.toBeInTheDocument());

    const trayButton = await screen.findByRole('button', { name: /Paths.*概説/ });
    await act(async () => {
      await user.click(trayButton);
    });
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Paths のWordPack概要' })).toBeInTheDocument());
  });

  it('shows 未生成 tooltip for unknown lemma token and notifies when generating', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(toggle);
    });
    await act(async () => {
      await user.keyboard('{Alt>}{1}{/Alt}');
    });

    const input = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
    await act(async () => {
      await user.clear(input);
      await user.type(input, 'theta');
      await user.click(screen.getByRole('button', { name: 'WordPackのみ作成' }));
    });

    const ghostToken = await screen.findByText((content, element) => {
      if (!element) return false;
      if (!element.matches('span.lemma-token')) return false;
      return content.trim() === 'Ghosts';
    });

    await act(async () => {
      await user.hover(ghostToken);
    });

    await waitFor(() => {
      const tipEl = Array.from(document.querySelectorAll('.lemma-tooltip')).find((el) => el.textContent === '未生成');
      expect(tipEl).toBeTruthy();
    });
    const tooltip = Array.from(document.querySelectorAll('.lemma-tooltip')).find((el) => el.textContent === '未生成') as HTMLElement | undefined;
    expect(tooltip).toBeTruthy();
    expect(tooltip).toHaveAttribute('role', 'tooltip');
    expect(tooltip?.querySelector('button')).toBeNull();
    expect(screen.queryByRole('button', { name: /WordPackを生成/ })).not.toBeInTheDocument();

    await act(async () => {
      await user.click(ghostToken);
    });

    const statuses = await screen.findAllByRole('status');
    const statusLabels = statuses.map((el) => el.getAttribute('aria-label') || '');
    expect(
      statusLabels.some(
        (label) =>
          label === '【Ghosts】の生成処理中... - progress' || label === '【Ghosts】の生成完了！ - success',
      ),
    ).toBe(true);

    const generatedBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/pack') : ((c[0] as URL).toString().endsWith('/api/word/pack'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(generatedBodies.some((body) => body.lemma === 'Ghosts')).toBe(true);
  });

  it('generates unknown lemma when token is clicked directly', async () => {
    const fetchMock = setupFetchMocks();
    renderWithAuth();

    const user = userEvent.setup();
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(toggle);
    });
    await act(async () => {
      await user.keyboard('{Alt>}{1}{/Alt}');
    });

    const input = screen.getByPlaceholderText('見出し語を入力') as HTMLInputElement;
    await act(async () => {
      await user.clear(input);
      await user.type(input, 'theta');
      await user.click(screen.getByRole('button', { name: 'WordPackのみ作成' }));
    });

    const ghostToken = await screen.findByText((content, element) => {
      if (!element) return false;
      if (!element.matches('span.lemma-token')) return false;
      return content.trim() === 'Ghosts';
    });

    await act(async () => {
      await user.hover(ghostToken);
    });

    await act(async () => {
      await user.click(ghostToken);
    });

    const statuses = await screen.findAllByRole('status');
    const statusLabels = statuses.map((el) => el.getAttribute('aria-label') || '');
    expect(
      statusLabels.some(
        (label) =>
          label === '【Ghosts】の生成処理中... - progress' || label === '【Ghosts】の生成完了！ - success',
      ),
    ).toBe(true);
    const generatedBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/pack') : ((c[0] as URL).toString().endsWith('/api/word/pack'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(generatedBodies.some((body) => body.lemma === 'Ghosts')).toBe(true);
  });

  // Note: 二重採点防止のテストは実装の複雑さのため、手動テストで確認
  // モーダルが開いている間は、WordPackPanelのキーハンドラーが無効化されることを確認済み
});
