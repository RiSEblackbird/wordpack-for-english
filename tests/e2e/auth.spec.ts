import { test, expect } from '@playwright/test';
import { json, mockConfig, runA11yCheck, seedAuthenticatedSession } from './helpers';

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
      await page.waitForURL('**/', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      // なぜ: ログイン後の常設UI（ヘッダー）に存在し、画面文言の揺らぎに強い要素を採用する。
      await expect(page.getByRole('button', { name: 'ログアウト' })).toBeVisible();
      await expect(
        page.getByRole('heading', { name: 'WordPack', level: 1, includeHidden: true }),
      ).toHaveCount(1);
    });

    await test.step('Then: サイドバーが閉じており aria-hidden-focus の a11y 違反がない', async () => {
      const menuButton = page.getByRole('button', { name: 'メニューを開く' });
      await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
      await runA11yCheck(page);
    });

    await test.step('Then: main ランドマークと h1 の a11y 違反がない', async () => {
      await runA11yCheck(page, { rules: ['landmark-one-main', 'page-has-heading-one'] });
    });

    await test.step('Then: キーボード操作でメニューを開ける', async () => {
      await page.keyboard.press('Tab');
      const menuButton = page.getByRole('button', { name: 'メニューを開く' });
      await expect(menuButton).toBeFocused();
      await page.keyboard.press('Enter');
      await expect(menuButton).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
