import React, { useEffect, useId, useRef, useState } from 'react';

const TOOLTIP_DELAY_MS = 300;
const TOOLTIP_TEXT = 'ゲストモードではAI機能は使用できません';
const DISABLEABLE_TAGS = new Set(['button', 'input', 'select', 'textarea', 'option']);

interface GuestLockProps {
  isGuest: boolean;
  children: React.ReactElement;
}

const supportsNativeDisabled = (child: React.ReactElement): boolean =>
  typeof child.type === 'string' && DISABLEABLE_TAGS.has(child.type);

/**
 * ゲストモード時の操作制限を共通化し、
 * 遅延ツールチップで「なぜ押せないか」を明示する。
 */
export const GuestLock: React.FC<GuestLockProps> = ({ isGuest, children }) => {
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const timerRef = useRef<number | null>(null);
  const tooltipId = useId();

  const clearTimer = () => {
    if (timerRef.current === null) return;
    window.clearTimeout(timerRef.current);
    timerRef.current = null;
  };

  useEffect(() => () => clearTimer(), []);

  const handleMouseEnter = () => {
    if (!isGuest) return;
    clearTimer();
    // ホバー直後に出すとストレスになるため、300ms 遅延で表示する。
    timerRef.current = window.setTimeout(() => {
      setTooltipVisible(true);
    }, TOOLTIP_DELAY_MS);
  };

  const handleMouseLeave = () => {
    if (!isGuest) return;
    clearTimer();
    setTooltipVisible(false);
  };

  const disableable = supportsNativeDisabled(children);
  const mergedDisabled = Boolean(children.props.disabled) || isGuest;
  const mergedAriaDisabled = isGuest ? true : children.props['aria-disabled'];
  const describedBy = [
    children.props['aria-describedby'],
    isGuest && tooltipVisible ? tooltipId : null,
  ]
    .filter(Boolean)
    .join(' ') || undefined;

  const lockedChild = React.cloneElement(children, {
    ...(disableable ? { disabled: mergedDisabled } : null),
    ...(mergedAriaDisabled ? { 'aria-disabled': mergedAriaDisabled } : null),
    ...(describedBy ? { 'aria-describedby': describedBy } : null),
    ...(isGuest && !disableable ? { tabIndex: -1 } : null),
  });

  return (
    <span
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {lockedChild}
      {isGuest && tooltipVisible ? (
        <span
          id={tooltipId}
          role="tooltip"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#212121',
            color: '#fff',
            padding: '4px 8px',
            borderRadius: 4,
            fontSize: 12,
            whiteSpace: 'nowrap',
            zIndex: 1000,
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.3)',
          }}
        >
          {TOOLTIP_TEXT}
        </span>
      ) : null}
    </span>
  );
};

export const guestLockMessage = TOOLTIP_TEXT;
