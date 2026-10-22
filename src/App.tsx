/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { ToastContainer } from './components/common/FeedbackStates';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminGeoDiseaseMapPage } from './pages/AdminGeoDiseaseMapPage';
import { CropCalendarPage } from './pages/CropCalendarPage';
import { DiagnosisDetailPage } from './pages/DiagnosisDetailPage';
import { DiagnosisHistoryPage } from './pages/DiagnosisHistoryPage';
import { DiagnosisPage } from './pages/DiagnosisPage';
import { DiagnosisResultPage } from './pages/DiagnosisResultPage';
import { DiscussionPage } from './pages/DiscussionPage';
import { ExtensionAgentManagementPage } from './pages/ExtensionAgentManagementPage';
import { ExtensionCasesPage } from './pages/ExtensionCasesPage';
import { ExtensionDashboardPage } from './pages/ExtensionDashboardPage';
import { ExtensionMapPage } from './pages/ExtensionMapPage';
import { FarmerDashboardPage } from './pages/FarmerDashboardPage';
import { FarmerManagementPage } from './pages/FarmerManagementPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { OutbreakManagementPage } from './pages/OutbreakManagementPage';
import { PasswordRecoveryPage } from './pages/PasswordRecoveryPage';
import { ProfilePage } from './pages/ProfilePage';
import { RegisterPage } from './pages/RegisterPage';
import { ReportsPage } from './pages/ReportsPage';
import { UserManagementPage } from './pages/UserManagementPage';
import { WeatherPage } from './pages/WeatherPage';

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/recover-password" element={<PasswordRecoveryPage />} />

            {/* Farmer Workspace Routes */}
            <Route
              path="/farmer/dashboard"
              element={
                <ProtectedRoute allowedRoles={['farmer', 'extension_agent', 'admin']}>
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
              path="/admin/outbreaks"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <OutbreakManagementPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/reports"
              element={
                <ProtectedRoute allowedRoles={['extension_agent', 'admin']}>
                  <ReportsPage />
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
