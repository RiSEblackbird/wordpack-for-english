import React from 'react';
import { SettingsPanel } from '../../components/SettingsPanel';
import { Badge } from '../../shared/ui';

interface SettingsPageProps {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ focusRef }) => (
  <div className="dictionary-main">
    <div className="dictionary-page-heading">
      <div className="dictionary-page-title">
        <h2>Settings</h2>
        <p>辞書操作、音声、表示、生成設定を調整する。</p>
      </div>
      <div className="dictionary-top-actions">
        <Badge variant="accent">dictionary preferences</Badge>
      </div>
    </div>
    <section className="dictionary-section">
      <SettingsPanel focusRef={focusRef} />
    </section>
  </div>
);

