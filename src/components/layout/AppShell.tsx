import React, { useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  BarChart3,
  Calendar,
  CloudSun,
  FileSpreadsheet,
  History,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  MessageSquare,
  Moon,
  RefreshCw,
  ScanLine,
  ShieldAlert,
  Sun,
  User,
  Users,
  X,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { syncService } from '../../services/syncService';
import { MaizeLogo } from '../common/MaizeLogo';

interface NavItem {
  to: string;
  labelKey: string;
  icon: React.FC<{ className?: string }>;
}

export const AppShell: React.FC<{
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, subtitle, actions, children }) => {
  const { t, language, setLanguage, theme, toggleTheme, isOnline } = useApp();
  const { user, effectiveRole, routePreviewRole, setRoutePreviewRole, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const queuedCount = syncService.getQueue().filter((i) => i.status === 'queued' || i.status === 'failed').length;

  const farmerNav: NavItem[] = [
    { to: '/farmer/dashboard', labelKey: 'navDashboard', icon: LayoutDashboard },
    { to: '/farmer/diagnose', labelKey: 'navDiagnose', icon: ScanLine },
    { to: '/farmer/history', labelKey: 'navHistory', icon: History },
    { to: '/farmer/weather', labelKey: 'navWeather', icon: CloudSun },
    { to: '/farmer/calendar', labelKey: 'navCalendar', icon: Calendar },
    { to: '/farmer/discussion', labelKey: 'navDiscussion', icon: MessageSquare },
    { to: '/farmer/profile', labelKey: 'navProfile', icon: User },
  ];

  const extensionNav: NavItem[] = [
    { to: '/extension/dashboard', labelKey: 'navExtDashboard', icon: LayoutDashboard },
    { to: '/extension/cases', labelKey: 'navExtCases', icon: ScanLine },
    { to: '/extension/map', labelKey: 'navExtMap', icon: MapPin },
    { to: '/farmer/discussion', labelKey: 'navDiscussion', icon: MessageSquare },
    { to: '/admin/outbreaks', labelKey: 'navAdminOutbreaks', icon: AlertOctagon },
    { to: '/admin/reports', labelKey: 'navAdminReports', icon: FileSpreadsheet },
  ];

  const adminNav: NavItem[] = [
    { to: '/admin/dashboard', labelKey: 'navAdminDashboard', icon: BarChart3 },
    { to: '/admin/users', labelKey: 'navAdminUsers', icon: Users },
    { to: '/admin/farmers', labelKey: 'navAdminFarmers', icon: User },
    { to: '/admin/extension-agents', labelKey: 'navAdminAgents', icon: ShieldAlert },
    { to: '/admin/outbreaks', labelKey: 'navAdminOutbreaks', icon: AlertOctagon },
    { to: '/admin/reports', labelKey: 'navAdminReports', icon: FileSpreadsheet },
    { to: '/farmer/discussion', labelKey: 'navDiscussion', icon: MessageSquare },
  ];

  const activeNav =
    effectiveRole === 'admin'
      ? adminNav
      : effectiveRole === 'extension_agent'
      ? extensionNav
      : farmerNav;

  const roleLabel =
    effectiveRole === 'admin'
      ? 'Administrator'
      : effectiveRole === 'extension_agent'
      ? 'Extension Agent'
      : 'Smallholder Farmer';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex bg-[#FAF8F5] dark:bg-[#0C1310] text-stone-900 dark:text-stone-100">
      {/* Desktop Sidebar (260px) */}
      <aside className="hidden lg:flex lg:flex-col lg:w-[264px] lg:shrink-0 border-r border-stone-200 dark:border-stone-800 bg-white dark:bg-[#101814]">
        <div className="px-6 py-5 border-b border-stone-200 dark:border-stone-800 flex items-center gap-3">
          <MaizeLogo className="w-7 h-7 shrink-0" />
          <Link
            to="/"
            className="text-base font-bold tracking-tight text-emerald-950 dark:text-emerald-200 font-display whitespace-nowrap"
          >
            {t('brandName')}
          </Link>
        </div>

        <div className="px-6 py-3.5 border-b border-stone-200/70 dark:border-stone-800/70 text-xs text-stone-600 dark:text-stone-400">
          <div className="font-medium text-stone-900 dark:text-stone-100 truncate">
            {user?.full_name || user?.name || user?.phone_number || 'Authenticated Workspace'}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-stone-500 dark:text-stone-400">
            <span>{roleLabel}</span>
            {user?.region && (
              <>
                <span aria-hidden="true">·</span>
                <span className="truncate">{user.region}</span>
              </>
            )}
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Workspace navigation">
          {activeNav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-emerald-900 text-white dark:bg-emerald-800 dark:text-white'
                      : 'text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800/70'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{t(item.labelKey)}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sidebar Footer Controls */}
        <div className="p-4 border-t border-stone-200 dark:border-stone-800 space-y-3">
          {/* Language & Theme Switcher */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1 p-1 rounded-lg bg-stone-100 dark:bg-stone-800 flex-1">
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`flex-1 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                  language === 'en'
                    ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                    : 'text-stone-600 dark:text-stone-400'
                }`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLanguage('am')}
                className={`flex-1 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap cursor-pointer ${
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
              aria-label={theme === 'light' ? t('darkTheme') : t('lightTheme')}
              className="p-2 rounded-lg border border-stone-200 dark:border-stone-700 text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
            >
              {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
          </div>

          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400 px-1">
            <span>{isOnline ? t('onlineStatus') : t('offlineStatus')}</span>
            {queuedCount > 0 && (
              <Link
                to="/farmer/diagnose"
                className="font-mono tabular-nums text-amber-700 dark:text-amber-400 hover:underline"
              >
                {queuedCount} queued
              </Link>
            )}
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 hover:text-red-700 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-lg border border-stone-200 dark:border-stone-800 transition-colors whitespace-nowrap cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>{t('signOut')}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 px-6 py-3.5 border-b border-stone-200 dark:border-stone-800 bg-[#FAF8F5]/95 dark:bg-[#0C1310]/95 backdrop-blur-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 -ml-2 rounded-lg text-stone-700 dark:text-stone-300 hover:bg-stone-200/60 dark:hover:bg-stone-800 cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400 truncate">
              <span className="font-medium text-stone-700 dark:text-stone-300">{roleLabel}</span>
              <span aria-hidden="true">/</span>
              <span className="text-stone-900 dark:text-stone-100 font-semibold truncate">{title}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {routePreviewRole && !user && (
              <div className="hidden sm:flex items-center gap-2 text-xs text-amber-800 dark:text-amber-300">
                <span>UI Preview ({routePreviewRole})</span>
                <span aria-hidden="true">·</span>
                <button
                  type="button"
                  onClick={() => {
                    const next =
                      routePreviewRole === 'farmer'
                        ? 'extension_agent'
                        : routePreviewRole === 'extension_agent'
                        ? 'admin'
                        : 'farmer';
                    setRoutePreviewRole(next);
                    navigate(
                      next === 'admin'
                        ? '/admin/dashboard'
                        : next === 'extension_agent'
                        ? '/extension/dashboard'
                        : '/farmer/dashboard'
                    );
                  }}
                  className="underline hover:no-underline cursor-pointer whitespace-nowrap"
                >
                  Switch Role
                </button>
              </div>
            )}
            {actions}
          </div>
        </header>

        {/* Mobile Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 lg:hidden flex">
            <div
              className="fixed inset-0 bg-black/60"
              onClick={() => setMobileMenuOpen(false)}
              aria-hidden="true"
            />
            <div className="relative w-72 max-w-[85vw] bg-white dark:bg-[#101814] h-full flex flex-col z-10 border-r border-stone-200 dark:border-stone-800">
              <div className="px-5 py-4 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <MaizeLogo className="w-6 h-6" />
                  <span className="font-bold text-sm font-display">{t('brandName')}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 rounded-lg text-stone-500 hover:text-stone-900 dark:hover:text-stone-100"
                  aria-label="Close navigation menu"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                {activeNav.map((item) => {
                  const Icon = item.icon;
                  const active = location.pathname === item.to;
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium ${
                        active
                          ? 'bg-emerald-900 text-white'
                          : 'text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800'
                      }`}
                    >
                      <Icon className="w-4 h-4 shrink-0" />
                      <span>{t(item.labelKey)}</span>
                    </Link>
                  );
                })}
              </nav>

              <div className="p-4 border-t border-stone-200 dark:border-stone-800 space-y-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setLanguage(language === 'en' ? 'am' : 'en')}
                    className="flex-1 py-2 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700"
                  >
                    {language === 'en' ? 'አማርኛ' : 'English'}
                  </button>
                  <button
                    type="button"
                    onClick={toggleTheme}
                    className="flex-1 py-2 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700"
                  >
                    {theme === 'light' ? t('darkTheme') : t('lightTheme')}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full py-2 text-xs font-medium text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50 rounded-lg"
                >
                  {t('signOut')}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Page Viewport */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-100 font-display">
                {title}
              </h1>
              {subtitle && (
                <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400 max-w-3xl leading-relaxed">
                  {subtitle}
                </p>
              )}
            </div>
            {queuedCount > 0 && effectiveRole === 'farmer' && (
              <Link
                to="/farmer/diagnose"
                className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-amber-900 dark:text-amber-200 bg-amber-100/80 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-800 rounded-lg whitespace-nowrap shrink-0"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span className="tabular-nums">{queuedCount} offline item(s) ready to sync</span>
              </Link>
            )}
          </div>

          {children}
        </main>
      </div>
    </div>
  );
};
