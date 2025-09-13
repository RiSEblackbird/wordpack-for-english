import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import '@testing-library/jest-dom';

describe('App navigation', () => {
  it('renders WordPack by default and navigates with keyboard', async () => {
    render(<App />);

    // デフォルトは WordPack（見出し語入力が見える）
    expect(screen.getByPlaceholderText('見出し語を入力')).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{2}{/Alt}');
    });
    expect(screen.getByPlaceholderText('英文を入力してください')).toBeInTheDocument();

    await act(async () => {
      await user.keyboard('{Alt>}{3}{/Alt}');
    });
    expect(screen.getByPlaceholderText('段落を入力してください')).toBeInTheDocument();

    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });
    // WordPack タブに戻る
    expect(screen.getByPlaceholderText('見出し語を入力')).toBeInTheDocument();

    await act(async () => {
      await user.keyboard('{Alt>}{5}{/Alt}');
    });
    expect(screen.getByLabelText('発音を有効化')).toBeInTheDocument();
    // temperature 入力の存在
    expect(screen.getByLabelText('temperature')).toBeInTheDocument();

    await act(async () => {
      await user.keyboard('{Alt>}{1}{/Alt}');
      await user.keyboard('/');
    });
    const cardPanel = document.getElementById('card-panel')!;
    expect(cardPanel).toHaveFocus();
  });

  it('renders WordPack panel and allows generating request UI presence', async () => {
    render(<App />);
    const user = userEvent.setup();
    await act(async () => {
      await user.keyboard('{Alt>}{4}{/Alt}');
    });
    expect(screen.getByPlaceholderText('見出し語を入力')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成' })).toBeInTheDocument();
    // モデル選択の存在
    expect(screen.getByLabelText('モデル')).toBeInTheDocument();
  });
});
