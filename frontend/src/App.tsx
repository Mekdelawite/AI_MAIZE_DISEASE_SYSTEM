/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import {
  LoadingSkeleton,
  ToastContainer,
} from './components/common/FeedbackStates';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminDiagnosisActivityPage } from './pages/AdminDiagnosisActivityPage';
import { AdminGeoDiseaseMapPage } from './pages/AdminGeoDiseaseMapPage';
import { AboutDevelopersPage } from './pages/AboutDevelopersPage';
import { CropCalendarPage } from './pages/CropCalendarPage';
import { DiagnosisDetailPage } from './pages/DiagnosisDetailPage';
import { DiagnosisHistoryPage } from './pages/DiagnosisHistoryPage';
import DiagnosisPage from "./pages/DiagnosisPage";
import { DiagnosisResultPage } from './pages/DiagnosisResultPage';
import { DiscussionPage } from './pages/DiscussionPage';
import { ExtensionAgentManagementPage } from './pages/ExtensionAgentManagementPage';
import { ExtensionCasesPage } from './pages/ExtensionCasesPage';
import { ExtensionDashboardPage } from './pages/ExtensionDashboardPage';
import { ExtensionFarmerDetailPage } from './pages/ExtensionFarmerDetailPage';
import { ExtensionMapPage } from './pages/ExtensionMapPage';
import { FarmerDashboardPage } from './pages/FarmerDashboardPage';
import { FarmerManagementPage } from './pages/FarmerManagementPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { OutbreakManagementPage } from './pages/OutbreakManagementPage';
import { OutbreakSmsPage } from './pages/OutbreakSmsPage';
import { PasswordRecoveryPage } from './pages/PasswordRecoveryPage';
import { ProfilePage } from './pages/ProfilePage';
import { RegisterPage } from './pages/RegisterPage';
import { ReportsPage } from './pages/ReportsPage';
import { RegionalAlertPage } from './pages/RegionalAlertPage';
import { UserManagementPage } from './pages/UserManagementPage';
import { WeatherPage } from './pages/WeatherPage';
import { useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { getStoredToken } from './services/api';
import { syncPendingDiagnoses } from './services/offlineDiagnosisSyncService';
import { getDefaultHomeForRole } from './components/layout/ProtectedRoute';
function OfflineSyncRunner() {
  const location = useLocation();
  const { user, isAuthenticated } = useAuth();
  const userId = user?.id;
  const syncingRef = React.useRef(false);
  const syncRequestedRef = React.useRef(false);
  const runSyncRef = React.useRef<() => void>(() => undefined);

  const runSync = React.useCallback(async () => {
    if (
      !navigator.onLine ||
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
      await syncPendingDiagnoses(userId, 'en');
    } catch (error) {
      console.error('Offline diagnosis sync could not complete:', error);
    } finally {
      syncingRef.current = false;
      if (syncRequestedRef.current) {
        syncRequestedRef.current = false;
        queueMicrotask(() => runSyncRef.current());
      }
    }
  }, [isAuthenticated, userId]);
  runSyncRef.current = runSync;

  // Retry on startup and after navigation, including after login.
  React.useEffect(() => {
    void runSync();
  }, [runSync, location.pathname]);

  // Retry when the internet returns or the user returns to the tab.
  React.useEffect(() => {
    const handleOnline = () => void runSync();
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void runSync();
      }
    };

    window.addEventListener('online', handleOnline);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('online', handleOnline);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
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
          <ToastContainer />
        </BrowserRouter>
      </AuthProvider>
    </AppProvider>
  );
}
