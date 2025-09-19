import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { App } from './App';
import { vi } from 'vitest';

describe('ArticleImportPanel model/params wiring (mocked fetch)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function setupFetchMocks() {
    const mock = vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString();
      if (url.endsWith('/api/config') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({ request_timeout_ms: 60000 }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }
      if (url.endsWith('/api/article/import') && init?.method === 'POST') {
        return new Response(
          JSON.stringify({ id: 'art:abcd1234' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/article/generate_and_import') && init?.method === 'POST') {
        return new Response(
          JSON.stringify({ lemma: 'test', word_pack_id: 'wp:test:abcd', category: 'Common', generated_examples: 2, article_ids: ['art:1', 'art:2'] }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/article/art:abcd1234') && (!init || (init && (!init.method || init.method === 'GET')))) {
        return new Response(
          JSON.stringify({
            id: 'art:abcd1234',
            title_en: 'Title',
            body_en: 'Body EN',
            body_ja: 'Body JA',
            llm_model: 'gpt-5-mini',
            llm_params: 'reasoning.effort=minimal;text.verbosity=medium',
            related_word_packs: [
              { word_pack_id: 'wp:regen:1', lemma: 'alpha', status: 'existing', is_empty: false },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/api/word/packs/wp:regen:1/regenerate') && init?.method === 'POST') {
        return new Response(
          JSON.stringify({ ok: true }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return new Response('not found', { status: 404 });
    });
    return mock;
  }

  it('sends model/temperature for sampling model on import', async () => {
    const fetchMock = setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    const importTab = await screen.findByRole('button', { name: '文章インポート' });
    await act(async () => {
      await user.click(importTab);
    });

    // モデルUIが表示される
    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-4o-mini');
    });

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello world');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    // リクエスト検証
    const calls = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(calls.length).toBeGreaterThan(0);
    expect(calls.some((b) => b.model === 'gpt-4o-mini' && typeof b.temperature === 'number' && !('reasoning' in b) && !('text_opts' in b) === false)).toBe(true);
  });

  it('sends reasoning/text_opts for gpt-5-mini on import, and reasoning/text on generate_and_import', async () => {
    const fetchMock = setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    const importTab = await screen.findByRole('button', { name: '文章インポート' });
    await act(async () => {
      await user.click(importTab);
    });

    // gpt-5-mini 選択で追加UIが表示
    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-5-mini');
    });
    expect(screen.getByLabelText('reasoning.effort')).toBeInTheDocument();
    expect(screen.getByLabelText('text.verbosity')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello world 2');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const importBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(importBodies.some((b) => b.model === 'gpt-5-mini' && b.reasoning && b.text_opts && !('temperature' in b))).toBe(true);

    // 生成＆インポートでも同様のパラメータ（text キー）
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /生成＆インポート/ }));
    });
    const genBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/generate_and_import') : ((c[0] as URL).toString().endsWith('/api/article/generate_and_import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(genBodies.some((b) => b.model === 'gpt-5-mini' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('sends reasoning params for gpt-5-nano on both import and generate_and_import', async () => {
    const fetchMock = setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    const importTab = await screen.findByRole('button', { name: '文章インポート' });
    await act(async () => {
      await user.click(importTab);
    });

    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-5-nano');
    });
    // 追加UIが表示される
    expect(screen.getByLabelText('reasoning.effort')).toBeInTheDocument();
    expect(screen.getByLabelText('text.verbosity')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello world nano');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const importBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/import') : ((c[0] as URL).toString().endsWith('/api/article/import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(importBodies.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text_opts && !('temperature' in b))).toBe(true);

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /生成＆インポート/ }));
    });
    const genBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/article/generate_and_import') : ((c[0] as URL).toString().endsWith('/api/article/generate_and_import'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(genBodies.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('uses selected model for regenerate from import result modal (reasoning model)', async () => {
    const fetchMock = setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    const importTab = await screen.findByRole('button', { name: '文章インポート' });
    await act(async () => {
      await user.click(importTab);
    });

    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-5-nano');
    });
    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello regenerate');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const regenBtn = await screen.findByRole('button', { name: '生成' });
    await act(async () => {
      await user.click(regenBtn);
    });

    const regenBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/packs/wp:regen:1/regenerate') : ((c[0] as URL).toString().endsWith('/api/word/packs/wp:regen:1/regenerate'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(regenBodies.some((b) => b.model === 'gpt-5-nano' && b.reasoning && b.text && !('temperature' in b))).toBe(true);
  });

  it('uses selected model for regenerate from import result modal (sampling model)', async () => {
    const fetchMock = setupFetchMocks();
    render(<App />);

    const user = userEvent.setup();
    const importTab = await screen.findByRole('button', { name: '文章インポート' });
    await act(async () => {
      await user.click(importTab);
    });

    const modelSelect = await screen.findByLabelText('モデル');
    await act(async () => {
      await user.selectOptions(modelSelect, 'gpt-4o-mini');
    });
    const textarea = screen.getByPlaceholderText('文章を貼り付け（日本語/英語）');
    await act(async () => {
      await user.type(textarea, 'hello regenerate sampling');
      await user.click(screen.getByRole('button', { name: 'インポート' }));
    });

    const regenBtn = await screen.findByRole('button', { name: '生成' });
    await act(async () => {
      await user.click(regenBtn);
    });

    const regenBodies = fetchMock.mock.calls
      .filter((c) => (typeof c[0] === 'string' ? (c[0] as string).endsWith('/api/word/packs/wp:regen:1/regenerate') : ((c[0] as URL).toString().endsWith('/api/word/packs/wp:regen:1/regenerate'))))
      .map((c) => (c[1]?.body ? JSON.parse(c[1]!.body as string) : {}));
    expect(regenBodies.some((b) => b.model === 'gpt-4o-mini' && typeof b.temperature === 'number' && !('reasoning' in b) && !('text' in b))).toBe(true);
  });
});


