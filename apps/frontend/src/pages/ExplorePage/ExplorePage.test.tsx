import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, expect, it } from 'vitest';
import { ExplorePage } from './index';

describe('ExplorePage', () => {
  it('lets the user switch relation mode and selected lemma', async () => {
    render(<ExplorePage />);

    expect(screen.getByRole('heading', { name: 'Explore' })).toBeInTheDocument();
    expect(screen.getByLabelText('探索する lemma を検索')).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'contrast' }));
      await user.click(screen.getByRole('button', { name: /brittle/ }));
    });

    expect(screen.getByRole('button', { name: 'contrast' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('heading', { name: 'brittle' })).toBeInTheDocument();
  });
});
