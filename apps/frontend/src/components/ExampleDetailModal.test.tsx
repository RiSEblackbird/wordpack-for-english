import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ExampleDetailModal, type ExampleItemData } from './ExampleDetailModal';

describe('ExampleDetailModal', () => {
  const item: ExampleItemData = {
    id: 101,
    word_pack_id: 'wp:test',
    lemma: 'alpha',
    category: 'Dev',
    en: 'Test sentence in English.',
    ja: '英語の例文です。',
    created_at: '2024-05-01T09:00:00+09:00',
  };

  it('renders TTS buttons for original and translated texts', () => {
    render(<ExampleDetailModal isOpen onClose={() => {}} item={item} />);

    const ttsButtons = screen.getAllByRole('button', { name: '音声' });
    expect(ttsButtons).toHaveLength(2);
    expect(screen.getByText(item.en)).toBeInTheDocument();
    expect(screen.getByText(item.ja)).toBeInTheDocument();
  });
});
