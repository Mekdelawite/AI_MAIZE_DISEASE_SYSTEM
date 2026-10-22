import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getStoredToken, setOnUnauthorized, setStoredToken } from '../services/api';
import { authService, LoginPayload } from '../services/authService';
import { UserRecord, UserRole } from '../types/api';
import { useApp } from './AppContext';

interface AuthContextValue {
  user: UserRecord | null;
  token: string | null;
  loading: boolean;
  sessionError: string | null;
  routePreviewRole: UserRole | null;
  setRoutePreviewRole: (role: UserRole | null) => void;
  effectiveRole: UserRole | null;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<UserRecord>;
  logout: () => void;
  refreshUser: () => Promise<UserRecord | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const PREVIEW_ROLE_KEY = 'maizecare_route_preview_role';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { setLanguage, notify } = useApp();
  const [user, setUser] = useState<UserRecord | null>(null);
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [loading, setLoading] = useState<boolean>(() => Boolean(getStoredToken()));
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [routePreviewRole, setRoutePreviewRoleState] = useState<UserRole | null>(() => {
    try {
      const saved = sessionStorage.getItem(PREVIEW_ROLE_KEY);
      if (saved === 'farmer' || saved === 'extension_agent' || saved === 'admin') {
        return saved;
      }
    } catch {
      // ignore
    }
    return null;
  });

  const setRoutePreviewRole = useCallback((role: UserRole | null) => {
    setRoutePreviewRoleState(role);
    try {
      if (!role) {
        sessionStorage.removeItem(PREVIEW_ROLE_KEY);
      } else {
        sessionStorage.setItem(PREVIEW_ROLE_KEY, role);
      }
    } catch {
      // ignore
    }
  }, []);

  const logout = useCallback(() => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setSessionError(null);
    setRoutePreviewRole(null);
  }, [setRoutePreviewRole]);

  useEffect(() => {
    setOnUnauthorized(() => {
      setStoredToken(null);
      setToken(null);
      setUser(null);
      notify('Your session has expired or is unauthorized. Please sign in again.', 'warning');
    });
    return () => setOnUnauthorized(null);
  }, [notify]);

  const refreshUser = useCallback(async (): Promise<UserRecord | null> => {
    const activeToken = getStoredToken();
    if (!activeToken) {
      setUser(null);
      setLoading(false);
      return null;
    }

    setLoading(true);
    setSessionError(null);
    try {
      const fetchedUser = await authService.getCurrentUser();
      setUser(fetchedUser);
      if (fetchedUser?.preferred_language === 'am' || fetchedUser?.preferred_language === 'en') {
        setLanguage(fetchedUser.preferred_language);
      }
      return fetchedUser;
    } catch (err: any) {
      if (err?.status === 401 || err?.status === 403) {
        setStoredToken(null);
        setToken(null);
        setUser(null);
      } else {
        setSessionError(err?.message || 'Unable to verify session with server.');
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [setLanguage]);

  useEffect(() => {
    if (token) {
      refreshUser();
    } else {
      setLoading(false);
    }
  }, [token, refreshUser]);

  const login = useCallback(
    async (payload: LoginPayload): Promise<UserRecord> => {
      const { token: newToken, user: loggedInUser } = await authService.login(payload);
      setStoredToken(newToken);
      setToken(newToken);
      setRoutePreviewRole(null);

      // If /api/auth/login didn't include complete user details, fetch /api/auth/me
      if (!loggedInUser || !loggedInUser.role) {
        const me = await authService.getCurrentUser();
        setUser(me);
        if (me?.preferred_language === 'am' || me?.preferred_language === 'en') {
          setLanguage(me.preferred_language);
        }
        return me;
      }

      setUser(loggedInUser);
      if (loggedInUser.preferred_language === 'am' || loggedInUser.preferred_language === 'en') {
        setLanguage(loggedInUser.preferred_language);
      }
      return loggedInUser;
    },
    [setLanguage, setRoutePreviewRole]
  );

  const effectiveRole: UserRole | null = user?.role || routePreviewRole || null;
  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        sessionError,
        routePreviewRole,
        setRoutePreviewRole,
        effectiveRole,
        isAuthenticated,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
