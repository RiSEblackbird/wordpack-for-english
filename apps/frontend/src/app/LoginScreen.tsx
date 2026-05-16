import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { MAIN_HEADING_TEXT } from './navigation';
import { GoogleLoginCard } from './GoogleLoginCard';
import './styles/login.css';

interface LoginScreenProps {
  children?: React.ReactNode;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ children }) => {
  const {
    signIn,
    isAuthenticating,
    error,
    clearError,
    missingClientId,
    authBypassActive,
    googleClientId,
    enterGuestMode,
  } = useAuth();
  const [localError, setLocalError] = useState<string | null>(null);
  const loginTitle = missingClientId ? 'Google ログインの設定が必要です' : 'WordPack にサインイン';

  return (
    <main className="login-shell">
      <h1 className="visually-hidden">{MAIN_HEADING_TEXT}</h1>
      {missingClientId ? (
        <section className="login-card" role="alert" aria-live="polite">
          <h2 className="login-title">Google ログインの設定が必要です</h2>
          <p className="login-description">
            VITE_GOOGLE_CLIENT_ID が未設定のため Google のサインインを開始できません。README.md の「Google OAuth クライアントの準備」節を参照し、以下の手順で環境を整えてください。
          </p>
          <h3 className="login-subtitle">設定手順</h3>
          <ol className="login-guide-list">
            <li>`apps/frontend/.env` に VITE_GOOGLE_CLIENT_ID=（Google Cloud Console で発行したクライアント ID）を記載する。</li>
            <li>`apps/backend/.env` や `.env` も同じクライアント ID を設定し、バックエンドと整合させる。</li>
            <li>設定後にフロントエンド開発サーバーを再起動し、ブラウザのキャッシュを削除して再読み込みする。</li>
          </ol>
          <p className="login-guide-hint">
            {authBypassActive
              ? '開発用の認証バイパスが有効なため、このままでもダミーアカウントで利用可能です。正式な OAuth を確認したい場合のみ上記手順を実施してください。'
              : '開発用の認証バイパスが無効な環境では、上記手順を完了するまでアプリへサインインできません。環境変数を設定後に再度アクセスしてください。'}
          </p>
          <button
            type="button"
            className="login-guest-button"
            onClick={() => {
              void enterGuestMode();
            }}
          >
            ゲスト閲覧モード
          </button>
        </section>
      ) : (
        <GoogleLoginCard
          title={loginTitle}
          isAuthenticating={isAuthenticating}
          clearError={clearError}
          error={error}
          localError={localError}
          setLocalError={setLocalError}
          signIn={signIn}
          googleClientId={googleClientId}
        />
      )}
      {children}
    </main>
  );
};
