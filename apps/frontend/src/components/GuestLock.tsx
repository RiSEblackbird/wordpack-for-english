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

  // GuestLock は tooltip のために wrapper 要素を挟むが、
  // 子要素側の `margin-left:auto` などは「外側のflex」に効かず、wrapper 内の揃えになってしまう。
  // 右寄せ等のレイアウト意図を保つため、autoマージンは wrapper 側へ持ち上げる。
  const childStyle = (children.props.style ?? {}) as React.CSSProperties;
  const wrapperAutoMargins: Partial<React.CSSProperties> = {};
  const nextChildStyle: React.CSSProperties = { ...childStyle };
  const hoistAutoMargin = (key: keyof React.CSSProperties) => {
    if (childStyle?.[key] !== 'auto') return;
    (wrapperAutoMargins as any)[key] = 'auto';
    (nextChildStyle as any)[key] = undefined;
  };
  hoistAutoMargin('marginLeft');
  hoistAutoMargin('marginInlineStart');
  hoistAutoMargin('marginRight');
  hoistAutoMargin('marginInlineEnd');

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
    ...(Object.keys(wrapperAutoMargins).length > 0 ? { style: nextChildStyle } : null),
  });

  return (
    <span
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', ...wrapperAutoMargins }}
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
