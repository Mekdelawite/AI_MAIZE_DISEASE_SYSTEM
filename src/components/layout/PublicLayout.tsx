import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { getDefaultHomeForRole } from './ProtectedRoute';

export const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { t, language, setLanguage, theme, toggleTheme } = useApp();
  const { isAuthenticated, effectiveRole } = useAuth();
  const navigate = useNavigate();

  const handlePrimaryCta = () => {
    if (isAuthenticated && effectiveRole) {
      navigate(effectiveRole === 'farmer' ? '/farmer/diagnose' : getDefaultHomeForRole(effectiveRole));
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FAF8F5] dark:bg-[#0C1310] text-stone-900 dark:text-stone-100">
      {/* Strict 3-Zone Top Bar Contract */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-8 px-6 py-4 border-b border-stone-200/80 dark:border-stone-800/80 bg-[#FAF8F5]/95 dark:bg-[#0C1310]/95 backdrop-blur-xs">
        {/* Zone 1: Single text element wordmark */}
        <Link
          to="/"
          className="text-lg font-bold tracking-tight text-emerald-950 dark:text-emerald-200 whitespace-nowrap shrink-0 font-display"
        >
          {t('brandName')}
        </Link>

        {/* Zone 2: 4–5 clean single-line text navigation links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-stone-600 dark:text-stone-300">
          <a
            href="/#workflow"
            className="hover:text-emerald-900 dark:hover:text-emerald-300 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {t('navWorkflow')}
          </a>
          <a
            href="/#capabilities"
            className="hover:text-emerald-900 dark:hover:text-emerald-300 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {t('navCapabilities')}
          </a>
          <a
            href="/#languages"
            className="hover:text-emerald-900 dark:hover:text-emerald-300 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {t('navLanguages')}
          </a>
          <a
            href="/#decision-support"
            className="hover:text-emerald-900 dark:hover:text-emerald-300 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {t('navDecisionSupport')}
          </a>
          <Link
            to={isAuthenticated ? getDefaultHomeForRole(effectiveRole) : '/login'}
            className="hover:text-emerald-900 dark:hover:text-emerald-300 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {isAuthenticated ? t('navDashboard') : t('signIn')}
          </Link>
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={handlePrimaryCta}
            className="px-4 py-2 text-xs font-medium text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {t('diagnoseLeaf')}
          </button>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      {/* Quiet Footer with language/theme controls and navigation links */}
      <footer className="border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-[#101814] py-12 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div>
            <p className="text-base font-bold text-emerald-950 dark:text-emerald-200 font-display">
              {t('brandName')}
            </p>
            <p className="mt-1 text-xs text-stone-600 dark:text-stone-400 max-w-md">
              {t('brandSubtitle')} · Ethiopian Smallholder Maize Advisory & Extension System
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs text-stone-600 dark:text-stone-400">
            <Link to="/login" className="hover:text-stone-900 dark:hover:text-stone-100 whitespace-nowrap">
              {t('signIn')}
            </Link>
            <Link to="/register" className="hover:text-stone-900 dark:hover:text-stone-100 whitespace-nowrap">
              {t('register')}
            </Link>
            <Link to="/recover-password" className="hover:text-stone-900 dark:hover:text-stone-100 whitespace-nowrap">
              {t('recoveryTitle')}
            </Link>

            <div className="flex items-center gap-1 p-1 rounded-lg bg-stone-100 dark:bg-stone-800">
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  language === 'en'
                    ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                    : 'text-stone-600 dark:text-stone-400'
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => setLanguage('am')}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  language === 'am'
                    ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                    : 'text-stone-600 dark:text-stone-400'
                }`}
              >
                አማርኛ
              </button>
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              {theme === 'light' ? t('darkTheme') : t('lightTheme')}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};
