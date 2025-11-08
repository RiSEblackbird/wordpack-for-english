import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

export const SIDEBAR_PORTAL_CONTAINER_ID = 'app-sidebar-controls';

interface SidebarPortalProps {
  children: React.ReactNode;
  containerId?: string;
}

export const SidebarPortal: React.FC<SidebarPortalProps> = ({ children, containerId = SIDEBAR_PORTAL_CONTAINER_ID }) => {
  /**
   * サイドバー側の DOM コンテナを動的に追跡し、マウント後にポータル描画を可能にする。
   * 副作用: 指定 ID の要素が存在しない場合は null を返し、後続レンダリングで再評価する。
   */
  const [container, setContainer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const el = document.getElementById(containerId);
    setContainer(el);
  }, [containerId]);

  if (!container) return null;
  return createPortal(children, container);
};
