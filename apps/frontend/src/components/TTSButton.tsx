import { type CSSProperties, useMemo, useState } from 'react';
import { useSettings } from '../SettingsContext';

type Props = {
  text: string;
  className?: string;
  voice?: string;
  style?: CSSProperties;
};

export function TTSButton({ text, className, voice = 'alloy', style }: Props) {
  const [loading, setLoading] = useState(false);
  let contextApiBase: string | undefined;
  let contextPlaybackRate = 1;
  try {
    const { settings } = useSettings();
    contextApiBase = settings.apiBase;
    if (typeof settings.ttsPlaybackRate === 'number' && Number.isFinite(settings.ttsPlaybackRate)) {
      contextPlaybackRate = Math.min(2, Math.max(0.5, settings.ttsPlaybackRate));
    }
  } catch (err) {
    contextApiBase = undefined;
  }
  const endpoint = useMemo(() => {
    const base = contextApiBase || '/api';
    const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
    return `${normalized}/tts`;
  }, [contextApiBase]);

  const speak = async () => {
    if (loading) return;
    const trimmed = text?.trim();
    if (!trimmed) return;
    if (typeof window === 'undefined' || typeof Audio === 'undefined') {
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed, voice }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      // UIで指定された再生速度をAudioインスタンスに反映させ、速度設定の即時性を担保する。
      audio.playbackRate = contextPlaybackRate;
      audio.onended = () => {
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
      };
      await audio.play();
    } catch (err) {
      console.error('[TTS] failed to fetch audio', err);
      if (typeof window !== 'undefined' && typeof window.alert === 'function') {
        window.alert('音声の取得に失敗しました');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={speak}
      disabled={loading || !text?.trim()}
      className={className}
      data-testid="speak-btn"
      style={style}
    >
      {loading ? '読み上げ中…' : '音声'}
    </button>
  );
}
