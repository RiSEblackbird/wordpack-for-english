import React from 'react';
import ReactDOM from 'react-dom/client';
import type { ReactNode } from 'react';
import { App } from './App';
import { AuthProvider } from './AuthContext';
import { SettingsProvider } from './SettingsContext';
import { ModalProvider } from './ModalContext';
import { ConfirmDialogProvider } from './ConfirmDialogContext';
import { NotificationsProvider } from './NotificationsContext';

const defaultGoogleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '';

interface AppProvidersProps {
  children: ReactNode;
  googleClientId?: string;
}

/**
 * アプリ全体で共有するコンテキストをまとめてラップする。
 * なぜ: 認証・設定・モーダル・通知などの横断的な状態を入口で集約し、
 *       App コンポーネントを描画専用の責務へ限定するため。
 */
export const AppProviders: React.FC<AppProvidersProps> = ({
  children,
  googleClientId,
}) => {
  const resolvedClientId = googleClientId ?? defaultGoogleClientId;
  return (
    <AuthProvider clientId={resolvedClientId}>
      <SettingsProvider>
        <ModalProvider>
          <ConfirmDialogProvider>
            <NotificationsProvider>{children}</NotificationsProvider>
          </ConfirmDialogProvider>
        </ModalProvider>
      </SettingsProvider>
    </AuthProvider>
  );
};

const container = document.getElementById('root');

if (container) {
  ReactDOM.createRoot(container).render(
    <React.StrictMode>
      <AppProviders>
        <App />
      </AppProviders>
    </React.StrictMode>,
  );
}
