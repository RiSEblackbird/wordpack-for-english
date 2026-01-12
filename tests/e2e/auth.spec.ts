import { test, expect } from '@playwright/test';
import { json, mockConfig, seedAuthenticatedSession } from './helpers';

const EMPTY_LIST_RESPONSE = { items: [], total: 0 };

test.describe('認証導線', () => {
  test('Cookie 注入で OAuth ポップアップを使わずにログイン状態へ遷移できる', async ({ page, context }) => {
    await seedAuthenticatedSession(context, page);
    await mockConfig(page, { requestTimeoutMs: 20000 });

    await page.route('**/api/word/packs?*', (route) => route.fulfill(json(EMPTY_LIST_RESPONSE)));

    await test.step('Given: 認証 Cookie と localStorage がセット済み', async () => {
      await page.goto('/');
    });

    await test.step('When: アプリを初期表示する', async () => {
      await expect(page.getByRole('button', { name: 'メニューを開く' })).toBeVisible();
    });

    await test.step('Then: ログイン済み UI が表示される', async () => {
      await expect(page.getByRole('button', { name: 'ログアウト' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'WordPack生成' })).toBeVisible();
    });
  });
});
