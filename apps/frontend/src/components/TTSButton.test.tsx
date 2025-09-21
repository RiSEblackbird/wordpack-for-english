import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { TTSButton } from './TTSButton';

describe('TTSButton', () => {
  const originalFetch = global.fetch;
  const originalAudio = (global as any).Audio;
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  const originalAlert = window.alert;

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
    if (originalAudio) {
      (global as any).Audio = originalAudio;
    } else {
      delete (global as any).Audio;
    }
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    window.alert = originalAlert;
  });

  it('fetches audio and plays it', async () => {
    const playMock = vi.fn().mockResolvedValue(undefined);
    const audioInstances: Array<{ onended: (() => void) | null }> = [];
    const audioCtor = vi.fn().mockImplementation(() => {
      const instance = {
        play: playMock,
        onended: null as (() => void) | null,
        onerror: null as (() => void) | null,
      };
      audioInstances.push(instance);
      return instance;
    });
    (global as any).Audio = audioCtor;
    URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    URL.revokeObjectURL = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(new Response('audio-data', { status: 200 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    render(<TTSButton text="Hello" />);
    const user = userEvent.setup();
    const button = screen.getByRole('button', { name: '音声読み上げ' });
    await user.click(button);

    expect(fetchMock).toHaveBeenCalledWith('/api/tts', expect.objectContaining({ method: 'POST' }));
    await waitFor(() => expect(playMock).toHaveBeenCalled());
    expect(URL.createObjectURL).toHaveBeenCalled();
    audioInstances[0].onended?.();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('alerts when fetch fails', async () => {
    (global as any).Audio = vi.fn().mockImplementation(() => ({ play: vi.fn().mockResolvedValue(undefined), onended: null, onerror: null }));
    URL.createObjectURL = vi.fn().mockReturnValue('blob:mock');
    URL.revokeObjectURL = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(new Response('error', { status: 500 }));
    global.fetch = fetchMock as unknown as typeof fetch;
    const alertMock = vi.fn();
    window.alert = alertMock;
    const consoleMock = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<TTSButton text="Hello" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '音声読み上げ' }));

    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('音声の取得に失敗しました'));
    expect(consoleMock).toHaveBeenCalled();
  });
});
