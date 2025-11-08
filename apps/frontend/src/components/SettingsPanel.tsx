import React from 'react';
import { useSettings } from '../SettingsContext';
import { useAuth } from '../AuthContext';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings, setSettings } = useSettings();
  const { signOut, isAuthenticating } = useAuth();

  /**
   * ユーザーが手動でセッションを破棄できるようにする。
   * 副作用: サーバーへログアウト通知を送り、保持中の認証情報を消去する。
   */
  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (err) {
      console.warn('manual sign-out failed', err);
    }
  };
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
      <div>
        <button type="button" onClick={handleSignOut} disabled={isAuthenticating}>
          ログアウト（Google セッションを終了）
        </button>
      </div>
    </section>
  );
};
