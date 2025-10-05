import React from 'react';
import { useSettings } from '../SettingsContext';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings, setSettings } = useSettings();
  const playbackRateOptions = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
  return (
    <section>
      <div>
        <label>
          カラーテーマ
          <select
            ref={focusRef as React.RefObject<HTMLSelectElement>}
            value={settings.theme}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSettings({ ...settings, theme: e.target.value as 'light' | 'dark' })}
          >
            <option value="dark">ダークカラー（既定）</option>
            <option value="light">ライトカラー</option>
          </select>
        </label>
      </div>
      <div>
        <label>
          音声再生スピード
          <select
            value={String(settings.ttsPlaybackRate)}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
              const parsed = Number(e.target.value);
              const clamped = Number.isFinite(parsed) ? Math.min(2, Math.max(0.5, parsed)) : 1;
              setSettings({ ...settings, ttsPlaybackRate: clamped });
            }}
            aria-describedby="tts-playback-help"
          >
            {playbackRateOptions.map((rate) => (
              <option key={rate} value={String(rate)}>
                {`${rate.toFixed(2).replace(/\.00$/, '')}倍速`}
              </option>
            ))}
          </select>
        </label>
        <div id="tts-playback-help">
          <small>0.5倍〜2.0倍の範囲を0.25刻みで選択できます。</small>
        </div>
      </div>
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
          temperature
          <input
            type="number"
            min={0}
            max={1}
            step={0.1}
            value={settings.temperature}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              const v = Number(e.target.value);
              const clamped = Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0.6;
              setSettings({ ...settings, temperature: clamped });
            }}
            aria-describedby="temperature-help"
          />
        </label>
        <div id="temperature-help">
          <small>0.6–0.8（文体の多様性）、語数厳密なら 0.3–0.5</small>
        </div>
      </div>
      
      
    </section>
  );
};
