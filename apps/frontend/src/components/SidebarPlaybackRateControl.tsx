import React, { useCallback } from 'react';
import { useSettings } from '../SettingsContext';

const PLAYBACK_RATE_OPTIONS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
// 音量の候補は 0〜300% を 25% 刻みで網羅し、ユーザーの細かな調整要求に応える。
const VOLUME_OPTIONS = [
  0,
  0.25,
  0.5,
  0.75,
  1,
  1.25,
  1.5,
  1.75,
  2,
  2.25,
  2.5,
  2.75,
  3,
];

type Props = {
  isSidebarOpen: boolean;
};

/**
 * サイドメニュー専用の音声再生スピード制御を司るコンポーネント。
 * 設定コンテキストを直接更新し、全画面のTTSボタンへ即座に反映させる。
 */
export const SidebarPlaybackRateControl: React.FC<Props> = ({ isSidebarOpen }) => {
  const { settings, setSettings } = useSettings();

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const parsed = Number(event.target.value);
      const clamped = Number.isFinite(parsed) ? Math.min(2, Math.max(0.5, parsed)) : 1;
      setSettings((prev) => ({ ...prev, ttsPlaybackRate: clamped }));
    },
    [setSettings],
  );
  // 音量選択が変化したときに設定コンテキストへ正規化した値を反映し、全画面で同じボリュームを共有する。
  const handleVolumeChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const parsed = Number(event.target.value);
      // UIから渡される値を0〜3の範囲へ正規化し、アプリ全体で一貫した音量倍率を共有する。
      const clamped = Number.isFinite(parsed) ? Math.min(3, Math.max(0, parsed)) : 1;
      setSettings((prev) => ({ ...prev, ttsVolume: clamped }));
    },
    [setSettings],
  );

  return (
    <section className="sidebar-section" aria-label="音声再生スピード設定" aria-hidden={!isSidebarOpen}>
      <h2>音声コントロール</h2>
      <div className="sidebar-field">
        <label htmlFor="sidebar-tts-playback">音声再生スピード</label>
        <select
          id="sidebar-tts-playback"
          value={String(settings.ttsPlaybackRate)}
          onChange={handleChange}
          disabled={!isSidebarOpen}
          aria-describedby="sidebar-tts-playback-help"
        >
          {PLAYBACK_RATE_OPTIONS.map((rate) => (
            <option key={rate} value={String(rate)}>
              {`${rate.toFixed(2).replace(/\.00$/, '')}倍速`}
            </option>
          ))}
        </select>
        <small id="sidebar-tts-playback-help">0.5倍〜2.0倍の範囲を0.25刻みで調整できます。</small>
      </div>
      <div className="sidebar-field">
        <label htmlFor="sidebar-tts-volume">音量</label>
        <select
          id="sidebar-tts-volume"
          value={String(settings.ttsVolume)}
          onChange={handleVolumeChange}
          disabled={!isSidebarOpen}
          aria-describedby="sidebar-tts-volume-help"
        >
          {VOLUME_OPTIONS.map((volume) => (
            <option key={volume} value={String(volume)}>
              {volume === 0 ? 'ミュート' : `${Math.round(volume * 100)}%`}
            </option>
          ))}
        </select>
        <small id="sidebar-tts-volume-help">0%（ミュート）〜300%まで音量を即座に変更できます。</small>
      </div>
    </section>
  );
};
