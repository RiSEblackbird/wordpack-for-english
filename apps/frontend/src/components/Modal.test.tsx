import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { Modal } from './Modal';

describe('Modal width constraint', () => {
  it('sets max width to 85% of main content width (with viewport cap)', () => {
    render(
      <Modal isOpen onClose={() => {}} title="Test">
        <div>content</div>
      </Modal>
    );

    const dialog = screen.getByRole('dialog');
    const container = dialog.querySelector('div > div') as HTMLDivElement | null;
    expect(container).not.toBeNull();
    // 期待値: min(96vw, calc(var(--main-max-width, 1000px) * 0.90))
    expect(container!.style.maxWidth).toBe('min(96vw, calc(var(--main-max-width, 1000px) * 0.90))');
    // 可読性のため、width は 100% であることも確認
    expect(container!.style.width).toBe('100%');
  });

  it('allows overriding max width when specified', () => {
    render(
      <Modal
        isOpen
        onClose={() => {}}
        title="Test"
        maxWidth="480px"
      >
        <div>content</div>
      </Modal>
    );

    const dialog = screen.getByRole('dialog');
    const container = dialog.querySelector('div > div') as HTMLDivElement | null;
    expect(container).not.toBeNull();
    expect(container!.style.maxWidth).toBe('480px');
  });
});

describe('Modal close interactions', () => {
  it('renders dialog with title', () => {
    render(
      <Modal isOpen onClose={() => {}} title="確認">
        <div>content</div>
      </Modal>
    );

    expect(screen.getByRole('dialog', { name: '確認' })).toBeInTheDocument();
  });

  it('calls onClose when pressing Escape', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <Modal isOpen onClose={onClose} title="確認">
        <div>content</div>
      </Modal>
    );

    await user.keyboard('{Escape}');

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when clicking the backdrop wrapper', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <Modal isOpen onClose={onClose} title="確認">
        <div>content</div>
      </Modal>
    );

    const dialog = screen.getByRole('dialog', { name: '確認' });
    // 背景クリック判定はラッパー自身へのクリックで行う。
    await user.click(dialog);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when clicking the close button', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <Modal isOpen onClose={onClose} title="確認">
        <div>content</div>
      </Modal>
    );

    // ユーザー操作として「閉じる」ボタンをクリックする。
    await user.click(screen.getByRole('button', { name: '閉じる' }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});


