import { test, expect } from '@playwright/test';
import { json, mockConfig, ignoreRoute } from './helpers';

test.describe('ゲストモード', () => {
  test('ログイン画面からゲスト閲覧へ遷移できる', async ({ page }) => {
    await mockConfig(page, { requestTimeoutMs: 20000, sessionAuthDisabled: false });

    await page.route('**/api/auth/logout', ignoreRoute);
    await page.route('**/api/auth/guest', (route) => route.fulfill(json({ mode: 'guest' })));
    await page.route('**/api/word/packs?*', (route) =>
      route.fulfill(json({ items: [{ id: 'wp:guest:1', lemma: 'guest', sense_title: 'guest' }], total: 1 })),
    );

    await test.step('Given: 未認証のログイン画面が表示されている', async () => {
      await page.goto('/');
      await expect(page.getByRole('heading', { name: 'WordPack にサインイン' })).toBeVisible();
    });

    await test.step('When: ゲスト閲覧モードを選択する', async () => {
      await page.getByRole('button', { name: 'ゲスト閲覧モード' }).click();
    });

    await test.step('Then: ゲストバッジと操作制限が表示される', async () => {
      await expect(page.getByText('ゲスト閲覧モード')).toBeVisible();
      await expect(page.getByRole('button', { name: '生成' })).toBeDisabled();
    });
  });
});
