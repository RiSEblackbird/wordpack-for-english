import React from 'react';
import { SIDEBAR_PORTAL_CONTAINER_ID } from '../components/SidebarPortal';
import { SidebarPlaybackRateControl } from '../components/SidebarPlaybackRateControl';
import { NAV_ITEMS, SIDEBAR_ID, type NavigationItem } from './navigation';

interface SidebarProps {
  activeNavKey: NavigationItem['key'];
  firstSidebarItemRef: React.RefObject<HTMLButtonElement>;
  isAuthenticating: boolean;
  isGuest: boolean;
  isSidebarOpen: boolean;
  onSelectRoute: (next: NavigationItem['key']) => void;
  onSignOut: () => void;
  sidebarRef: React.RefObject<HTMLElement>;
}

const GithubIcon: React.FC = () => (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
  </svg>
);

export const Sidebar: React.FC<SidebarProps> = ({
  activeNavKey,
  firstSidebarItemRef,
  isAuthenticating,
  isGuest,
  isSidebarOpen,
  onSelectRoute,
  onSignOut,
  sidebarRef,
}) => (
  <aside
    id={SIDEBAR_ID}
    className="sidebar"
    aria-label="アプリ内共通メニュー"
    aria-hidden={isSidebarOpen ? 'false' : 'true'}
    ref={sidebarRef}
    style={isSidebarOpen ? { transform: 'translateX(0)' } : undefined}
  >
    <div className="sidebar-content" style={{ width: '100%', boxSizing: 'border-box' }}>
      <div className="sidebar-main">
        <div className="sidebar-brand" aria-label="アプリタイトル">
          <span className="sidebar-title">WordPack</span>
        </div>
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
      <div className="sidebar-footer" aria-label="アカウントと外部リンク">
        <a
          href="https://github.com/RiSEblackbird/wordpack-for-english"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="GitHubリポジトリを開く"
          className="github-link sidebar-github-link"
          tabIndex={isSidebarOpen ? 0 : -1}
        >
          <GithubIcon />
          <span>GitHub</span>
        </a>
        <div className="sidebar-auth">
          {isGuest ? (
            <span className="guest-badge">ゲスト閲覧モード</span>
          ) : null}
          <button
            type="button"
            className="logout-button"
            onClick={onSignOut}
            disabled={isAuthenticating}
            tabIndex={isSidebarOpen ? 0 : -1}
          >
            ログアウト
          </button>
        </div>
      </div>
    </div>
  </aside>
);
