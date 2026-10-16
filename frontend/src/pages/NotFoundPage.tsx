import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { PublicLayout } from '../components/layout/PublicLayout';
import { getDefaultHomeForRole } from '../components/layout/ProtectedRoute';
import { useAuth } from '../context/AuthContext';

export const NotFoundPage: React.FC = () => {
  const { isAuthenticated, effectiveRole } = useAuth();

  return (
    <PublicLayout>
      <div className="max-w-lg mx-auto px-6 py-24 text-center">
        <p className="text-xs font-mono text-emerald-800 dark:text-emerald-400">HTTP 404</p>
        <h1 className="mt-2 text-2xl sm:text-3xl font-bold text-stone-900 dark:text-stone-100 font-display">
          Page Not Found
        </h1>
        <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
          The requested route does not exist in MaizeCare AI.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link
            to={isAuthenticated ? getDefaultHomeForRole(effectiveRole) : '/'}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>{isAuthenticated ? 'Return to Workspace' : 'Return to Home'}</span>
          </Link>
        </div>
      </div>
    </PublicLayout>
  );
};
