import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SidebarPortal, SIDEBAR_PORTAL_CONTAINER_ID } from './SidebarPortal';

/**
 * SidebarPortal は既存の DOM ノードへ子要素を移して描画する薄いラッパーであり、
 * DOM の有無に応じた挙動をテストで固定化する。
 */
describe('SidebarPortal', () => {
  afterEach(() => {
    const existing = document.getElementById(SIDEBAR_PORTAL_CONTAINER_ID);
    if (existing && existing.parentNode) {
      existing.parentNode.removeChild(existing);
    }
  });

  it('renders children inside the specified container when it exists', () => {
    const host = document.createElement('div');
    host.id = SIDEBAR_PORTAL_CONTAINER_ID;
    document.body.appendChild(host);

    render(
      <SidebarPortal>
        <span>ポータル内テキスト</span>
      </SidebarPortal>,
    );

    expect(host).toContainElement(screen.getByText('ポータル内テキスト'));
  });

  it('renders nothing when the container is missing', () => {
    render(
      <SidebarPortal>
        <span>未表示テキスト</span>
      </SidebarPortal>,
    );

    expect(screen.queryByText('未表示テキスト')).not.toBeInTheDocument();
  });
});
