import React from 'react';
import { ThemeApplier } from './ThemeApplier';
import { AppProviders } from './AppProviders';
import { AppShell } from './AppShell';
import { AuthGate } from './AuthGate';
import '../shared/styles/index.css';
import './styles/app-shell.css';

export const App: React.FC = () => (
  <AppProviders>
    <ThemeApplier />
    <AuthGate>
      <AppShell />
    </AuthGate>
  </AppProviders>
);
