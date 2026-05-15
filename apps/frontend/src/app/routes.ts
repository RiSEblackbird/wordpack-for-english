export type AppRouteKey =
  | 'lexicon'
  | 'wordpackDetail'
  | 'reader'
  | 'examples'
  | 'explore'
  | 'shelves'
  | 'settings';

export interface AppRouteState {
  key: AppRouteKey;
  wordPackId?: string;
}

export const routeToPath = (route: AppRouteState): string => {
  if (route.key === 'wordpackDetail' && route.wordPackId) {
    return `/wordpacks/${encodeURIComponent(route.wordPackId)}`;
  }
  if (route.key === 'lexicon') return '/lexicon';
  return `/${route.key}`;
};

export const parseAppRoute = (pathname: string): AppRouteState => {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  if (normalized === '/' || normalized === '/lexicon') {
    return { key: 'lexicon' };
  }
  if (normalized.startsWith('/wordpacks/')) {
    const id = decodeURIComponent(normalized.slice('/wordpacks/'.length));
    return id ? { key: 'wordpackDetail', wordPackId: id } : { key: 'lexicon' };
  }
  if (normalized === '/reader' || normalized === '/articles') return { key: 'reader' };
  if (normalized === '/examples') return { key: 'examples' };
  if (normalized === '/explore') return { key: 'explore' };
  if (normalized === '/shelves') return { key: 'shelves' };
  if (normalized === '/settings') return { key: 'settings' };
  return { key: 'lexicon' };
};

