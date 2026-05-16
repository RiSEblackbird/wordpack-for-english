import type React from 'react';
import type { AppRouteState } from './routes';

interface KeyboardShortcutOptions {
  closeSidebar: () => void;
  focusRef: React.RefObject<HTMLElement>;
  isSidebarOpen: boolean;
  navigate: (next: AppRouteState) => void;
}

export const bindAppKeyboardShortcuts = ({
  closeSidebar,
  focusRef,
  isSidebarOpen,
  navigate,
}: KeyboardShortcutOptions): (() => void) => {
  const handler = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && isSidebarOpen) {
      event.preventDefault();
      closeSidebar();
      return;
    }
    if (event.altKey) {
      if (event.key === '1') navigate({ key: 'lexicon' });
      if (event.key === '2') navigate({ key: 'settings' });
      if (event.key === '3') navigate({ key: 'reader' });
      if (event.key === '4') navigate({ key: 'lexicon' });
      if (event.key === '5') navigate({ key: 'examples' });
      if (event.key === '6') navigate({ key: 'explore' });
      if (event.key === '7') navigate({ key: 'shelves' });
    } else if (event.key === '/') {
      event.preventDefault();
      focusRef.current?.focus();
    }
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
};
