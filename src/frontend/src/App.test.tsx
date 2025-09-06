import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import '@testing-library/jest-dom';

describe('App navigation', () => {
  it('renders card panel by default and navigates with keyboard', async () => {
    render(<App />);

    const cardBtn = screen.getByRole('button', { name: /get card/i });
    expect(cardBtn).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{2}{/Alt}');
    expect(screen.getByPlaceholderText('Enter a sentence')).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{3}{/Alt}');
    expect(screen.getByPlaceholderText('Enter a paragraph')).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{4}{/Alt}');
    expect(screen.getByLabelText('API Base')).toBeInTheDocument();

    await userEvent.keyboard('{Alt>}{1}{/Alt}');
    await userEvent.keyboard('/');
    expect(cardBtn).toHaveFocus();
  });
});
