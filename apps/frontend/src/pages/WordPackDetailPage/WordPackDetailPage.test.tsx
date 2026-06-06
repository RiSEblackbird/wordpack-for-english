import { createRef } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';
import { NotificationsProvider } from '../../NotificationsContext';
import { WordPackDetailPage } from './index';

vi.mock('../../components/WordPackPanel', () => ({
  WordPackPanel: ({ selectedWordPackId }: { selectedWordPackId: string }) => (
    <div data-testid="wordpack-panel">{selectedWordPackId}</div>
  ),
}));

describe('WordPackDetailPage', () => {
  it('renders dictionary article chrome and delegates the selected WordPack id', async () => {
    const onBackToLexicon = vi.fn();

    render(
      <NotificationsProvider persist={false}>
        <WordPackDetailPage
          focusRef={createRef<HTMLElement>()}
          wordPackId="wp:test:alpha"
          onBackToLexicon={onBackToLexicon}
        />
      </NotificationsProvider>,
    );

    expect(screen.getByRole('heading', { name: 'WordPack' })).toBeInTheDocument();
    expect(screen.getByText('dictionary article')).toBeInTheDocument();
    expect(screen.getByTestId('wordpack-panel')).toHaveTextContent('wp:test:alpha');

    await userEvent.click(screen.getByRole('button', { name: 'Lexiconへ戻る' }));

    expect(onBackToLexicon).toHaveBeenCalledTimes(1);
  });
});
