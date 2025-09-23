import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import '@testing-library/jest-dom';

describe('App navigation', () => {
  it('renders WordPack by default and navigates with keyboard', async () => {
    render(<App />);

    // デフォルトは WordPack（見出し語入力が見える） - 設定読み込み完了を待つ
    expect(await screen.findByPlaceholderText('見出し語を入力')).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{2}{/Alt}');
    });
    expect(await screen.findByLabelText('発音を有効化')).toBeInTheDocument();
    // temperature 入力の存在
    expect(await screen.findByLabelText('temperature')).toBeInTheDocument();
  });

  it('opens the sidebar with the hamburger button and keeps it visible after selecting a tab', async () => {
    render(<App />);
    const user = userEvent.setup();

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const sidebar = screen.getByLabelText('アプリ内共通メニュー');
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');

    const computed = window.getComputedStyle(sidebar);
    expect(computed.display).toBe('block');
    expect(sidebar.getAttribute('style')).toContain('280px');

    const examplesButton = await screen.findByRole('button', { name: '例文一覧' });
    await act(async () => {
      await user.click(examplesButton);
    });

    expect(await screen.findByRole('heading', { name: '例文一覧' })).toBeInTheDocument();
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');

    const appShell = document.querySelector('.app-shell');
    const mainInner = document.querySelector('.main-inner');
    if (!appShell || !mainInner) {
      throw new Error('layout elements not found');
    }
    expect(appShell).toHaveClass('sidebar-open');

    const sidebarRect = sidebar.getBoundingClientRect();
    const mainRect = mainInner.getBoundingClientRect();
    expect(Math.round(sidebarRect.left)).toBe(0);
    expect(mainRect.left).toBeGreaterThanOrEqual(sidebarRect.right);
  });

  it('places the hamburger button on the viewport left edge', async () => {
    render(<App />);
    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    expect(Math.round(toggle.getBoundingClientRect().left)).toBe(0);
  });

  it('keeps the main content position when enough horizontal margin remains', async () => {
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 1600,
    });

    render(<App />);
    const user = userEvent.setup();

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const appShell = document.querySelector('.app-shell');
    if (!appShell) {
      throw new Error('app shell not found');
    }

    const shiftValue = parseFloat(appShell.style.getPropertyValue('--main-shift'));
    expect(shiftValue).toBeCloseTo(-140, 1);

    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: originalWidth,
    });
    window.dispatchEvent(new Event('resize'));
  });

  it('does not move the main content unnecessarily on tighter viewports', async () => {
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 1100,
    });

    render(<App />);
    const user = userEvent.setup();

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const appShell = document.querySelector('.app-shell');
    if (!appShell) {
      throw new Error('app shell not found');
    }

    const shiftValue = parseFloat(appShell.style.getPropertyValue('--main-shift'));
    expect(shiftValue).toBeCloseTo(0, 1);

    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: originalWidth,
    });
    window.dispatchEvent(new Event('resize'));
  });
});
