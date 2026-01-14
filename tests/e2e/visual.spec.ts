import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import { json, mockConfig, seedAuthenticatedSession } from './helpers';

const STATIC_MASK_SELECTOR = '[aria-live="polite"]';

const disableAnimations = async (page: Page): Promise<void> => {
  /**
   * 視覚スナップショットの差分を安定化するため、全要素のアニメーション/トランジションを無効化する。
   * なぜ: トーストの経過時間やフェードがフレークの温床になるため。
   */
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
      ${STATIC_MASK_SELECTOR} {
        visibility: hidden !important;
      }
    `,
  });
};

const openSidebarAndSelect = async (
  page: Page,
  label: string,
  options: { keepOpen?: boolean } = {},
): Promise<void> => {
  /**
   * サイドバー経由でタブ移動を統一する。
   * なぜ: どの表示幅でも同じ操作でメニュー遷移できるよう手順を固定するため。
   */
  const openButton = page.getByRole('button', { name: 'メニューを開く' });
  if ((await openButton.count()) > 0) {
    await openButton.click();
  }
  await page.getByRole('button', { name: label }).click();
  if (!options.keepOpen) {
    /**
     * メニューを閉じる操作はキーボード（Enter）で行い、オーバーレイの pointer-events による
     * クリック遮断を回避する。
     * なぜ: 画面幅やレイアウト差でサイドバー要素がボタン上に重なり、ポインタ操作が
     *      不安定になることがあるため（a11y 的にはキーボード操作でも閉じられるべき）。
     */
    const closeButton = page.getByRole('button', { name: 'メニューを閉じる' });
    if ((await closeButton.count()) > 0) {
      await closeButton.focus();
      await page.keyboard.press('Enter');
      await expect(page.getByRole('button', { name: 'メニューを開く' })).toBeVisible();
    }
  }
};

const prepareAuthenticatedPage = async (context: BrowserContext, page: Page): Promise<void> => {
  /**
   * 認証済み状態でUIを固定する。
   * なぜ: OAuthポップアップやセッション不整合を避け、画面描画に集中するため。
   */
  await seedAuthenticatedSession(context, page);
  await mockConfig(page, { requestTimeoutMs: 20000, sessionAuthDisabled: false });
};

const mockWordPackList = async (page: Page): Promise<void> => {
  /**
   * WordPack一覧を固定データで再現する。
   * なぜ: 視覚リグレッションの対象をデータ変動から切り離すため。
   */
  await page.route('**/api/word/packs?**', (route) =>
    route.fulfill(
      json({
        items: [
          {
            id: 'wp:e2e:alpha',
            lemma: 'alpha',
            sense_title: 'alpha 概説',
            created_at: '2024-01-10T09:15:00Z',
            updated_at: '2024-01-12T12:00:00Z',
            is_empty: false,
            guest_public: true,
            examples_count: {
              Dev: 3,
              CS: 1,
              LLM: 0,
              Business: 2,
              Common: 4,
            },
            checked_only_count: 1,
            learned_count: 2,
          },
          {
            id: 'wp:e2e:bravo',
            lemma: 'bravo',
            sense_title: 'bravo 概説',
            created_at: '2024-01-08T08:30:00Z',
            updated_at: '2024-01-11T18:05:00Z',
            is_empty: true,
            guest_public: false,
            examples_count: {
              Dev: 0,
              CS: 0,
              LLM: 2,
              Business: 0,
              Common: 1,
            },
            checked_only_count: 0,
            learned_count: 0,
          },
          {
            id: 'wp:e2e:charlie',
            lemma: 'charlie',
            sense_title: 'charlie 概説',
            created_at: '2024-01-05T03:20:00Z',
            updated_at: '2024-01-06T11:10:00Z',
            is_empty: false,
            guest_public: true,
            examples_count: {
              Dev: 5,
              CS: 0,
              LLM: 0,
              Business: 1,
              Common: 2,
            },
            checked_only_count: 2,
            learned_count: 1,
          },
        ],
        total: 3,
        limit: 200,
        offset: 0,
      }),
    ),
  );
};

const mockExampleList = async (page: Page): Promise<void> => {
  /**
   * 例文一覧の固定レスポンスを用意する。
   * なぜ: ランダム性のある集計結果を排除し、UI差分のみに集中するため。
   */
  await page.route('**/api/word/examples?**', (route) =>
    route.fulfill(
      json({
        items: [
          {
            id: 101,
            word_pack_id: 'wp:e2e:alpha',
            lemma: 'alpha',
            category: 'Dev',
            en: 'We shipped the alpha build yesterday.',
            ja: '昨日アルファ版を出荷しました。',
            grammar_ja: '第4文型の例。',
            created_at: '2024-01-04T06:30:00Z',
            word_pack_updated_at: '2024-01-12T12:00:00Z',
            checked_only_count: 1,
            learned_count: 0,
            transcription_typing_count: 120,
          },
          {
            id: 102,
            word_pack_id: 'wp:e2e:bravo',
            lemma: 'bravo',
            category: 'Common',
            en: 'Bravo! That presentation was clear.',
            ja: 'ブラボー！あの発表は分かりやすかった。',
            grammar_ja: null,
            created_at: '2024-01-02T03:10:00Z',
            word_pack_updated_at: '2024-01-11T18:05:00Z',
            checked_only_count: 0,
            learned_count: 1,
            transcription_typing_count: 48,
          },
        ],
        total: 2,
        limit: 200,
        offset: 0,
      }),
    ),
  );
};

const mockArticleImport = async (page: Page): Promise<void> => {
  /**
   * 文章インポートの確定画面を再現するため、POST/GETを一貫したモックに固定する。
   * なぜ: モーダル内容が揺れるとスクリーンショットが不安定になるため。
   */
  const articleDetail = {
    id: 'article:e2e:001',
    title_en: 'A short briefing on alpha releases',
    body_en: 'Alpha releases validate core workflows for early adopters.',
    body_ja: 'アルファ版は初期利用者向けに主要なワークフローを検証します。',
    notes_ja: '例文抽出はDevカテゴリを優先。',
    llm_model: 'gpt-4o-mini',
    llm_params: 'temperature=0.6',
    generation_category: 'Dev',
    related_word_packs: [
      { word_pack_id: 'wp:e2e:alpha', lemma: 'alpha', status: 'existing' },
      { word_pack_id: 'wp:e2e:beta', lemma: 'beta', status: 'created', is_empty: true },
    ],
    warnings: ['既存WordPackが1件含まれています。'],
    created_at: '2024-01-10T09:15:00Z',
    updated_at: '2024-01-10T09:16:10Z',
    generation_started_at: '2024-01-10T09:15:00Z',
    generation_completed_at: '2024-01-10T09:16:00Z',
    generation_duration_ms: 60000,
  };

  await page.route('**/api/article/import', (route) => {
    if (route.request().method() !== 'POST') {
      return route.fulfill(json({ detail: 'Not found' }, 404));
    }
    return route.fulfill(json({ id: articleDetail.id }));
  });

  await page.route('**/api/article?**', (route) =>
    route.fulfill(
      json({
        items: [
          {
            id: 'article:e2e:001',
            title_en: 'A short briefing on alpha releases',
            created_at: '2024-01-10T09:15:00Z',
            updated_at: '2024-01-10T09:16:10Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }),
    ),
  );

  // 記事IDにコロンが含まれるため、URL エンコード有無の差分を吸収してモックする。
  await page.route('**/api/article/article*e2e*001', (route) => route.fulfill(json(articleDetail)));
};

test.describe('ビジュアル回帰: 主要画面', () => {
  test('WordPack一覧（保存済み一覧）', async ({ page, context }) => {
    await prepareAuthenticatedPage(context, page);
    await mockWordPackList(page);

    await page.goto('/');
    await disableAnimations(page);

    await expect(page.getByRole('heading', { name: '保存済みWordPack一覧' })).toBeVisible();
    await expect(page.getByText('alpha')).toBeVisible();

    await expect(page).toHaveScreenshot('wordpack-list.png', {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      mask: [page.locator(STATIC_MASK_SELECTOR)],
    });
  });

  test('文章インポート（例文からのインポート確認UI）', async ({ page, context }) => {
    await prepareAuthenticatedPage(context, page);
    await mockWordPackList(page);
    await mockArticleImport(page);

    await page.goto('/');
    await disableAnimations(page);

    await openSidebarAndSelect(page, '文章インポート', { keepOpen: true });
    // 「文章」はセクション名やチェックボックスにも使われるため、入力欄をプレースホルダーで特定する。
    await page
      .getByPlaceholder('文章を貼り付け（日本語/英語）')
      .fill('Alpha releases validate core workflows.');
    // 「インポート」を含むボタン（例: 文章インポート/生成＆インポート）が複数あるため、完全一致で確定する。
    const importResponse = page.waitForResponse(
      (res) =>
        res.request().method() === 'POST' &&
        /\/api\/article\/import(?:\?|$)/.test(res.url()) &&
        res.ok(),
    );
    const detailResponse = page.waitForResponse(
      (res) => /\/api\/article\/article(?:%3A|:)?e2e(?:%3A|:)?001(?:\?|$)/.test(res.url()) && res.ok(),
    );
    await page.getByRole('button', { name: 'インポート', exact: true }).click();
    await importResponse;
    await detailResponse;

    // サイドバーはレイアウト上の重なりで視認性が落ちることがあるため、キーボード操作で閉じる。
    // なぜ: pointer-events の重なりでクリックが遮られるケースがあるため。
    const closeMenuButton = page.getByRole('button', { name: 'メニューを閉じる' });
    if ((await closeMenuButton.count()) > 0) {
      await closeMenuButton.focus();
      await page.keyboard.press('Enter');
    } else {
      await page.keyboard.press('Escape');
    }

    // 確認 UI は実装都合（モーダル/パネル）で role やラベルが変わり得るため、
    // ユーザーに見える内容（モックで固定した文言）で完了を待つ。
    await expect(page.getByText('既存WordPackが1件含まれています。')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('A short briefing on alpha releases')).toBeVisible();

    await expect(page).toHaveScreenshot('article-import-confirmation.png', {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      mask: [page.locator(STATIC_MASK_SELECTOR)],
    });
  });

  test('例文一覧', async ({ page, context }) => {
    await prepareAuthenticatedPage(context, page);
    await mockWordPackList(page);
    await mockExampleList(page);

    await page.goto('/');
    await disableAnimations(page);

    await openSidebarAndSelect(page, '例文一覧');
    await expect(page.getByRole('heading', { name: '例文一覧' })).toBeVisible();
    await expect(page.getByText('We shipped the alpha build yesterday.')).toBeVisible();

    await expect(page).toHaveScreenshot('example-list.png', {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      mask: [page.locator(STATIC_MASK_SELECTOR)],
    });
  });

  test('設定ダイアログ（SettingsPanel表示）', async ({ page, context }) => {
    await prepareAuthenticatedPage(context, page);
    await mockWordPackList(page);

    await page.goto('/');
    await disableAnimations(page);

    await openSidebarAndSelect(page, '設定');
    await expect(page.getByRole('button', { name: 'ログアウト（Google セッションを終了）' })).toBeVisible();

    await expect(page).toHaveScreenshot('settings-panel.png', {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      mask: [page.locator(STATIC_MASK_SELECTOR)],
    });
  });
});
