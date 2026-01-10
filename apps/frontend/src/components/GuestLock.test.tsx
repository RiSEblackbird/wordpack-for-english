import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { GuestLock, guestLockMessage } from './GuestLock';

describe('GuestLock', () => {
  it('disables guest actions and keeps focus away', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(
      <div>
        <GuestLock isGuest>
          <button type="button" onClick={onClick}>
            AI操作
          </button>
        </GuestLock>
        <button type="button">次の操作</button>
      </div>
    );

    const guestButton = screen.getByRole('button', { name: 'AI操作' });
    const nextButton = screen.getByRole('button', { name: '次の操作' });

    expect(guestButton).toBeDisabled();
    expect(guestButton).toHaveAttribute('aria-disabled', 'true');

    await user.click(guestButton);
    expect(onClick).not.toHaveBeenCalled();

    await user.tab();
    expect(nextButton).toHaveFocus();
  });

  it('shows tooltip after 300ms hover and hides immediately on leave', async () => {
    vi.useFakeTimers();
    render(
      <GuestLock isGuest>
        <button type="button">AI操作</button>
      </GuestLock>
    );

    const guestButton = screen.getByRole('button', { name: 'AI操作' });
    const wrapper = guestButton.parentElement as HTMLElement;

    act(() => {
      fireEvent.mouseEnter(wrapper);
    });
    expect(screen.queryByText(guestLockMessage)).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(screen.getByText(guestLockMessage)).toBeInTheDocument();

    act(() => {
      fireEvent.mouseLeave(wrapper);
    });
    expect(screen.queryByText(guestLockMessage)).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
