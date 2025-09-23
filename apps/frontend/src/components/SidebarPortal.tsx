import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

export const SIDEBAR_PORTAL_CONTAINER_ID = 'app-sidebar-controls';

interface SidebarPortalProps {
  children: React.ReactNode;
  containerId?: string;
}

export const SidebarPortal: React.FC<SidebarPortalProps> = ({ children, containerId = SIDEBAR_PORTAL_CONTAINER_ID }) => {
  const [container, setContainer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const el = document.getElementById(containerId);
    setContainer(el);
  }, [containerId]);

  if (!container) return null;
  return createPortal(children, container);
};
