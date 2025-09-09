import React from 'react';
import { useSettings } from '../SettingsContext';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings, setSettings } = useSettings();
  return (
    <section>
      <div>
        <label>
          発音を有効化
          <input
            ref={focusRef as React.RefObject<HTMLInputElement>}
            type="checkbox"
            checked={settings.pronunciationEnabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, pronunciationEnabled: e.target.checked })}
          />
        </label>
      </div>
      <div>
        <label>
          再生成スコープ
          <select
            value={settings.regenerateScope}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSettings({ ...settings, regenerateScope: e.target.value as any })}
          >
            <option value="all">全体</option>
            <option value="examples">例文のみ</option>
            <option value="collocations">コロケのみ</option>
          </select>
        </label>
      </div>
      <div>
        <label>
          採点後に自動で次へ
          <input
            type="checkbox"
            checked={settings.autoAdvanceAfterGrade}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, autoAdvanceAfterGrade: e.target.checked })}
          />
        </label>
      </div>
      <div>
        <label>
          リクエスト・タイムアウト(ms)
          <input
            type="number"
            min={1000}
            step={1000}
            value={settings.requestTimeoutMs}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, requestTimeoutMs: Math.max(1000, Number(e.target.value || 0)) })}
          />
        </label>
      </div>
    </section>
  );
};
