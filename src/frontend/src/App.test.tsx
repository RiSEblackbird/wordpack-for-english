import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import '@testing-library/jest-dom';

describe('App navigation', () => {
  it('renders card panel by default and navigates with keyboard', async () => {
    render(<App />);

    const cardBtn = screen.getByRole('button', { name: 'カードを取得' });
    expect(cardBtn).toBeInTheDocument();

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
    expect(screen.getByPlaceholderText('見出し語を入力')).toBeInTheDocument();

    await act(async () => {
      await user.keyboard('{Alt>}{6}{/Alt}');
    });
    expect(screen.getByLabelText('発音を有効化')).toBeInTheDocument();

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
  });
});
