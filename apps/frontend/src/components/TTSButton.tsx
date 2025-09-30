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
  let contextUserRole: 'admin' | 'viewer' = 'admin';
  try {
    const { settings } = useSettings();
    contextApiBase = settings.apiBase;
    contextUserRole = settings.userRole;
  } catch (err) {
    contextApiBase = undefined;
  }
  const endpoint = useMemo(() => {
    const base = contextApiBase || '/api';
    const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
    return `${normalized}/tts`;
  }, [contextApiBase]);

  const aiDisabled = contextUserRole === 'viewer';
  const buttonDisabled = aiDisabled || loading || !text?.trim();
  const combinedStyle = {
    ...style,
    ...(aiDisabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}),
  } satisfies CSSProperties;

  const speak = async () => {
    if (aiDisabled || loading) return;
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
      disabled={buttonDisabled}
      className={className}
      data-testid="speak-btn"
      style={combinedStyle}
      title={aiDisabled ? '閲覧ユーザーは音声機能を利用できません' : undefined}
    >
      {loading ? '読み上げ中…' : '音声'}
    </button>
  );
}
