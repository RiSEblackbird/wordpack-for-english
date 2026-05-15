import React from 'react';
import { useSettings } from '../SettingsContext';
import { useAuth } from '../AuthContext';

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const SettingsPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings, setSettings } = useSettings();
  const { signOut, isAuthenticating, isGuest } = useAuth();
  const signOutLabel = isGuest ? 'ログアウト（ゲスト閲覧を終了）' : 'ログアウト（Google セッションを終了）';
  const instantGenerate = settings.dictionaryInstantGenerate ?? true;
  const hoverDelay = settings.hoverTooltipDelayMs ?? 180;
  const openGeneratedIn = settings.openGeneratedWordPackIn ?? 'side-peek';
  const density = settings.defaultWordPackDensity ?? 'shelf';
  const ttsEnabled = settings.ttsEnabled ?? true;
  const autoPlayAfterGeneration = settings.autoPlayAfterGeneration ?? false;

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
    <section className="settings-grid">
      <div className="settings-card">
        <h3>Appearance</h3>
        <label className="settings-field">
          <span>カラーテーマ</span>
          <select
            ref={focusRef as React.RefObject<HTMLSelectElement>}
            value={settings.theme}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSettings({ ...settings, theme: e.target.value as 'light' | 'dark' })}
          >
            <option value="dark">ダークカラー（既定）</option>
            <option value="light">ライトカラー</option>
          </select>
        </label>
        <label className="settings-field">
          <span>既定の辞書表示密度</span>
          <select
            value={density}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setSettings({ ...settings, defaultWordPackDensity: e.target.value as typeof density })
            }
          >
            <option value="shelf">Shelf</option>
            <option value="dense">Dense</option>
            <option value="table">Table</option>
          </select>
        </label>
      </div>

      <div className="settings-card">
        <h3>Dictionary behavior</h3>
        <label className="settings-switch">
          <span>未生成語クリックで即生成</span>
          <input
            type="checkbox"
            role="switch"
            checked={instantGenerate}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSettings({ ...settings, dictionaryInstantGenerate: e.target.checked })
            }
          />
        </label>
        <label className="settings-field">
          <span>hover tooltip delay</span>
          <input
            type="number"
            min={0}
            max={1500}
            step={10}
            value={hoverDelay}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSettings({ ...settings, hoverTooltipDelayMs: Number(e.target.value) })
            }
          />
        </label>
        <label className="settings-field">
          <span>生成後に開く場所</span>
          <select
            value={openGeneratedIn}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setSettings({ ...settings, openGeneratedWordPackIn: e.target.value as typeof openGeneratedIn })
            }
          >
            <option value="side-peek">Side Peek</option>
            <option value="detail">Detail Page</option>
          </select>
        </label>
      </div>

      <div className="settings-card">
        <h3>Audio</h3>
        <label className="settings-switch">
          <span>発音を有効化</span>
          <input
            ref={focusRef as React.RefObject<HTMLInputElement>}
            type="checkbox"
            checked={settings.pronunciationEnabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, pronunciationEnabled: e.target.checked })}
          />
        </label>
        <label className="settings-switch">
          <span>TTS enabled</span>
          <input
            type="checkbox"
            role="switch"
            checked={ttsEnabled}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, ttsEnabled: e.target.checked })}
          />
        </label>
        <label className="settings-switch">
          <span>生成後に自動再生</span>
          <input
            type="checkbox"
            role="switch"
            checked={autoPlayAfterGeneration}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSettings({ ...settings, autoPlayAfterGeneration: e.target.checked })
            }
          />
        </label>
      </div>

      <div className="settings-card">
        <h3>Generation</h3>
        <label className="settings-field">
          <span>再生成スコープ</span>
          <select
            value={settings.regenerateScope}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSettings({ ...settings, regenerateScope: e.target.value as any })}
          >
            <option value="all">全体</option>
            <option value="examples">用例のみ</option>
            <option value="collocations">共起のみ</option>
          </select>
        </label>
        <label className="settings-switch">
          <span>確認後に次の用例へ移動</span>
          <input
            type="checkbox"
            checked={settings.autoAdvanceAfterGrade}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettings({ ...settings, autoAdvanceAfterGrade: e.target.checked })}
          />
        </label>
      </div>

      <div className="settings-card">
        <h3>Guest / account</h3>
        <p>ゲスト閲覧は読み取り専用です。生成、削除、音声再生はロックされます。</p>
        <button type="button" onClick={handleSignOut} disabled={isAuthenticating}>
          {signOutLabel}
        </button>
      </div>
    </section>
  );
};
