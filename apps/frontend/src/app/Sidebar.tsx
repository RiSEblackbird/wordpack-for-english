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

const BrandMark: React.FC = () => (
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
    <path d="M14 2 25 14 14 26 3 14 14 2Z" fill="#2f73ff" />
    <path d="M14 2v24M3 14h22" stroke="#93c5fd" strokeWidth="2" strokeLinecap="round" />
    <path d="m8.8 8.8 10.4 10.4M19.2 8.8 8.8 19.2" stroke="#0b1220" strokeOpacity=".42" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
);

const NavIcon: React.FC<{ item: NavigationItem['key'] }> = ({ item }) => {
  switch (item) {
    case 'lexicon':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 5.8c0-.9.7-1.6 1.6-1.6h4.3c1.1 0 2.1.5 2.8 1.3.7-.8 1.7-1.3 2.8-1.3h4.3c.9 0 1.6.7 1.6 1.6v13.4c0 .6-.6 1-1.1.8l-4.5-1.8c-.9-.4-2-.2-2.8.4l-.3.2-.3-.2c-.8-.6-1.9-.8-2.8-.4L6.1 20c-.5.2-1.1-.2-1.1-.8V5.8Z" />
        </svg>
      );
    case 'reader':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 4h9.5L19 7.5V20H6V4Zm8.7 1.7V8h2.6M8.5 11h8M8.5 14h8M8.5 17h5" />
        </svg>
      );
    case 'examples':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 5h14v3H5V5Zm0 5.5h14v3H5v-3ZM5 16h14v3H5v-3Z" />
        </svg>
      );
    case 'explore':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm3.4 4.6-1.7 5.1-5.1 1.7 1.7-5.1 5.1-1.7Z" />
        </svg>
      );
    case 'shelves':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 4h3.5v16H6V4Zm5.2 0H15v16h-3.8V4Zm5.5.6 3.2 14.8-2.8.6-3.2-14.8 2.8-.6Z" />
        </svg>
      );
    case 'quiz':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 4.5h12A1.5 1.5 0 0 1 19.5 6v12A1.5 1.5 0 0 1 18 19.5H6A1.5 1.5 0 0 1 4.5 18V6A1.5 1.5 0 0 1 6 4.5Zm3 4h6M9 12h6M9 15.5h3" />
        </svg>
      );
    case 'settings':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 8.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6Zm8 3.8-2.1-.7a6.7 6.7 0 0 0-.6-1.5l1-2-2.1-2.1-2 1a6.7 6.7 0 0 0-1.5-.6L12 4H9l-.7 2.1c-.5.1-1 .3-1.5.6l-2-1-2.1 2.1 1 2c-.3.5-.5 1-.6 1.5L1 12v3l2.1.7c.1.5.3 1 .6 1.5l-1 2 2.1 2.1 2-1c.5.3 1 .5 1.5.6L9 23h3l.7-2.1c.5-.1 1-.3 1.5-.6l2 1 2.1-2.1-1-2c.3-.5.5-1 .6-1.5L20 15v-3Z" />
        </svg>
      );
    default:
      return null;
  }
};

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
          <BrandMark />
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
              <span className="sidebar-nav-icon"><NavIcon item={item.key} /></span>
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
        <div className="sidebar-user-card" aria-label={isGuest ? 'ゲストユーザー' : 'ログインユーザー'}>
          <span className="sidebar-user-avatar" aria-hidden="true">U</span>
          <span>
            <strong>User</strong>
            <small>{isGuest ? 'ゲスト' : 'ログイン中'}</small>
          </span>
        </div>
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
