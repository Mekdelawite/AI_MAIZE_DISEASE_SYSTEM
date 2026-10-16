import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types/api';
import { LoadingSkeleton } from '../common/FeedbackStates';

export function getDefaultHomeForRole(role?: UserRole | null): string {
  if (role === 'admin') return '/admin/dashboard';
  if (role === 'extension_agent') return '/extension/dashboard';
  return '/farmer/dashboard';
}

export const ProtectedRoute: React.FC<{
  allowedRoles?: UserRole[];
  children: React.ReactNode;
}> = ({ allowedRoles, children }) => {
  const { isAuthenticated, effectiveRole, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-12">
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  if (!isAuthenticated || !effectiveRole) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(effectiveRole)) {
    return <Navigate to={getDefaultHomeForRole(effectiveRole)} replace />;
  }

  return <>{children}</>;
};
