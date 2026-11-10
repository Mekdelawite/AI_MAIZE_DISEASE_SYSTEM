/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import {
  LoadingSkeleton,
  ToastContainer,
} from './components/common/FeedbackStates';
import { getDefaultHomeForRole, ProtectedRoute } from './components/layout/ProtectedRoute';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { getStoredToken } from './services/api';
import { syncPendingDiagnoses } from './services/offlineDiagnosisSyncService';
import { useApp } from './context/AppContext';

const AboutDevelopersPage = lazy(() => import('./pages/AboutDevelopersPage').then((page) => ({ default: page.AboutDevelopersPage })));
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage').then((page) => ({ default: page.AdminDashboardPage })));
const AdminDiagnosisActivityPage = lazy(() => import('./pages/AdminDiagnosisActivityPage').then((page) => ({ default: page.AdminDiagnosisActivityPage })));
const AdminGeoDiseaseMapPage = lazy(() => import('./pages/AdminGeoDiseaseMapPage').then((page) => ({ default: page.AdminGeoDiseaseMapPage })));
const CropCalendarPage = lazy(() => import('./pages/CropCalendarPage').then((page) => ({ default: page.CropCalendarPage })));
const DiagnosisDetailPage = lazy(() => import('./pages/DiagnosisDetailPage').then((page) => ({ default: page.DiagnosisDetailPage })));
const DiagnosisHistoryPage = lazy(() => import('./pages/DiagnosisHistoryPage').then((page) => ({ default: page.DiagnosisHistoryPage })));
const DiagnosisPage = lazy(() => import('./pages/DiagnosisPage'));
const DiagnosisResultPage = lazy(() => import('./pages/DiagnosisResultPage').then((page) => ({ default: page.DiagnosisResultPage })));
const DiscussionPage = lazy(() => import('./pages/DiscussionPage').then((page) => ({ default: page.DiscussionPage })));
const ExtensionAgentManagementPage = lazy(() => import('./pages/ExtensionAgentManagementPage').then((page) => ({ default: page.ExtensionAgentManagementPage })));
const ExtensionAgentActivationPage = lazy(() => import('./pages/ExtensionAgentActivationPage').then((page) => ({ default: page.ExtensionAgentActivationPage })));
const ExtensionCasesPage = lazy(() => import('./pages/ExtensionCasesPage').then((page) => ({ default: page.ExtensionCasesPage })));
const ExtensionDashboardPage = lazy(() => import('./pages/ExtensionDashboardPage').then((page) => ({ default: page.ExtensionDashboardPage })));
const ExtensionFarmerDetailPage = lazy(() => import('./pages/ExtensionFarmerDetailPage').then((page) => ({ default: page.ExtensionFarmerDetailPage })));
const ExtensionMapPage = lazy(() => import('./pages/ExtensionMapPage').then((page) => ({ default: page.ExtensionMapPage })));
const FarmerDashboardPage = lazy(() => import('./pages/FarmerDashboardPage').then((page) => ({ default: page.FarmerDashboardPage })));
const FarmerManagementPage = lazy(() => import('./pages/FarmerManagementPage').then((page) => ({ default: page.FarmerManagementPage })));
const LandingPage = lazy(() => import('./pages/LandingPage').then((page) => ({ default: page.LandingPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then((page) => ({ default: page.LoginPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((page) => ({ default: page.NotFoundPage })));
const OutbreakManagementPage = lazy(() => import('./pages/OutbreakManagementPage').then((page) => ({ default: page.OutbreakManagementPage })));
const OutbreakSmsPage = lazy(() => import('./pages/OutbreakSmsPage').then((page) => ({ default: page.OutbreakSmsPage })));
const PasswordRecoveryPage = lazy(() => import('./pages/PasswordRecoveryPage').then((page) => ({ default: page.PasswordRecoveryPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((page) => ({ default: page.ProfilePage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((page) => ({ default: page.RegisterPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((page) => ({ default: page.ReportsPage })));
const RegionalAlertPage = lazy(() => import('./pages/RegionalAlertPage').then((page) => ({ default: page.RegionalAlertPage })));
const UserManagementPage = lazy(() => import('./pages/UserManagementPage').then((page) => ({ default: page.UserManagementPage })));
const VerifyExtensionAgentEmailPage = lazy(() => import('./pages/VerifyExtensionAgentEmailPage').then((page) => ({ default: page.VerifyExtensionAgentEmailPage })));
const WeatherPage = lazy(() => import('./pages/WeatherPage').then((page) => ({ default: page.WeatherPage })));
function OfflineSyncRunner() {
  const location = useLocation();
  const { isOnline } = useApp();
  const { user, isAuthenticated } = useAuth();
  const userId = user?.id;
  const syncingRef = React.useRef(false);
  const syncRequestedRef = React.useRef(false);
  const runSyncRef = React.useRef<() => void>(() => undefined);

  const runSync = React.useCallback(async () => {
    if (
      !navigator.onLine ||
      !isOnline ||
      !isAuthenticated ||
      userId === undefined ||
      !getStoredToken()
    ) {
      return;
    }

    if (syncingRef.current) {
      syncRequestedRef.current = true;
      return;
    }

    syncingRef.current = true;

    try {
      await syncPendingDiagnoses(
        userId,
        user?.preferred_language === 'am' ? 'am' : 'en',
      );
    } catch (error) {
      console.error('Offline diagnosis sync could not complete:', error);
    } finally {
      syncingRef.current = false;
      if (syncRequestedRef.current) {
        syncRequestedRef.current = false;
        queueMicrotask(() => runSyncRef.current());
      }
    }
  }, [isAuthenticated, isOnline, userId, user?.preferred_language]);
  runSyncRef.current = runSync;

  // Retry on startup and after navigation, including after login.
  React.useEffect(() => {
    void runSync();
  }, [runSync, location.pathname]);

  // Retry when the internet returns or the user returns to the tab.
  React.useEffect(() => {
    const handleOnline = () => {
      void runSync();
    };
    const handleQueueChanged = () => void runSync();
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void runSync();
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener(
      'maizecare:offline-diagnosis-queue-changed',
      handleQueueChanged,
    );
    document.addEventListener('visibilitychange', handleVisibilityChange);
    const retryTimer = window.setInterval(() => void runSync(), 60_000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener(
        'maizecare:offline-diagnosis-queue-changed',
        handleQueueChanged,
      );
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.clearInterval(retryTimer);
    };
  }, [runSync]);

  return null;
}

function AuthRouteLoading() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <LoadingSkeleton rows={5} />
    </div>
  );
}

function RouteLoadErrorView() {
  const { t } = useApp();
  return (
    <div className="mx-auto max-w-xl px-5 py-12 text-center" role="alert">
      <p className="text-sm text-stone-700 dark:text-stone-200">{t('routeLoadError')}</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="mt-4 inline-flex min-h-11 items-center justify-center rounded-lg bg-emerald-900 px-4 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
      >
        {t('reloadPage')}
      </button>
    </div>
  );
}

class RouteLoadErrorBoundary extends React.Component<
  React.PropsWithChildren,
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error('A page could not be loaded:', error);
  }

  render() {
    return this.state.hasError ? <RouteLoadErrorView /> : this.props.children;
  }
}

function HomeRoute() {
  const {
    loading,
    isAuthenticated,
    effectiveRole,
    hasExplicitlyLoggedOut,
  } = useAuth();

  if (loading) {
    return <AuthRouteLoading />;
  }

  if (isAuthenticated && effectiveRole) {
    return <Navigate to={getDefaultHomeForRole(effectiveRole)} replace />;
  }

  if (hasExplicitlyLoggedOut) {
    return <Navigate to="/login" replace />;
  }

  return <LandingPage />;
}

function GuestOnlyRoute({ children }: { children: React.ReactNode }) {
  const { loading, isAuthenticated, effectiveRole } = useAuth();

  if (loading) {
    return <AuthRouteLoading />;
  }

  if (isAuthenticated && effectiveRole) {
    return <Navigate to={getDefaultHomeForRole(effectiveRole)} replace />;
  }

  return <>{children}</>;
}


export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <BrowserRouter>
        <OfflineSyncRunner />
        <RouteLoadErrorBoundary>
          <Suspense fallback={<div className="max-w-5xl mx-auto px-6 py-12"><LoadingSkeleton rows={3} /></div>}>
            <Routes>
            {/* Public Routes */}

            <Route path="/" element={<HomeRoute />} />
            <Route
              path="/about"
              element={
                <GuestOnlyRoute>
                  <AboutDevelopersPage />
                </GuestOnlyRoute>
              }
            />
            <Route
              path="/login"
              element={
                <GuestOnlyRoute>
                  <LoginPage />
                </GuestOnlyRoute>
              }
            />
            <Route
              path="/register"
              element={
                <GuestOnlyRoute>
                  <RegisterPage />
                </GuestOnlyRoute>
              }
            />
            <Route path="/recover-password" element={<PasswordRecoveryPage />} />
            <Route path="/activate-extension-agent" element={<ExtensionAgentActivationPage />} />
            <Route path="/verify-extension-agent" element={<VerifyExtensionAgentEmailPage />} />
            {/* Farmer Workspace Routes */}
            <Route
              path="/farmer/dashboard"
              element={
                <ProtectedRoute allowedRoles={['farmer']}>
                  <FarmerDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/diagnose"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <DiagnosisPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/diagnose/result"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <DiagnosisResultPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/history"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <DiagnosisHistoryPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/history/:id"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <DiagnosisDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/profile"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/weather"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <WeatherPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/calendar"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <CropCalendarPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/discussion"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
                  <DiscussionPage />
                </ProtectedRoute>
              }
            />

            {/* Extension-Agent Workspace Routes */}
            <Route
              path="/extension/dashboard"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ExtensionDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/extension/cases"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ExtensionCasesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/extension/farmers/:farmerId"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ExtensionFarmerDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/extension/farmers/:farmerId/diagnoses/:diagnosisId"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ExtensionFarmerDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/extension/map"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ExtensionMapPage />
                </ProtectedRoute>
              }
            />

            {/* Administrator & Outbreak/SMS/Reports Workspace Routes */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AdminDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <UserManagementPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/farmers"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <FarmerManagementPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/geo-diseases"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AdminGeoDiseaseMapPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/extension-agents"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <ExtensionAgentManagementPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/outbreaks/sms"
              element={<ProtectedRoute allowedRoles={['extension_agent', 'admin']}><OutbreakSmsPage /></ProtectedRoute>}
            />
            <Route
              path="/admin/outbreaks"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <OutbreakManagementPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/regional-alerts"
              element={<ProtectedRoute allowedRoles={['admin']}><RegionalAlertPage /></ProtectedRoute>}
            />
            <Route
              path="/admin/reports"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ReportsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/diagnoses"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AdminDiagnosisActivityPage />
                </ProtectedRoute>
              }
            />

            {/* Catch-all 404 */}
            <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </RouteLoadErrorBoundary>
          <ToastContainer />
        </BrowserRouter>
      </AuthProvider>
    </AppProvider>
  );
}
