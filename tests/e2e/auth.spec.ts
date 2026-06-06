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
      // メニューの開閉で aria-label が変わるため、aria-controls でトグルボタンを特定する。
      await expect(page.locator('button[aria-controls="app-sidebar"]')).toBeVisible();
    });

    await test.step('Then: ログイン済み UI が表示される', async () => {
      await page.waitForURL('**/', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      // なぜ: ログイン状態の操作はサイドバー下部に集約しているため、メニューを開いて確認する。
      const menuButton = page.locator('button[aria-controls="app-sidebar"]');
      await menuButton.click();
      await expect(page.getByRole('button', { name: 'ログアウト' })).toBeVisible();
      await menuButton.click();
      await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
      await expect(
        page.getByRole('heading', { name: 'WordPack', level: 1, includeHidden: true }),
      ).toHaveCount(1);
    });

    await test.step('Then: サイドバーが閉じており aria-hidden-focus の a11y 違反がない', async () => {
      const menuButton = page.locator('button[aria-controls="app-sidebar"]');
      await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
      await runA11yCheck(page);
    });

    await test.step('Then: main ランドマークと h1 の a11y 違反がない', async () => {
      await runA11yCheck(page, { rules: ['landmark-one-main', 'page-has-heading-one'] });
    });

    await test.step('Then: キーボード操作でメニューを開ける', async () => {
      const menuButton = page.locator('button[aria-controls="app-sidebar"]');
      await menuButton.focus();
      await expect(menuButton).toBeFocused();
      await page.keyboard.press('Enter');
      await expect(menuButton).toHaveAttribute('aria-expanded', 'true');
      await expect
        .poll(async () => menuButton.evaluate((button) => Number(getComputedStyle(button).zIndex)))
        .toBeLessThan(1000);
      await expect
        .poll(async () =>
          menuButton.evaluate((button) => {
            const rect = button.getBoundingClientRect();
            const topElement = document.elementFromPoint(
              rect.left + rect.width / 2,
              rect.top + rect.height / 2,
            );
            return topElement === button || button.contains(topElement);
          }),
        )
        .toBe(true);
    });
  });
});
