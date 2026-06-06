import React, { useEffect, useRef } from 'react';
import { NAV_ITEMS, type NavigationItem } from './navigation';

interface BottomNavProps {
  activeNavKey: NavigationItem['key'];
  isOverlaySidebar: boolean;
  onSelectRoute: (next: NavigationItem['key']) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  activeNavKey,
  isOverlaySidebar,
  onSelectRoute,
}) => {
  const navRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const nav = navRef.current;
    const shell = nav?.closest<HTMLElement>('.dictionary-shell');
    if (!nav || !shell || typeof window === 'undefined') return;

    const updateReservedHeight = () => {
      const isRendered = window.getComputedStyle(nav).display !== 'none';
      const height = isRendered ? Math.ceil(nav.getBoundingClientRect().height) : 0;
      shell.style.setProperty('--bottom-nav-height', `${height}px`);
    };

    updateReservedHeight();
    let resizeObserver: ResizeObserver | null = null;
    if ('ResizeObserver' in window) {
      resizeObserver = new ResizeObserver(updateReservedHeight);
      resizeObserver.observe(nav);
    }
    window.addEventListener('resize', updateReservedHeight);
    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener('resize', updateReservedHeight);
      shell.style.removeProperty('--bottom-nav-height');
    };
  }, []);

  return (
    <nav
      ref={navRef}
      className="dictionary-bottom-nav"
      aria-label="モバイル主要メニュー"
      aria-hidden={isOverlaySidebar ? 'false' : 'true'}
    >
      {NAV_ITEMS.filter((item) => item.key !== 'settings').map((item) => (
        <button
          key={item.key}
          type="button"
          aria-label={item.legacyLabel}
          aria-current={activeNavKey === item.key ? 'page' : undefined}
          tabIndex={isOverlaySidebar ? 0 : -1}
          onClick={() => onSelectRoute(item.key)}
        >
          {item.shortLabel}
        </button>
      ))}
    </nav>
  );
};
