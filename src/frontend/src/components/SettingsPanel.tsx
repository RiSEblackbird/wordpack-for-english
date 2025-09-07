import React from 'react';
import { useSettings } from '../SettingsContext';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings, setSettings } = useSettings();
  return (
    <section>
      <label>
        API ベースURL
        <input
          ref={focusRef as React.RefObject<HTMLInputElement>}
          value={settings.apiBase}
          onChange={(e) => setSettings({ ...settings, apiBase: e.target.value })}
        />
      </label>
    </section>
  );
};
