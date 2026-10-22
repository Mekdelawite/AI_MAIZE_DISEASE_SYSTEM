import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

import {
  getStoredToken,
  setOnUnauthorized,
  setStoredToken,
} from '../services/api';

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
  canLoginOffline: boolean;
  loginOffline: () => UserRecord;
  login: (payload: LoginPayload) => Promise<UserRecord>;
  logout: () => void;
  refreshUser: () => Promise<UserRecord | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const PREVIEW_ROLE_KEY = 'maizecare_route_preview_role';
const OFFLINE_USER_KEY = 'maize_offline_user';

/**
 * Store the last server-verified profile for offline app restoration.
 * This profile restores the local interface only; it is not server
 * authorization or proof of a currently valid session.
 */
function saveOfflineUser(user: UserRecord | null): void {
  try {
    if (user) {
      localStorage.setItem(OFFLINE_USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(OFFLINE_USER_KEY);
    }
  } catch {
    // Browser storage may be unavailable.
  }
}

/**
 * Read a previously saved user profile for explicit offline access.
 */
function getOfflineUser(): UserRecord | null {
  try {
    const saved = localStorage.getItem(OFFLINE_USER_KEY);

    if (!saved) {
      return null;
    }

    const parsed: unknown = JSON.parse(saved);

    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'role' in parsed &&
      (
        parsed.role === 'farmer' ||
        parsed.role === 'extension_agent' ||
        parsed.role === 'admin'
      )
    ) {
      return parsed as UserRecord;
    }
  } catch {
    // Ignore invalid or unavailable cached data.
  }

  return null;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { setLanguage, notify } = useApp();

  const [user, setUser] = useState<UserRecord | null>(null);

  const [token, setToken] = useState<string | null>(() =>
    getStoredToken()
  );

  const [loading, setLoading] = useState<boolean>(() =>
    Boolean(getStoredToken())
  );

  const [sessionError, setSessionError] = useState<string | null>(null);
  const [offlineMode, setOfflineMode] = useState(false);

  const [routePreviewRole, setRoutePreviewRoleState] =
    useState<UserRole | null>(() => {
      try {
        const saved = sessionStorage.getItem(PREVIEW_ROLE_KEY);

        if (
          saved === 'farmer' ||
          saved === 'extension_agent' ||
          saved === 'admin'
        ) {
          return saved;
        }
      } catch {
        // Ignore unavailable session storage.
      }

      return null;
    });

  const setRoutePreviewRole = useCallback(
    (role: UserRole | null): void => {
      setRoutePreviewRoleState(role);

      try {
        if (!role) {
          sessionStorage.removeItem(PREVIEW_ROLE_KEY);
        } else {
          sessionStorage.setItem(PREVIEW_ROLE_KEY, role);
        }
      } catch {
        // Ignore unavailable session storage.
      }
    },
    []
  );

  /**
   * Log out of the current session while preserving the last saved
   * profile so the user can explicitly choose offline access later.
   */
  const logout = useCallback((): void => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setOfflineMode(false);
    setSessionError(null);
    setLoading(false);
    setRoutePreviewRole(null);

    // Intentionally preserve OFFLINE_USER_KEY.
  }, [setRoutePreviewRole]);

  /**
   * Handle server responses that indicate an invalid or expired token.
   */
  useEffect(() => {
    setOnUnauthorized(() => {
      setStoredToken(null);
      setToken(null);
      setUser(null);
      setOfflineMode(false);
      setLoading(false);

      const message =
        'Your session has expired or is unauthorized. Please sign in again.';

      setSessionError(message);
      notify(message, 'warning');
    });

    return () => {
      setOnUnauthorized(null);
    };
  }, [notify]);

  /**
   * Verify the active token and restore the current user.
   *
   * Important:
   * - This callback does not depend on user or offlineMode.
   * - That prevents user-state updates from repeatedly triggering
   *   the refresh effect and creating an endless loading loop.
   * - A missing token does not clear an explicitly restored offline
   *   user. Logout handles clearing the user itself.
   */
  const refreshUser = useCallback(
    async (): Promise<UserRecord | null> => {
      const activeToken = getStoredToken();

      if (!activeToken) {
        setLoading(false);
        return null;
      }

      setLoading(true);
      setSessionError(null);

      try {
        const fetchedUser = await authService.getCurrentUser();

        setUser(fetchedUser);
        setOfflineMode(false);
        saveOfflineUser(fetchedUser);

        if (
          fetchedUser.preferred_language === 'am' ||
          fetchedUser.preferred_language === 'en'
        ) {
          setLanguage(fetchedUser.preferred_language);
        }

        return fetchedUser;
      } catch (err: unknown) {
        const error = err as {
          status?: number;
          message?: string;
        };

        if ([401, 403, 404, 422].includes(error?.status ?? 0)) {
          // The server rejected this token or its account identity.
          setStoredToken(null);
          setToken(null);
          setUser(null);
          setOfflineMode(false);

          setSessionError(
            'Your session is no longer valid. Please sign in again.'
          );

          return null;
        }

        // Use the cached profile only when the failure looks like
        // a network/server connectivity problem.
        const cachedUser = getOfflineUser();

        const looksLikeNetworkFailure =
          !navigator.onLine ||
          error?.status == null ||
          error.status === 0 ||
          (typeof error.status === 'number' && error.status >= 500);

        if (cachedUser && looksLikeNetworkFailure) {
          setUser(cachedUser);
          setOfflineMode(true);

          if (
            cachedUser.preferred_language === 'am' ||
            cachedUser.preferred_language === 'en'
          ) {
            setLanguage(cachedUser.preferred_language);
          }

          setSessionError(
            'Offline mode: using your previously saved profile. ' +
              'Server features require an internet connection.'
          );

          return cachedUser;
        }

        setSessionError(
          error?.message || 'Unable to verify session with server.'
        );

        return null;
      } finally {
        setLoading(false);
      }
    },
    [setLanguage]
  );

  /**
   * Verify the user when a token exists.
   *
   * refreshUser has a stable identity, so updating user state will
   * not cause this effect to run repeatedly.
   */
  useEffect(() => {
    if (token) {
      void refreshUser();
    } else {
      setLoading(false);
    }
  }, [token, refreshUser]);

  /**
   * Explicit offline sign-in.
   *
   * This restores the last saved profile locally. It does not verify
   * credentials or establish a server-authenticated session.
   */
  const loginOffline = useCallback((): UserRecord => {
    const cachedUser = getOfflineUser();

    if (!cachedUser) {
      throw new Error(
        'No saved profile is available. Connect to the internet and sign in first.'
      );
    }

    setStoredToken(null);
    setToken(null);
    setUser(cachedUser);
    setOfflineMode(true);
    setLoading(false);

    setSessionError(
      'Offline mode: server authentication and online features are unavailable.'
    );

    setRoutePreviewRole(null);

    if (
      cachedUser.preferred_language === 'am' ||
      cachedUser.preferred_language === 'en'
    ) {
      setLanguage(cachedUser.preferred_language);
    }

    return cachedUser;
  }, [setLanguage, setRoutePreviewRole]);

  /**
   * Online login using the existing backend authentication contract.
   */
  const login = useCallback(
    async (payload: LoginPayload): Promise<UserRecord> => {
      const {
        token: newToken,
        user: loggedInUser,
      } = await authService.login(payload);

      // Remove the previous account's cached profile before replacing it.
      saveOfflineUser(null);

      setStoredToken(newToken);
      setToken(newToken);
      setOfflineMode(false);
      setSessionError(null);
      setLoading(false);
      setRoutePreviewRole(null);

      // Fetch the full user profile if login returned incomplete data.
      if (!loggedInUser || !loggedInUser.role) {
        try {
          const me = await authService.getCurrentUser();

          setUser(me);
          saveOfflineUser(me);

          if (
            me.preferred_language === 'am' ||
            me.preferred_language === 'en'
          ) {
            setLanguage(me.preferred_language);
          }

          return me;
        } catch (error) {
          // Do not leave an incomplete session behind if fetching
          // the full user profile fails immediately after login.
          setStoredToken(null);
          setToken(null);
          setUser(null);
          setOfflineMode(false);
          saveOfflineUser(null);

          throw error;
        }
      }

      setUser(loggedInUser);
      saveOfflineUser(loggedInUser);

      if (
        loggedInUser.preferred_language === 'am' ||
        loggedInUser.preferred_language === 'en'
      ) {
        setLanguage(loggedInUser.preferred_language);
      }

      return loggedInUser;
    },
    [setLanguage, setRoutePreviewRole]
  );

  const effectiveRole: UserRole | null =
    user?.role || routePreviewRole || null;

  const isAuthenticated =
    Boolean(token && user) ||
    Boolean(offlineMode && user);

  const canLoginOffline = Boolean(getOfflineUser());

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
        canLoginOffline,
        loginOffline,
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
