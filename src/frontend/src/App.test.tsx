import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import '@testing-library/jest-dom';

describe('App navigation', () => {
  it('renders card panel by default and navigates with keyboard', async () => {
    render(<App />);

    const cardBtn = screen.getByRole('button', { name: 'カードを取得' });
    expect(cardBtn).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{2}{/Alt}');
    expect(screen.getByPlaceholderText('英文を入力してください')).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{3}{/Alt}');
    expect(screen.getByPlaceholderText('段落を入力してください')).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{4}{/Alt}');
    expect(screen.getByLabelText('API ベースURL')).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{1}{/Alt}');
    await userEvent.keyboard('/');
    const cardPanel = document.getElementById('card-panel')!;
    expect(cardPanel).toHaveFocus();
  });
});
