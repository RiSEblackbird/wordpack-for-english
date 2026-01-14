import { test, expect } from '@playwright/test';
import { json, mockConfig, runA11yCheck, seedAuthenticatedSession } from './helpers';

type ExampleItem = { en: string; ja: string; grammar_ja?: string };

type Examples = {
  Dev: ExampleItem[];
  CS: ExampleItem[];
  LLM: ExampleItem[];
  Business: ExampleItem[];
  Common: ExampleItem[];
};

type WordPack = {
  lemma: string;
  sense_title: string;
  pronunciation: {
    ipa_GA: string | null;
    ipa_RP: string | null;
    syllables: string | null;
    stress_index: number | null;
    linking_notes: string[];
  };
  senses: Array<{ id: string; gloss_ja: string; definition_ja: string; nuances_ja: string; patterns: string[]; synonyms: string[]; antonyms: string[]; register: string; notes_ja: string }>;
  collocations: {
    general: { verb_object: string[]; adj_noun: string[]; prep_noun: string[] };
    academic: { verb_object: string[]; adj_noun: string[]; prep_noun: string[] };
  };
  contrast: string[];
  examples: Examples;
  etymology: { note: string; confidence: string };
  study_card: string;
  citations: Array<{ text: string }>;
  confidence: string;
};

const createBaseWordPack = (lemma: string): WordPack => ({
  lemma,
  sense_title: `${lemma} 概説`,
  pronunciation: {
    ipa_GA: null,
    ipa_RP: null,
    syllables: null,
    stress_index: null,
    linking_notes: [],
  },
  senses: [
    {
      id: 's1',
      gloss_ja: '意味',
      definition_ja: '定義',
      nuances_ja: 'ニュアンス',
      patterns: ['p1'],
      synonyms: ['syn'],
      antonyms: ['ant'],
      register: 'formal',
      notes_ja: '注意',
    },
  ],
  collocations: {
    general: { verb_object: [], adj_noun: [], prep_noun: [] },
    academic: { verb_object: [], adj_noun: [], prep_noun: [] },
  },
  contrast: [],
  examples: {
    Dev: [{ en: `${lemma} dev example`, ja: `${lemma} の例文`, grammar_ja: '第3文型' }],
    CS: [],
    LLM: [],
    Business: [],
    Common: [],
  },
  etymology: { note: '-', confidence: 'low' },
  study_card: `${lemma} study`,
  citations: [],
  confidence: 'medium',
});

const cloneWordPack = (wordPack: WordPack): WordPack => JSON.parse(JSON.stringify(wordPack));

// 例文の追加・削除・再生成を1テスト内で完結させるため、
// メモリ内ストアで WordPack データを更新する。
const createWordPackStore = () => {
  const wordPackId = 'wp:e2e:001';
  let currentWordPack: WordPack | null = null;

  const create = (lemma: string) => {
    currentWordPack = createBaseWordPack(lemma);
    return wordPackId;
  };

  const read = () => (currentWordPack ? cloneWordPack(currentWordPack) : null);

  const addExamples = (category: keyof Examples) => {
    if (!currentWordPack) return;
    const next = currentWordPack.examples[category];
    next.push(
      { en: `${currentWordPack.lemma} extra example 1`, ja: '追加例文1' },
      { en: `${currentWordPack.lemma} extra example 2`, ja: '追加例文2' },
    );
  };

  const deleteExample = (category: keyof Examples, index: number) => {
    if (!currentWordPack) return;
    currentWordPack.examples[category].splice(index, 1);
  };

  const regenerate = () => {
    if (!currentWordPack) return null;
    currentWordPack = {
      ...currentWordPack,
      sense_title: `${currentWordPack.lemma} 再生成済み`,
    };
    return cloneWordPack(currentWordPack);
  };

  const reset = () => {
    currentWordPack = null;
  };

  return {
    wordPackId,
    create,
    read,
    addExamples,
    deleteExample,
    regenerate,
    reset,
  };
};

