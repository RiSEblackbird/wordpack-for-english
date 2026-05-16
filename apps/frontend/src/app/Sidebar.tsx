import React from 'react';
import { SIDEBAR_PORTAL_CONTAINER_ID } from '../components/SidebarPortal';
import { SidebarPlaybackRateControl } from '../components/SidebarPlaybackRateControl';
import { NAV_ITEMS, SIDEBAR_ID, type NavigationItem } from './navigation';

interface SidebarProps {
  activeNavKey: NavigationItem['key'];
  firstSidebarItemRef: React.RefObject<HTMLButtonElement>;
  isSidebarOpen: boolean;
  onSelectRoute: (next: NavigationItem['key']) => void;
  sidebarRef: React.RefObject<HTMLElement>;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeNavKey,
  firstSidebarItemRef,
  isSidebarOpen,
  onSelectRoute,
  sidebarRef,
}) => (
  <aside
    id={SIDEBAR_ID}
    className="sidebar"
    aria-label="アプリ内共通メニュー"
    aria-hidden={isSidebarOpen ? 'false' : 'true'}
    ref={sidebarRef}
  >
    <div className="sidebar-content" style={{ width: '100%', boxSizing: 'border-box' }}>
      <nav className="sidebar-nav" aria-label="主要メニュー">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            className="sidebar-nav-button"
            aria-label={item.legacyLabel}
            aria-pressed={activeNavKey === item.key}
            aria-current={activeNavKey === item.key ? 'page' : undefined}
            onClick={() => onSelectRoute(item.key)}
            tabIndex={isSidebarOpen ? 0 : -1}
            ref={item.key === NAV_ITEMS[0].key ? firstSidebarItemRef : undefined}
          >
            <span aria-hidden="true">◇</span>
            <span aria-hidden="true">{item.label}</span>
          </button>
        ))}
      </nav>
      <SidebarPlaybackRateControl isSidebarOpen={isSidebarOpen} />
      <div
        id={SIDEBAR_PORTAL_CONTAINER_ID}
        className="sidebar-controls"
        role="region"
        aria-label="ページ固有の操作"
      />
    </div>
  </aside>
);
