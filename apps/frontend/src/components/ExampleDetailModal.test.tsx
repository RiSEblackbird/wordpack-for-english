import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ExampleDetailModal, type ExampleItemData } from './ExampleDetailModal';
import { SettingsProvider } from '../SettingsContext';
import type { ReactNode } from 'react';

vi.mock('../SettingsContext', () => {
  const settings = {
    apiBase: '/api',
    pronunciationEnabled: true,
    regenerateScope: 'all',
    autoAdvanceAfterGrade: false,
    requestTimeoutMs: 60000,
    model: 'gpt-5-mini',
    temperature: 0.6,
    reasoningEffort: 'minimal' as const,
    textVerbosity: 'medium' as const,
    theme: 'dark' as const,
  };
  return {
    useSettings: () => ({ settings, setSettings: () => {} }),
    SettingsProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  };
});

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
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={item} />
      </SettingsProvider>
    );

    const ttsButtons = screen.getAllByRole('button', { name: '音声' });
    expect(ttsButtons).toHaveLength(2);
    expect(screen.getByText(item.en)).toBeInTheDocument();
    expect(screen.getByText(item.ja)).toBeInTheDocument();
  });

  it('shows study progress buttons with counts', () => {
    const enriched: ExampleItemData = { ...item, checked_only_count: 2, learned_count: 1 };
    render(
      <SettingsProvider>
        <ExampleDetailModal isOpen onClose={() => {}} item={enriched} />
      </SettingsProvider>
    );

    expect(screen.getByRole('button', { name: '確認した (2)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '学習した (1)' })).toBeInTheDocument();
  });
});
