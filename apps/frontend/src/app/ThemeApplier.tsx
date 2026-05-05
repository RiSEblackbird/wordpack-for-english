import React, { useEffect } from 'react';
import { useSettings } from '../SettingsContext';

export const ThemeApplier: React.FC = () => {
  const { settings } = useSettings();
  useEffect(() => {
    const clsLight = 'theme-light';
    const clsDark = 'theme-dark';
    const body = document.body;
    body.classList.remove(clsLight, clsDark);
    body.classList.add(settings.theme === 'light' ? clsLight : clsDark);
  }, [settings.theme]);
  return null;
};
