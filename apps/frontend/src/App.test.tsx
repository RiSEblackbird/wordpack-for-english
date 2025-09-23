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
    const rect = toggle.getBoundingClientRect();
    expect(Math.round(rect.left)).toBe(0);
    expect(Math.round(rect.top)).toBe(0);
  });

  it('renders the main content without a shift animation', async () => {
    render(<App />);

    await screen.findByRole('heading', { name: 'WordPack' });

    const mainInner = document.querySelector('.main-inner');
    if (!mainInner) {
      throw new Error('main content wrapper not found');
    }

    const styles = window.getComputedStyle(mainInner);
    expect(styles.transitionDuration === '0s' || styles.transitionDuration === '').toBe(true);
    expect(styles.transitionProperty === 'all' || styles.transitionProperty === '').toBe(true);
  });

  it('does not rely on deferred timers to stabilize the layout', async () => {
    render(<App />);

    await screen.findByRole('heading', { name: 'WordPack' });

    const appShell = document.querySelector('.app-shell');
    if (!appShell) {
      throw new Error('app shell not found');
    }

    expect(appShell.style.getPropertyValue('--main-shift')).toBe('');

    const toggle = await screen.findByRole('button', { name: 'メニューを開く' });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(toggle);
    });

    expect(appShell.style.getPropertyValue('--main-shift')).toBe('');

    const mainInner = document.querySelector('.main-inner');
    if (!mainInner) {
      throw new Error('main content wrapper not found');
    }

    const computed = window.getComputedStyle(mainInner);
    expect(mainInner.style.left).toBe('');
    expect(computed.position === 'static' || computed.position === '').toBe(true);
  });

  it('aligns sidebar content to the top (no space-between stretching)', async () => {
    render(<App />);
    const user = userEvent.setup();

    const openButton = await screen.findByRole('button', { name: 'メニューを開く' });
    await act(async () => {
      await user.click(openButton);
    });

    const sidebarContent = document.querySelector('.sidebar-content');
    if (!sidebarContent) throw new Error('sidebar content not found');

    const styles = window.getComputedStyle(sidebarContent as Element);
    // JSDOM は 'flex-start' を返す
    expect(styles.alignContent === 'flex-start' || styles.alignContent === 'start').toBe(true);
  });
});
