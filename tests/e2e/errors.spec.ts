import { test, expect } from '@playwright/test';
import { json, mockConfig, seedAuthenticatedSession } from './helpers';

test.describe('異常系ハンドリング', () => {
  test('API タイムアウト時に警告メッセージを表示する', async ({ page, context }) => {
    await seedAuthenticatedSession(context, page);
    await mockConfig(page, { requestTimeoutMs: 50 });

    await page.route('**/api/word/packs?*', (route) => route.fulfill(json({ items: [], total: 0 })));
    await page.route('**/api/word/pack', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 200));
      await route.fulfill(json({ detail: 'late response' }, 504));
    });

    await test.step('Given: WordPack 生成フォームが表示されている', async () => {
      await page.goto('/');
      await page.getByLabel('見出し語').fill('timeout-test');
    });

    await test.step('When: 生成リクエストがタイムアウトする', async () => {
      await page.getByRole('button', { name: '生成' }).click();
    });

    await test.step('Then: タイムアウトの通知が表示される', async () => {
      await expect(page.getByRole('alert').first()).toContainText('タイムアウトしました');
    });
  });

  test('OpenAI API キー未設定時のメッセージを表示する', async ({ page, context }) => {
    await seedAuthenticatedSession(context, page);
    await mockConfig(page, { requestTimeoutMs: 20000 });

    await page.route('**/api/word/packs?*', (route) => route.fulfill(json({ items: [], total: 0 })));
    await page.route('**/api/word/pack', (route) =>
      route.fulfill(
        json(
          {
            detail: {
              message: 'LLM provider authentication failed',
              reason_code: 'AUTH',
              hint: 'OPENAI_API_KEY を確認（有効/権限/課金）。コンテナ環境変数に反映されているか確認。',
            },
          },
          401,
        ),
      ),
    );

    await test.step('Given: WordPack 生成フォームが表示されている', async () => {
      await page.goto('/');
      await page.getByLabel('見出し語').fill('auth-error');
    });

    await test.step('When: OpenAI 認証エラーを受け取る', async () => {
      await page.getByRole('button', { name: '生成' }).click();
    });

    await test.step('Then: API キー未設定に紐づくエラー文言が表示される', async () => {
      await expect(page.getByRole('alert').first()).toContainText('LLM provider authentication failed');
      await expect(page.getByRole('alert').first()).toContainText('OPENAI_API_KEY');
    });
  });
});
