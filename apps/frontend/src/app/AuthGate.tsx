import React from 'react';
import { NotificationsOverlay } from '../components/NotificationsOverlay';
import { useAuth } from '../AuthContext';
import { LoginScreen } from './LoginScreen';

interface AuthGateProps {
  children: React.ReactNode;
}

export const AuthGate: React.FC<AuthGateProps> = ({ children }) => {
  const { user, isGuest } = useAuth();

  if (user || isGuest) {
    return <>{children}</>;
  }

  return (
    <LoginScreen>
      <NotificationsOverlay />
    </LoginScreen>
  );
};
