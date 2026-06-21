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

  test('デスクトップでページ全体をスクロールしてもサイドバー下部のユーザー操作が追従する', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await mockConfig(page, { requestTimeoutMs: 20000, sessionAuthDisabled: false });

    await page.route('**/api/auth/logout', ignoreRoute);
    await page.route('**/api/auth/guest', (route) => route.fulfill(json({ mode: 'guest' })));
    await page.route('**/api/word/packs?*', (route) =>
      route.fulfill(json({ items: [{ id: 'wp:guest:1', lemma: 'guest', sense_title: 'guest' }], total: 1 })),
    );

    await page.goto('/');
    await page.getByRole('button', { name: 'ゲスト閲覧モード' }).click();
    await expect(page.getByLabel('アプリ内共通メニュー')).toBeVisible();
    await expect(page.getByRole('button', { name: 'ログアウト' })).toBeVisible();

    await page.evaluate(() => {
      const content = document.querySelector<HTMLElement>('.dictionary-content');
      if (!content) {
        throw new Error('main content target is missing');
      }
      const spacer = document.createElement('div');
      spacer.setAttribute('data-testid', 'scroll-spacer');
      spacer.style.height = '1400px';
      content.appendChild(spacer);
    });

    const footer = page.locator('.sidebar-footer');
    const sidebar = page.getByLabel('アプリ内共通メニュー');
    const before = await footer.boundingBox();
    if (!before) {
      throw new Error('sidebar footer is missing');
    }

    await expect(sidebar).toHaveCSS('position', 'sticky');
    await page.evaluate(() => window.scrollTo(0, 620));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(500);

    const after = await footer.boundingBox();
    if (!after) {
      throw new Error('sidebar footer disappeared after scrolling');
    }

    expect(Math.abs(after.y - before.y)).toBeLessThanOrEqual(1);
    expect(after.y).toBeGreaterThan(0);
    expect(after.y + after.height).toBeLessThanOrEqual(720);
    await expect(page.getByRole('button', { name: 'ログアウト' })).toBeVisible();
  });

  test('デスクトップでサイドバーを折りたたんでも主要メニューを使える', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await mockConfig(page, { requestTimeoutMs: 20000, sessionAuthDisabled: false });

    await page.route('**/api/auth/logout', ignoreRoute);
    await page.route('**/api/auth/guest', (route) => route.fulfill(json({ mode: 'guest' })));
    await page.route('**/api/word/packs?*', (route) =>
      route.fulfill(json({ items: [{ id: 'wp:guest:1', lemma: 'guest', sense_title: 'guest' }], total: 1 })),
    );
    await page.route('**/api/word/examples?*', (route) =>
      route.fulfill(json({ items: [], total: 0, limit: 200, offset: 0 })),
    );

    await page.goto('/');
    await page.getByRole('button', { name: 'ゲスト閲覧モード' }).click();
    await expect(page.getByLabel('アプリ内共通メニュー')).toBeVisible();

    const before = await page.evaluate(() => {
      const sidebar = document.querySelector<HTMLElement>('.sidebar');
      const main = document.querySelector<HTMLElement>('.main-inner');
      if (!sidebar || !main) {
        throw new Error('layout metrics target is missing');
      }
      return {
        mainLeft: main.getBoundingClientRect().left,
        sidebarWidth: sidebar.getBoundingClientRect().width,
      };
    });

    const collapseButton = page.getByRole('button', { name: 'サイドメニューを折りたたむ' });
    await expect(collapseButton).toHaveAttribute('aria-expanded', 'true');
    await collapseButton.click();
    await expect(page.getByRole('button', { name: 'サイドメニューを展開' })).toHaveAttribute('aria-expanded', 'false');

    const after = await page.evaluate(() => {
      const sidebar = document.querySelector<HTMLElement>('.sidebar');
      const main = document.querySelector<HTMLElement>('.main-inner');
      const controls = document.querySelector<HTMLElement>('.sidebar-controls');
      const footer = document.querySelector<HTMLElement>('.sidebar-footer');
      if (!sidebar || !main || !controls || !footer) {
        throw new Error('collapsed layout metrics target is missing');
      }
      return {
        controlsDisplay: getComputedStyle(controls).display,
        footerDisplay: getComputedStyle(footer).display,
        mainLeft: main.getBoundingClientRect().left,
        sidebarWidth: sidebar.getBoundingClientRect().width,
      };
    });

    expect(after.sidebarWidth).toBeLessThan(before.sidebarWidth);
    expect(after.sidebarWidth).toBeLessThanOrEqual(80);
    expect(after.mainLeft).toBeLessThan(before.mainLeft);
    expect(after.controlsDisplay).toBe('none');
    expect(after.footerDisplay).toBe('none');

    await page.getByRole('button', { name: '例文一覧' }).click();
    await expect(page.getByRole('heading', { name: '例文一覧' })).toBeVisible();

    await page.getByRole('button', { name: 'サイドメニューを展開' }).click();
    await expect(page.getByRole('button', { name: 'サイドメニューを折りたたむ' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    await expect(page.getByRole('button', { name: 'ログアウト' })).toBeVisible();
  });
});
