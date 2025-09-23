import { render, screen, act, waitFor } from '@testing-library/react';
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

  it('renders WordPack panel and allows generating request UI presence', async () => {
    render(<App />);
    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });
    expect(await screen.findByPlaceholderText('見出し語を入力')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成' })).toBeInTheDocument();
    // モデル選択の存在
    expect(screen.getByLabelText('モデル')).toBeInTheDocument();
  });

  it('allows switching tabs via sidebar navigation', async () => {
    render(<App />);
    const user = userEvent.setup();

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    expect(Math.round(openButton.getBoundingClientRect().left)).toBe(0);
    await act(async () => {
      await user.click(openButton);
    });

    const sidebar = screen.getByLabelText('アプリ内共通メニュー');
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');
    expect(window.getComputedStyle(sidebar).position).toBe('relative');

    const examplesButton = await screen.findByRole('button', { name: '例文一覧' });
    await user.click(examplesButton);

    expect(await screen.findByRole('heading', { name: '例文一覧' })).toBeInTheDocument();
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');

    const appShell = document.querySelector('.app-shell');
    if (!appShell) {
      throw new Error('app shell not found');
    }
    expect(appShell).toHaveClass('sidebar-open');
  });

  it('positions the sidebar flush to the viewport left edge on wide screens without shifting the main column', async () => {
    const originalInnerWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: 1600 });
    await act(async () => {
      window.dispatchEvent(new Event('resize'));
    });

    render(<App />);
    const user = userEvent.setup();

    await screen.findByPlaceholderText('見出し語を入力');

    const mainInner = document.querySelector('.main-inner');
    if (!mainInner) {
      throw new Error('main inner not found');
    }

    const initialLeft = Math.round(mainInner.getBoundingClientRect().left);

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const appShell = document.querySelector('.app-shell');
    const sidebar = document.querySelector('.sidebar');
    if (!appShell || !sidebar) {
      throw new Error('layout elements not found');
    }

    expect(appShell).toHaveClass('sidebar-open');

    await waitFor(() => {
      expect(appShell.style.getPropertyValue('--main-left-padding')).toBe('20px');
      expect(appShell.style.getPropertyValue('--main-right-padding')).toBe('300px');
    });

    const openedLeft = Math.round(mainInner.getBoundingClientRect().left);
    expect(openedLeft).toBe(initialLeft);

    const sidebarRect = sidebar.getBoundingClientRect();
    expect(Math.round(sidebarRect.left)).toBeGreaterThanOrEqual(-1);
    expect(Math.round(sidebarRect.left)).toBeLessThanOrEqual(1);

    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: originalInnerWidth,
    });
    await act(async () => {
      window.dispatchEvent(new Event('resize'));
    });
  });

  it('reduces the main column offset only when the sidebar exceeds the centered margin', async () => {
    const originalInnerWidth = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: 1100 });
    await act(async () => {
      window.dispatchEvent(new Event('resize'));
    });

    render(<App />);
    const user = userEvent.setup();

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const appShell = document.querySelector('.app-shell');
    const sidebar = document.querySelector('.sidebar');
    const mainInner = document.querySelector('.main-inner');
    if (!appShell || !sidebar || !mainInner) {
      throw new Error('layout elements not found');
    }

    await waitFor(() => {
      expect(appShell.style.getPropertyValue('--main-left-padding')).toBe('0px');
      expect(appShell.style.getPropertyValue('--main-right-padding')).toBe('50px');
    });

    const sidebarRect = sidebar.getBoundingClientRect();
    const mainInnerRect = mainInner.getBoundingClientRect();
    expect(Math.round(mainInnerRect.left)).toBe(Math.round(sidebarRect.right));

    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: originalInnerWidth,
    });
    await act(async () => {
      window.dispatchEvent(new Event('resize'));
    });
  });
});
