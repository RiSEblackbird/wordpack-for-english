import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
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
});


