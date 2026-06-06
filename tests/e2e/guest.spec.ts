import { test, expect } from '@playwright/test';
import { json, mockConfig, ignoreRoute, runA11yCheck } from './helpers';

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
      await page.waitForLoadState('networkidle');
      // ログイン見出しは App.tsx の login-title と一致させ、UI文言の正を明確にする。
      await expect(page.getByRole('heading', { name: 'WordPack にサインイン', level: 2 })).toBeVisible({ timeout: 15000 });
      await expect(page.getByRole('button', { name: 'ゲスト閲覧モード' })).toBeVisible();
    });

    await test.step('Then: ログイン画面で a11y 違反がない', async () => {
      await runA11yCheck(page);
    });

    await test.step('Then: main ランドマークと h1 の a11y 違反がない', async () => {
      await runA11yCheck(page, { rules: ['landmark-one-main', 'page-has-heading-one'] });
    });

    await test.step('When: キーボードでゲスト閲覧モードを選択する', async () => {
      const guestButton = page.getByRole('button', { name: 'ゲスト閲覧モード' });

      /**
       * Googleログインボタンは外部SDKが iframe/Shadow DOM を注入するため、E2E では
       * 「ゲスト導線がキーボードで到達・実行できる」ことを観測点にする。
       */
      await page.keyboard.press('Tab');
      // 直前のフォーカス位置は環境依存のため、確実にゲストボタンへフォーカスして Enter で実行する。
      await guestButton.focus();
      await expect(guestButton).toBeFocused();
      await page.keyboard.press('Enter');
    });

    await test.step('Then: ゲストバッジと操作制限が表示される', async () => {
      await expect(page.getByText('ゲスト閲覧モード')).toBeVisible();
      await expect(page.getByLabel('アプリ内共通メニュー')).toBeVisible();
      await expect(page.getByRole('button', { name: '作成を開始' })).toBeDisabled();
    });
  });

  test('モバイル下部ナビの高さを本文下余白に反映する', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await mockConfig(page, { requestTimeoutMs: 20000, sessionAuthDisabled: false });

    await page.route('**/api/auth/logout', ignoreRoute);
    await page.route('**/api/auth/guest', (route) => route.fulfill(json({ mode: 'guest' })));
    await page.route('**/api/word/packs?*', (route) =>
      route.fulfill(json({ items: [{ id: 'wp:guest:1', lemma: 'guest', sense_title: 'guest' }], total: 1 })),
    );

    await page.goto('/');
    await page.getByRole('button', { name: 'ゲスト閲覧モード' }).click();
    await expect(page.getByRole('navigation', { name: 'モバイル主要メニュー' })).toBeVisible();

    const metrics = await page.evaluate(() => {
      const nav = document.querySelector<HTMLElement>('.dictionary-bottom-nav');
      const shell = document.querySelector<HTMLElement>('.dictionary-shell');
      const mainInner = document.querySelector<HTMLElement>('.main-inner');
      if (!nav || !shell || !mainInner) {
        throw new Error('bottom nav metrics target is missing');
      }
      const navHeight = Math.ceil(nav.getBoundingClientRect().height);
      const reservedHeight = getComputedStyle(shell).getPropertyValue('--bottom-nav-height').trim();
      const paddingBottom = Number.parseFloat(getComputedStyle(mainInner).paddingBottom);
      return { navHeight, paddingBottom, reservedHeight };
    });

    expect(metrics.navHeight).toBeGreaterThan(0);
    expect(metrics.reservedHeight).toBe(`${metrics.navHeight}px`);
    expect(metrics.paddingBottom).toBeGreaterThanOrEqual(metrics.navHeight + 20);
  });
});
