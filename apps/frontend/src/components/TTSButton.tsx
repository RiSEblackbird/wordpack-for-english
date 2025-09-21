import { type CSSProperties, useState } from 'react';

type Props = {
  text: string;
  className?: string;
  voice?: string;
  style?: CSSProperties;
};

export function TTSButton({ text, className, voice = 'alloy', style }: Props) {
  const [loading, setLoading] = useState(false);

  const speak = async () => {
    if (loading) return;
    const trimmed = text?.trim();
    if (!trimmed) return;
    if (typeof window === 'undefined' || typeof Audio === 'undefined') {
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/tts', {
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
      {loading ? '読み上げ中…' : '音声読み上げ'}
    </button>
  );
}
