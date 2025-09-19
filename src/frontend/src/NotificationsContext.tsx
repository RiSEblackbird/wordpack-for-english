import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

export type NotificationStatus = 'progress' | 'success' | 'error';

export interface NotificationItem {
  id: string;
  title: string; // 表示用タイトル（例: 【lemma】の生成処理中...）
  message?: string; // 詳細（例: 新規生成 / 再生成 / 例文の追加生成など）
  status: NotificationStatus;
  createdAt: number;
  updatedAt: number;
  model?: string; // 任意: 使用モデル名（表示用）
}

interface NotificationsContextValue {
  notifications: NotificationItem[];
  add: (input: { title: string; message?: string; status?: NotificationStatus; id?: string; model?: string }) => string;
  update: (id: string, patch: Partial<Pick<NotificationItem, 'title' | 'message' | 'status' | 'model'>>) => void;
  remove: (id: string) => void;
  clearAll: () => void;
}

const NotificationsContext = createContext<NotificationsContextValue | undefined>(undefined);

const STORAGE_KEY = 'wpfe.notifications.v1';

function loadFromStorage(): NotificationItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const items = JSON.parse(raw) as NotificationItem[];
    if (!Array.isArray(items)) return [];
    return items;
  } catch {
    return [];
  }
}

function saveToStorage(items: NotificationItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // ignore
  }
}

export const NotificationsProvider: React.FC<{ children: React.ReactNode } & { persist?: boolean }> = ({ children, persist = true }) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>(() => (persist ? loadFromStorage() : []));
  const idSeq = useRef<number>(0);

  useEffect(() => {
    if (persist) saveToStorage(notifications);
  }, [notifications, persist]);

  const add: NotificationsContextValue['add'] = useCallback((input) => {
    const id = input.id || `n-${Date.now()}-${idSeq.current++}`;
    const now = Date.now();
    const item: NotificationItem = {
      id,
      title: input.title,
      message: input.message,
      status: input.status || 'progress',
      createdAt: now,
      updatedAt: now,
      model: input.model,
    };
    setNotifications((prev) => {
      const next = [...prev, item];
      return next;
    });
    return id;
  }, []);

  const update: NotificationsContextValue['update'] = useCallback((id, patch) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, ...patch, updatedAt: Date.now() } : n)));
  }, []);

  const remove: NotificationsContextValue['remove'] = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => setNotifications([]), []);

  const value = useMemo<NotificationsContextValue>(() => ({ notifications, add, update, remove, clearAll }), [notifications, add, update, remove, clearAll]);

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
};

export function useNotifications(): NotificationsContextValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationsProvider');
  return ctx;
}


