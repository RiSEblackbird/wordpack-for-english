import React, { useId } from 'react';
import { GuestLock } from './GuestLock';

interface GuestPublicToggleProps {
  isGuest: boolean;
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
  description: string;
  tooltip: string;
  disabledReason?: string | null;
  compact?: boolean;
}

/**
 * ゲスト公開トグルを共通化し、説明文とツールチップを統一する。
 * なぜ: 「公開範囲の意図」と「誤操作を避ける理由」を同じ文言で伝え、UIの表現ぶれを防ぐため。
 */
export const GuestPublicToggle: React.FC<GuestPublicToggleProps> = ({
  isGuest,
  checked,
  disabled = false,
  onChange,
  description,
  tooltip,
  disabledReason,
  compact = false,
}) => {
  const inputId = useId();
  const helperId = `${inputId}-desc`;

  const toggleInput = (
    <input
      id={inputId}
      type="checkbox"
      checked={checked}
      onChange={(event) => onChange(event.target.checked)}
      disabled={disabled}
      aria-describedby={helperId}
      title={tooltip}
      style={{ width: compact ? 14 : 16, height: compact ? 14 : 16 }}
    />
  );

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: compact ? '0.2rem' : '0.35rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <label htmlFor={inputId} style={{ fontSize: compact ? '0.7em' : '0.85em', fontWeight: 600 }}>
          ゲスト公開
        </label>
        <GuestLock isGuest={isGuest}>
          {toggleInput}
        </GuestLock>
        <span
          style={{ fontSize: compact ? '0.65em' : '0.75em', color: 'var(--color-subtle)' }}
          title={tooltip}
          aria-label="ゲスト公開の説明"
        >
          ℹ
        </span>
      </div>
      <div
        id={helperId}
        style={{
          fontSize: compact ? '0.65em' : '0.78em',
          color: 'var(--color-subtle)',
          lineHeight: 1.4,
        }}
      >
        {description}
        {disabledReason ? <span style={{ display: 'block', marginTop: '0.15rem' }}>{disabledReason}</span> : null}
      </div>
    </div>
  );
};
