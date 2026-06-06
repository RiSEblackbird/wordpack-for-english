import type { AppRouteKey } from './routes';

export interface NavigationItem {
  key: Exclude<AppRouteKey, 'wordpackDetail'>;
  label: string;
  legacyLabel: string;
  shortLabel: string;
}

export const NAV_ITEMS: NavigationItem[] = [
  { key: 'lexicon', label: 'Lexicon', legacyLabel: 'WordPack', shortLabel: '辞書' },
  { key: 'reader', label: 'Reader', legacyLabel: '文章インポート', shortLabel: 'Reader' },
  { key: 'examples', label: 'Examples', legacyLabel: '例文一覧', shortLabel: '用例' },
  { key: 'explore', label: 'Explore', legacyLabel: 'Explore', shortLabel: 'Explore' },
  { key: 'shelves', label: 'Shelves', legacyLabel: 'Shelves', shortLabel: '棚' },
  { key: 'settings', label: 'Settings', legacyLabel: '設定', shortLabel: '設定' },
];

export const SIDEBAR_ID = 'app-sidebar';
export const MAIN_MAX_WIDTH = 1560;
export const MAIN_HEADING_TEXT = 'WordPack';
