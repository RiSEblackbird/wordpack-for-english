import React from 'react';

interface HeaderProps {
  fixedSafeAreaClass: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  sidebarToggleRef: React.RefObject<HTMLButtonElement>;
}

const HamburgerIcon: React.FC = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <line x1="4" y1="6" x2="20" y2="6" />
    <line x1="4" y1="12" x2="20" y2="12" />
    <line x1="4" y1="18" x2="20" y2="18" />
  </svg>
);

export const Header: React.FC<HeaderProps> = ({
  fixedSafeAreaClass,
  isSidebarOpen,
  onToggleSidebar,
  sidebarToggleRef,
}) => (
  <header>
    <div className="header-bar">
      <button
        ref={sidebarToggleRef}
        type="button"
        className={`hamburger-button hamburger-toggle${fixedSafeAreaClass}`}
        aria-label={isSidebarOpen ? 'メニューを閉じる' : 'メニューを開く'}
        aria-expanded={isSidebarOpen ? 'true' : 'false'}
        aria-controls="app-sidebar"
        onClick={onToggleSidebar}
      >
        <HamburgerIcon />
      </button>
    </div>
  </header>
);