test.describe('WordPack 操作', () => {
  test('例文の追加/削除/再生成を1本のシナリオで完結できる', async ({ page, context }) => {
    const store = createWordPackStore();

    await seedAuthenticatedSession(context, page);
    await mockConfig(page, { requestTimeoutMs: 20000 });

    await page.route('**/api/word/packs?*', (route) => route.fulfill(json({ items: [], total: 0 })));

    await page.route('**/api/word/packs', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fulfill(json({ detail: 'Not found' }, 404));
        return;
      }
      const body = route.request().postDataJSON() as { lemma?: string } | null;
      const id = store.create(body?.lemma ?? 'alpha');
      await route.fulfill(json({ id }));
    });

    await page.route('**/api/word/packs/**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();

      if (url.includes('/examples/') && method === 'POST') {
        const match = url.match(/examples\/([^/]+)\/generate/);
        const category = (match?.[1] ?? 'Dev') as keyof Examples;
        store.addExamples(category);
        await route.fulfill(json({ ok: true }));
        return;
      }

      if (url.includes('/examples/') && method === 'DELETE') {
        const match = url.match(/examples\/([^/]+)\/(\d+)/);
        const category = (match?.[1] ?? 'Dev') as keyof Examples;
        const index = Number(match?.[2] ?? 0);
        store.deleteExample(category, index);
        await route.fulfill(json({ ok: true }));
        return;
      }

      if (url.endsWith('/regenerate/async') && method === 'POST') {
        await route.fulfill(json({ job_id: 'job:e2e:1', status: 'running' }));
        return;
      }

      if (url.includes('/regenerate/jobs/') && method === 'GET') {
        const result = store.regenerate();
        await route.fulfill(json({ job_id: 'job:e2e:1', status: 'succeeded', result }));
        return;
      }

      if (method === 'GET') {
        const payload = store.read();
        await route.fulfill(payload ? json(payload) : json({ detail: 'Not found' }, 404));
        return;
      }

      await route.fulfill(json({ detail: 'Not found' }, 404));
    });

    await test.step('Given: WordPack を作成して編集可能な状態にする', async () => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await expect(page.getByRole('heading', { name: 'WordPack', level: 1 })).toBeVisible();
      await runA11yCheck(page);
      // WordPack の入力・作成ボタンはサイドバー内に配置されているため、メニューを開く。
      const menuToggle = page.locator('button[aria-controls="app-sidebar"]');
      await expect(menuToggle).toBeVisible();
      await menuToggle.click();
      await expect(menuToggle).toHaveAttribute('aria-expanded', 'true');
      await page.getByLabel('見出し語').fill('alpha');
      // 入力バリデーション完了後にボタンが有効化されるため、明示的に待機してから押下する。
      const generateButton = page.getByRole('button', { name: '生成' });
      const createWordPackButton = page.getByRole('button', { name: 'WordPackのみ作成' });
      await expect(createWordPackButton).toBeEnabled();
      await page.getByLabel('見出し語').focus();
      await page.keyboard.press('Tab');
      // タブ順は「生成」→「WordPackのみ作成」の順に並ぶため、2回で作成ボタンへ到達する。
      await expect(generateButton).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(createWordPackButton).toBeFocused();
      await page.keyboard.press('Space');
      await expect(page.getByRole('heading', { name: /例文/ })).toBeVisible();
    });

    await test.step('When: 例文を追加生成する', async () => {
      await page.getByRole('button', { name: 'generate-examples-Dev' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: 'Dev に例文を2件追加しました' }).first(),
      ).toBeVisible();
    });

    await test.step('Then: 例文の件数が増えている', async () => {
      await expect(page.getByText('Dev (3件)')).toBeVisible();
    });

    await test.step('When: 追加した例文を削除する', async () => {
      await page.getByRole('button', { name: 'delete-example-Dev-0' }).click();
      await page.getByRole('button', { name: 'はい' }).click();
      await expect(
        page.getByRole('status').filter({ hasText: '例文を削除しました' }).first(),
      ).toBeVisible();
    });

    await test.step('Then: 例文の件数が減っている', async () => {
      await expect(page.getByText('Dev (2件)')).toBeVisible();
    });

    await test.step('When: WordPack を再生成する', async () => {
      await page.getByRole('button', { name: '再生成' }).click();
    });

    await test.step('Then: 再生成完了メッセージが出る', async () => {
      await expect(
        page.getByRole('status').filter({ hasText: 'WordPackを再生成しました' }).first(),
      ).toBeVisible();
    });

    await test.step('Then: テストデータを後片付けする', async () => {
      store.reset();
      await expect(page.getByRole('heading', { name: /例文/ })).toBeVisible();
    });
  });
});
