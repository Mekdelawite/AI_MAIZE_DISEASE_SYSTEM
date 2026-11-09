import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { SupportedLanguage, translations } from '../i18n/translations';
import { apiRequest } from '../services/api';
import { getApiBaseUrl, setApiBaseUrlOverride } from '../utils/media';

export type ThemeMode = 'light' | 'dark';
export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  variant: ToastVariant;
}

export type ConnectionStatus = 'checking' | 'online' | 'offline' | 'unavailable';
export type OfflineSyncStatus = 'idle' | 'syncing' | 'succeeded' | 'failed';

interface AppContextValue {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (theme: ThemeMode) => void;
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string) => string;
  isOnline: boolean;
  connectionStatus: ConnectionStatus;
  offlineSyncStatus: OfflineSyncStatus;
  toasts: ToastMessage[];
  notify: (message: string, variant?: ToastVariant) => void;
  dismissToast: (id: string) => void;
  apiBaseUrl: string;
  updateApiBaseUrl: (url: string | null) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

const THEME_STORAGE_KEY = 'maizecare_theme';
const LANG_STORAGE_KEY = 'maizecare_language';

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === 'dark' || saved === 'light') return saved;
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    } catch {
      // ignore
    }
    return 'light';
  });

  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    try {
      const saved = localStorage.getItem(LANG_STORAGE_KEY);
      if (saved === 'en' || saved === 'am') return saved;
    } catch {
      // ignore
    }
    return 'en';
  });

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(() =>
    typeof navigator !== 'undefined' && navigator.onLine ? 'checking' : 'offline'
  );

  const [offlineSyncStatus, setOfflineSyncStatus] =
    useState<OfflineSyncStatus>('idle');

  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [apiBaseUrl, setApiBaseUrlState] = useState<string>(() => getApiBaseUrl());

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      localStorage.setItem(LANG_STORAGE_KEY, language);
    } catch {
      // ignore
    }
  }, [language]);

  useEffect(() => {
    let active = true;
    let checking = false;

    const checkConnection = async () => {
      if (document.visibilityState !== 'visible') return;
      if (!navigator.onLine) {
        setConnectionStatus('offline');
        return;
      }
      if (checking) return;

      checking = true;
      try {
        const health = await apiRequest<{ status?: string }>('/health', {
          method: 'GET',
          skipAuth: true,
          timeoutMs: 5000,
        });
        if (active) {
          setConnectionStatus(
            navigator.onLine
              ? health?.status === 'healthy'
                ? 'online'
                : 'unavailable'
              : 'offline',
          );
        }
      } catch {
        if (active) {
          setConnectionStatus(navigator.onLine ? 'unavailable' : 'offline');
        }
      } finally {
        checking = false;
      }
    };

    const handleOffline = () => setConnectionStatus('offline');
    const handleOnline = () => {
      setConnectionStatus('checking');
      void checkConnection();
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') void checkConnection();
    };

    void checkConnection();
    const connectionTimer = window.setInterval(() => void checkConnection(), 90_000);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      active = false;
      window.clearInterval(connectionTimer);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    let clearTimer: number | undefined;
    const handleSyncStatus = (event: Event) => {
      const status = (event as CustomEvent<{ status?: string }>).detail?.status;
      if (status !== 'syncing' && status !== 'succeeded' && status !== 'failed') {
        return;
      }

      if (clearTimer !== undefined) window.clearTimeout(clearTimer);
      setOfflineSyncStatus(status);
      if (status !== 'syncing') {
        clearTimer = window.setTimeout(
          () => setOfflineSyncStatus('idle'),
          15_000,
        );
      }
    };

    window.addEventListener(
      'maizecare:offline-diagnosis-sync-status',
      handleSyncStatus,
    );
    return () => {
      window.removeEventListener(
        'maizecare:offline-diagnosis-sync-status',
        handleSyncStatus,
      );
      if (clearTimer !== undefined) window.clearTimeout(clearTimer);
    };
  }, []);

  const setTheme = useCallback((next: ThemeMode) => {
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const setLanguage = useCallback((lang: SupportedLanguage) => {
    setLanguageState(lang);
  }, []);

  const t = useCallback(
    (key: string): string => {
      return translations[language]?.[key] || translations.en[key] || key;
    },
    [language]
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev, { id, message, variant }]);
      setTimeout(() => {
        dismissToast(id);
      }, 5000);
    },
    [dismissToast]
  );

  const updateApiBaseUrl = useCallback((url: string | null) => {
    setApiBaseUrlOverride(url);
    setApiBaseUrlState(getApiBaseUrl());
  }, []);

  const isOnline = connectionStatus === 'online';

  return (
    <AppContext.Provider
      value={{
        theme,
        toggleTheme,
        setTheme,
        language,
        setLanguage,
        t,
        isOnline,
        connectionStatus,
        offlineSyncStatus,
        toasts,
        notify,
        dismissToast,
        apiBaseUrl,
        updateApiBaseUrl,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return ctx;
}
