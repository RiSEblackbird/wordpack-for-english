import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { SettingsPanel } from './SettingsPanel';
import type { Settings } from '../SettingsContext';
import type { RefObject } from 'react';

const setSettingsMock = vi.fn();
let currentSettings: Settings;

vi.mock('../SettingsContext', () => ({
  useSettings: () => ({ settings: currentSettings, setSettings: setSettingsMock }),
}));

describe('SettingsPanel', () => {
  beforeEach(() => {
    currentSettings = {
      apiBase: '/api',
      pronunciationEnabled: true,
      regenerateScope: 'all',
      autoAdvanceAfterGrade: false,
      requestTimeoutMs: 360000,
      model: 'gpt-5-mini',
      temperature: 0.6,
      reasoningEffort: 'minimal',
      textVerbosity: 'medium',
      theme: 'dark',
      ttsPlaybackRate: 1,
    };
    setSettingsMock.mockReset();
  });

  it('toggle pronunciation setting from checkbox', async () => {
    const focusRef = { current: null } as RefObject<HTMLElement>;
    render(<SettingsPanel focusRef={focusRef} />);

    const user = userEvent.setup();
    const checkbox = screen.getByLabelText('発音を有効化');
    await user.click(checkbox);

    expect(setSettingsMock).toHaveBeenCalledWith({ ...currentSettings, pronunciationEnabled: false });
  });
});
