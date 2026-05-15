import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { ShelvesPage } from './index';

describe('ShelvesPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows dictionary shelves and lets the user add a local shelf draft', async () => {
    render(<ShelvesPage />);

    expect(screen.getByRole('heading', { name: 'Shelves' })).toBeInTheDocument();
    expect(screen.getByText('LLMまわり')).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.type(screen.getByLabelText('棚名'), '気になる語');
      await user.type(screen.getByLabelText('棚の説明'), 'curious / crisp');
      await user.click(screen.getByRole('button', { name: '追加' }));
    });

    expect(screen.getByText('気になる語')).toBeInTheDocument();
    expect(screen.getByText('curious / crisp')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('wp.localShelves.v1') || '[]')).toEqual([
      {
        name: '気になる語',
        description: 'curious / crisp',
        count: 0,
        color: 'sky',
      },
    ]);
  });
});
