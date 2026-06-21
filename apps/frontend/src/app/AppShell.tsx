import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { useAuth } from '../AuthContext';
import { LexiconPage } from '../pages/LexiconPage';
import { WordPackDetailPage } from '../pages/WordPackDetailPage';
import { ReaderPage } from '../pages/ReaderPage';
import { ExamplesPage } from '../pages/ExamplesPage';
import { ExplorePage } from '../pages/ExplorePage';
import { QuizPage } from '../pages/QuizPage';
import { ShelvesPage } from '../pages/ShelvesPage';
import { SettingsPage } from '../pages/SettingsPage';
import { BottomNav } from './BottomNav';
import { Header } from './Header';
import { bindAppKeyboardShortcuts } from './keyboardShortcuts';
import { MAIN_HEADING_TEXT, MAIN_MAX_WIDTH, type NavigationItem } from './navigation';
import { parseAppRoute, routeToPath, type AppRouteState } from './routes';
import { Sidebar } from './Sidebar';
import './styles/app-shell.css';

type ShellStyle = React.CSSProperties & { '--main-max-width': string };

export const AppShell: React.FC = () => {
  const [route, setRoute] = useState<AppRouteState>(() => {
    if (typeof window === 'undefined') {
      return { key: 'lexicon' };
    }
    return parseAppRoute(window.location.pathname);
  });
  const [selectedWordPackId, setSelectedWordPackId] = useState<string | null>(null);
  const focusRef = useRef<HTMLElement>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isOverlaySidebar, setIsOverlaySidebar] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const sidebarToggleRef = useRef<HTMLButtonElement>(null);
  const firstSidebarItemRef = useRef<HTMLButtonElement>(null);
  const hasSidebarOpened = useRef(false);
  const { signOut, isAuthenticating, isGuest } = useAuth();

  const closeSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const navigate = useCallback((next: AppRouteState, options?: { replace?: boolean }) => {
    setRoute(next);
    if (typeof window === 'undefined') {
      return;
    }
    const nextPath = routeToPath(next);
    if (window.location.pathname === nextPath) {
      return;
    }
    const historyAction = options?.replace ? 'replaceState' : 'pushState';
    window.history[historyAction](null, '', nextPath);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const initialRoute = parseAppRoute(window.location.pathname);
    if (window.location.pathname === '/') {
      navigate(initialRoute, { replace: true });
    }
    const handlePopState = () => {
      setRoute(parseAppRoute(window.location.pathname));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [navigate]);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && import.meta.env.MODE === 'test') {
        window.history.replaceState(null, '', '/');
      }
    };
  }, []);

  useEffect(
    () => bindAppKeyboardShortcuts({ closeSidebar, focusRef, isSidebarOpen, navigate }),
    [closeSidebar, isSidebarOpen, navigate],
  );

  const isSidebarVisible = isOverlaySidebar ? isSidebarOpen : true;

  useEffect(() => {
    if (!isOverlaySidebar) {
      return;
    }
    if (isSidebarOpen) {
      hasSidebarOpened.current = true;
      firstSidebarItemRef.current?.focus();
    } else if (hasSidebarOpened.current) {
      sidebarToggleRef.current?.focus();
    }
  }, [isOverlaySidebar, isSidebarOpen]);

  useLayoutEffect(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar) {
      return;
    }
    if (isSidebarVisible) {
      sidebar.removeAttribute('inert');
      return;
    }
    sidebar.setAttribute('inert', '');
  }, [isSidebarVisible]);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return undefined;
    }
    const mediaQuery = window.matchMedia('(max-width: 900px)');
    const updateOverlayState = () => {
      setIsOverlaySidebar(mediaQuery.matches);
    };
    updateOverlayState();
    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', updateOverlayState);
      return () => mediaQuery.removeEventListener('change', updateOverlayState);
    }
    mediaQuery.addListener(updateOverlayState);
    return () => mediaQuery.removeListener(updateOverlayState);
  }, []);

  const toggleSidebar = () =>
    flushSync(() => {
      setIsSidebarOpen((prev) => !prev);
    });

  const handleSelectRoute = (next: NavigationItem['key']) => {
    navigate({ key: next });
    if (isOverlaySidebar) {
      closeSidebar();
    }
  };

  const handleHeaderSignOut = useCallback(async () => {
    try {
      await signOut();
    } catch (error) {
      console.warn('[Header] signOut failed', error);
    }
  }, [signOut]);

  const activeNavKey: NavigationItem['key'] = route.key === 'wordpackDetail' ? 'lexicon' : route.key;
  const fixedSafeAreaClass = ' safe-area-adjusted';
  const shellStyle: ShellStyle = { '--main-max-width': `${MAIN_MAX_WIDTH}px` };

  return (
    <main
      className={`app-shell dictionary-shell${isSidebarVisible ? ' sidebar-open' : ''}`}
      style={shellStyle}
    >
      <h1 className="visually-hidden">{MAIN_HEADING_TEXT}</h1>
      {isSidebarOpen && isOverlaySidebar ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-hidden="true"
          tabIndex={-1}
          onClick={closeSidebar}
        />
      ) : null}
      <div className="app-layout">
        <Sidebar
          activeNavKey={activeNavKey}
          firstSidebarItemRef={firstSidebarItemRef}
          isAuthenticating={isAuthenticating}
          isGuest={isGuest}
          isSidebarOpen={isSidebarVisible}
          onSelectRoute={handleSelectRoute}
          onSignOut={handleHeaderSignOut}
          sidebarRef={sidebarRef}
        />
        <div className="main-column">
          <div className="main-inner">
            <Header
              fixedSafeAreaClass={fixedSafeAreaClass}
              isSidebarOpen={isSidebarVisible}
              isSidebarToggleVisible={isOverlaySidebar}
              onToggleSidebar={toggleSidebar}
              sidebarToggleRef={sidebarToggleRef}
            />
            <section aria-label="アプリのメインコンテンツ" className="dictionary-content">
              {route.key === 'lexicon' && (
                <LexiconPage
                  focusRef={focusRef}
                  selectedWordPackId={selectedWordPackId}
                  onWordPackGenerated={(wordPackId) => setSelectedWordPackId(wordPackId)}
                />
              )}
              {route.key === 'wordpackDetail' && route.wordPackId ? (
                <WordPackDetailPage
                  focusRef={focusRef}
                  wordPackId={route.wordPackId}
                  onBackToLexicon={() => navigate({ key: 'lexicon' })}
                />
              ) : null}
              {route.key === 'reader' && <ReaderPage />}
              {route.key === 'examples' && <ExamplesPage />}
              {route.key === 'explore' && <ExplorePage />}
              {route.key === 'shelves' && <ShelvesPage />}
              {route.key === 'quiz' && <QuizPage />}
              {route.key === 'settings' && <SettingsPage focusRef={focusRef} />}
            </section>
            <footer className="app-footer">
              <small>WordPack personal lexicon</small>
            </footer>
          </div>
        </div>
      </div>
      <BottomNav
        activeNavKey={activeNavKey}
        isOverlaySidebar={isOverlaySidebar}
        onSelectRoute={handleSelectRoute}
      />
    </main>
  );
};
