import React from 'react';
import { AppRightRail, RailCard } from '../../components/AppRightRail';
import { SettingsPanel } from '../../components/SettingsPanel';
import { Badge } from '../../shared/ui';

interface SettingsPageProps {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ focusRef }) => (
  <div className="dictionary-main">
    <div className="dictionary-workspace">
      <div className="dictionary-primary">
        <div className="dictionary-page-heading">
          <div className="dictionary-page-title">
            <h2>Settings</h2>
            <p>辞書操作、音声、表示、生成設定を調整します。</p>
          </div>
          <div className="dictionary-top-actions">
            <Badge variant="accent">dictionary preferences</Badge>
          </div>
        </div>
        <section className="dictionary-section">
          <SettingsPanel focusRef={focusRef} />
        </section>
      </div>
      <AppRightRail>
        <RailCard title="設定の影響範囲" badge="live">
          <p className="dictionary-rail-copy">
            生成モデル、音声、表示密度の変更は各画面に反映されます。進行中の生成はこのキューで継続して確認できます。
          </p>
        </RailCard>
      </AppRightRail>
    </div>
  </div>
);
