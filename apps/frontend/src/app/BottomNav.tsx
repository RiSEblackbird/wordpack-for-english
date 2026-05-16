import React from 'react';
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
}) => (
  <nav
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
