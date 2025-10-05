import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { SidebarPlaybackRateControl } from './SidebarPlaybackRateControl';
import type { Settings } from '../SettingsContext';

const setSettingsMock = vi.fn();
let currentSettings: Settings;

vi.mock('../SettingsContext', () => ({
  useSettings: () => ({ settings: currentSettings, setSettings: setSettingsMock }),
}));

describe('SidebarPlaybackRateControl', () => {
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

  it('updates playback rate when sidebar is open', async () => {
    render(<SidebarPlaybackRateControl isSidebarOpen />);
    const select = screen.getByLabelText('音声再生スピード');
    const user = userEvent.setup();
    await user.selectOptions(select, '1.25');

    expect(setSettingsMock).toHaveBeenCalledTimes(1);
    const updater = setSettingsMock.mock.calls[0][0] as (prev: Settings) => Settings;
    const next = updater(currentSettings);
    expect(next.ttsPlaybackRate).toBe(1.25);
  });

  it('disables select when sidebar is closed', () => {
    render(<SidebarPlaybackRateControl isSidebarOpen={false} />);
    const select = screen.getByLabelText('音声再生スピード');
    expect(select).toBeDisabled();
  });
});
