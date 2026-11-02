import React, { useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  ArrowLeft,
  BarChart3,
  Bell,
  Calendar,
  CloudRain,
  CloudSun,
  Droplets,
  FileSpreadsheet,
  History,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  Megaphone,
  MessageSquare,
  Moon,
  RefreshCw,
  ScanLine,
  ShieldAlert,
  Sun,
  Sprout,
  Stethoscope,
  Info,
  User,
  Users,
  X,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { FarmerNotification, notificationService } from '../../services/notificationService';
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
  const [notificationCount, setNotificationCount] = useState(0);
  const [notificationPanelOpen, setNotificationPanelOpen] = useState(false);
  const [notifications, setNotifications] = useState<FarmerNotification[]>([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationError, setNotificationError] = useState(false);
  const [notificationActionError, setNotificationActionError] = useState(false);
  const [selectedNotificationId, setSelectedNotificationId] = useState<number | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const queuedCount = syncService.getQueue().filter((i) => i.status === 'queued' || i.status === 'failed').length;

  const refreshNotificationCount = React.useCallback(async () => {
    if (effectiveRole !== 'farmer') {
      setNotificationCount(0);
      return;
    }
    try {
      setNotificationCount(await notificationService.getUnreadCount());
    } catch {
      setNotificationError(true);
    }
  }, [effectiveRole]);

  const loadNotifications = React.useCallback(async () => {
    if (effectiveRole !== 'farmer') return;
    setNotificationsLoading(true);
    setNotificationError(false);
    try {
      const [items, count] = await Promise.all([
        notificationService.getFarmerNotifications(),
        notificationService.getUnreadCount(),
      ]);
      setNotifications(items);
      setNotificationCount(count);
    } catch {
      // Keep the last successful data visible while offering an explicit retry.
      setNotificationError(true);
    } finally {
      setNotificationsLoading(false);
    }
  }, [effectiveRole]);

  React.useEffect(() => {
    if (effectiveRole !== 'farmer') {
      setNotificationCount(0);
      setNotifications([]);
      setNotificationPanelOpen(false);
      return;
    }
    void refreshNotificationCount();
    const timer = window.setInterval(() => void refreshNotificationCount(), 45_000);
    const onFocus = () => void refreshNotificationCount();
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', onFocus);
    };
  }, [effectiveRole, refreshNotificationCount]);

  const toggleNotificationPanel = () => {
    const opening = !notificationPanelOpen;
    setNotificationPanelOpen(opening);
    setNotificationActionError(false);
    if (opening) {
      setSelectedNotificationId(null);
      void loadNotifications();
    }
  };

  const handleNotificationClick = async (item: FarmerNotification) => {
    setSelectedNotificationId(item.id);
    setNotificationActionError(false);
    if (item.is_read) return;
    try {
      await notificationService.markNotificationRead(item.id);
      setNotifications((current) => current.map((row) => row.id === item.id ? { ...row, is_read: true } : row));
      await refreshNotificationCount();
    } catch {
      setNotificationActionError(true);
    }
  };

  const handleMarkAllRead = async () => {
    setNotificationActionError(false);
    try {
      await notificationService.markAllNotificationsRead();
      setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
      setNotificationCount(0);
    } catch {
      setNotificationActionError(true);
    }
  };

  const notificationCategory = (type?: string) => {
    const keys: Record<string, string> = {
      outbreak_alert: 'notificationCategoryOutbreak', disease_outbreak_alert: 'notificationCategoryOutbreak',
      regional_alert: 'notificationCategoryRegional', weather_alert: 'notificationCategoryWeather',
      crop_activity: 'notificationCategoryCrop', soil_water_alert: 'notificationCategorySoilWater',
      agricultural_advisory: 'notificationCategoryAgricultural',
      crop_guidance: 'notificationCategoryCrop', crop_cultivation_guidance: 'notificationCategoryCrop',
      diagnosis_advisory: 'notificationCategoryDiagnosis', disease_diagnosis_advisory: 'notificationCategoryDiagnosis',
      announcement: 'notificationCategoryAnnouncement', admin_announcement: 'notificationCategoryAnnouncement',
      system: 'notificationCategorySystem', system_notification: 'notificationCategorySystem',
    };
    return t(keys[type || ''] || 'notificationCategoryGeneral');
  };

  const notificationVisual = (type?: string) => {
    const category = type || '';
    if (['outbreak_alert', 'disease_outbreak_alert', 'regional_alert'].includes(category)) {
      return { Icon: ShieldAlert, tone: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300' };
    }
    if (category === 'weather_alert') {
      return { Icon: CloudRain, tone: 'bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300' };
    }
    if (category === 'soil_water_alert') {
      return { Icon: Droplets, tone: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950/60 dark:text-cyan-300' };
    }
    if (['crop_activity', 'crop_guidance', 'crop_cultivation_guidance'].includes(category)) {
      return { Icon: Sprout, tone: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' };
    }
    if (['diagnosis_advisory', 'disease_diagnosis_advisory'].includes(category)) {
      return { Icon: Stethoscope, tone: 'bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300' };
    }
    if (['announcement', 'admin_announcement'].includes(category)) {
      return { Icon: Megaphone, tone: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300' };
    }
    if (['agricultural_advisory'].includes(category)) {
      return { Icon: Sprout, tone: 'bg-lime-100 text-lime-800 dark:bg-lime-950/60 dark:text-lime-300' };
    }
    return { Icon: Info, tone: 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300' };
  };

  const notificationDate = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString(language === 'am' ? 'am-ET' : 'en-ET', { dateStyle: 'medium', timeStyle: 'short' });
  };

  const selectedNotification = notifications.find((item) => item.id === selectedNotificationId) ?? null;

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
    { to: '/admin/geo-diseases', labelKey: 'navAdminGeoMap', icon: MapPin },
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

  const roleLabel = language === 'am'
    ? effectiveRole === 'admin'
      ? 'አስተዳዳሪ'
      : effectiveRole === 'extension_agent'
      ? 'የግብርና ኤክስቴንሽን ባለሙያ'
      : 'አርሶ አደር'
    : effectiveRole === 'admin'
      ? 'Administrator'
      : effectiveRole === 'extension_agent'
      ? 'Extension Agent'
      : 'Smallholder Farmer';

  const localizedTitles: Record<string, string> = {
    'Diagnosis Result': 'የምርመራ ውጤት',
    'Maize Leaf Diagnosis Result': 'የበቆሎ ቅጠል ምርመራ ውጤት',
    'Geo-Disease Map': 'የበሽታ ጂኦ ካርታ',
    'SMS Notification Dispatch': 'የSMS ማሳወቂያ መላኪያ',
    'Send Regional Alert': 'የክልል ማንቂያ ላክ',
  };
  const localizedSubtitles: Record<string, string> = {
    'Review AI classification, Grad-CAM explainability, and advisory.': 'የAI ምደባን፣ የGrad-CAM ማብራሪያን እና የግብርና ምክርን ይመልከቱ።',
    'MobileNetV2 classification output, Grad-CAM visual attention heatmap, and server-generated agronomic advisory.': 'የMobileNetV2 ምደባ ውጤትን፣ የGrad-CAM ምስላዊ ማብራሪያን እና ከሰርቨር የተዘጋጀ የግብርና ምክርን ይመልከቱ።',
    'Detailed view of historical maize leaf classification, Grad-CAM explainability, and saved advisory.': 'የቀድሞ የበቆሎ ቅጠል ምርመራን፣ የGrad-CAM ማብራሪያን እና የተቀመጠ ምክርን በዝርዝር ይመልከቱ።',
    'Manage your personal information, regional woreda assignment, GPS coordinates for local weather, and SMS alert preferences.': 'የግል መረጃዎን፣ ክልልና ወረዳዎን፣ ለአካባቢያዊ የአየር ሁኔታ የGPS መጋጠሚያዎችን እና የSMS ማንቂያ ምርጫዎችን ያስተዳድሩ።',
  };
  const pageTitle = language === 'am'
    ? localizedTitles[title] || title.replace(/^Diagnosis Record/, 'የምርመራ መዝገብ')
    : title;
  const pageSubtitle = language === 'am' && subtitle ? localizedSubtitles[subtitle] || subtitle : subtitle;

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
            {user?.full_name || user?.name || user?.phone_number || (language === 'am' ? 'የተረጋገጠ የስራ ቦታ' : 'Authenticated Workspace')}
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
              <span className="text-stone-900 dark:text-stone-100 font-semibold truncate">{pageTitle}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {effectiveRole === 'farmer' && (
              <div className="relative">
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    toggleNotificationPanel();
                  }}
                  aria-label={t('notificationsTitle')}
                  aria-expanded={notificationPanelOpen}
                  aria-controls="farmer-notification-center"
                  className="relative rounded-xl border border-stone-200 bg-white p-2.5 text-stone-700 shadow-sm transition-colors hover:border-emerald-300 hover:bg-emerald-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200 dark:hover:border-emerald-800 dark:hover:bg-emerald-950/40 dark:focus-visible:ring-emerald-400"
                >
                  <Bell className="h-4 w-4" />
                  {notificationCount > 0 && (
                    <span className="absolute -right-1.5 -top-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white ring-2 ring-[#FAF8F5] dark:ring-[#0C1310]">
                      {notificationCount > 99 ? '99+' : notificationCount}
                    </span>
                  )}
                </button>

                {notificationPanelOpen && (
                  <section id="farmer-notification-center" aria-label={t('notificationsTitle')} onClick={(event) => event.stopPropagation()} className="absolute right-0 top-[calc(100%+0.75rem)] z-50 flex max-h-[min(78vh,720px)] w-[min(92vw,460px)] flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-2xl shadow-stone-900/15 ring-1 ring-black/5 dark:border-stone-800 dark:bg-[#101814] dark:shadow-black/40 dark:ring-white/5">
                    <div className="flex shrink-0 items-center justify-between gap-3 border-b border-stone-200 bg-stone-50/80 px-4 py-3.5 dark:border-stone-800 dark:bg-stone-900/60 sm:px-5">
                      {selectedNotification ? (
                        <button type="button" onClick={() => setSelectedNotificationId(null)} className="inline-flex items-center gap-2 rounded-md text-sm font-semibold text-stone-900 hover:text-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:text-stone-100 dark:hover:text-emerald-300" aria-label={t('notificationsBack')}>
                          <ArrowLeft className="h-4 w-4" />
                          {t('notificationsBack')}
                        </button>
                      ) : (
                        <div className="min-w-0">
                          <div className="text-sm font-bold text-stone-900 dark:text-stone-100">{t('notificationsTitle')}</div>
                          <div className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">{notificationCount > 0 ? `${notificationCount} ${t('notificationsUnread').toLowerCase()}` : t('notificationsRead')}</div>
                        </div>
                      )}
                      {!selectedNotification && notificationCount > 0 && (
                        <button type="button" onClick={handleMarkAllRead} className="shrink-0 rounded-lg px-2.5 py-2 text-xs font-semibold text-emerald-800 transition-colors hover:bg-emerald-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:text-emerald-300 dark:hover:bg-emerald-950/60 dark:focus-visible:ring-emerald-400">
                          {t('notificationsMarkAllRead')}
                        </button>
                      )}
                    </div>
                    {notificationError && <div role="alert" className="flex items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100"><span>{t('notificationsLoadError')}</span><button type="button" disabled={!isOnline} onClick={() => void loadNotifications()} className="shrink-0 font-semibold underline disabled:opacity-50">{t('notificationsRetry')}</button></div>}
                    {notificationActionError && <div role="alert" className="border-b border-red-200 bg-red-50 px-4 py-2 text-xs text-red-900 dark:border-red-900 dark:bg-red-950/30 dark:text-red-100">{t('notificationsReadError')}</div>}
                    <div className="min-h-0 flex-1 overflow-y-auto">
                      {notificationsLoading ? (
                        <div className="p-4 text-sm text-stone-500 dark:text-stone-400" role="status">{t('notificationsLoading')}</div>
                      ) : selectedNotification ? (
                        <article aria-labelledby="notification-detail-title" className="p-5 sm:p-6">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold text-stone-700 dark:bg-stone-800 dark:text-stone-200">{notificationCategory(selectedNotification.notification_type)}</span>
                            <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${selectedNotification.is_read ? 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300' : 'bg-emerald-700 text-white'}`}>{selectedNotification.is_read ? t('notificationsRead') : t('notificationsUnread')}</span>
                          </div>
                          <h3 id="notification-detail-title" className="mt-4 break-words text-lg font-semibold text-stone-900 dark:text-stone-100">{selectedNotification.title}</h3>
                          <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">{notificationDate(selectedNotification.created_at)}</p>
                          <p className="mt-5 whitespace-pre-line break-words text-sm leading-relaxed text-stone-700 dark:text-stone-300">{selectedNotification.message}</p>
                        </article>
                      ) : notifications.length === 0 ? (
                        notificationError ? null : <div className="p-6 text-center text-sm text-stone-500 dark:text-stone-400">{t('notificationsEmpty')}</div>
                      ) : (
                        <ul className="space-y-2 p-2.5 sm:p-3">
                          {notifications.map((item) => {
                            const { Icon, tone } = notificationVisual(item.notification_type);
                            return (
                            <li key={item.id}>
                              <button
                                type="button"
                                onClick={() => void handleNotificationClick(item)}
                                aria-label={`${item.title}. ${notificationCategory(item.notification_type)}. ${item.is_read ? t('notificationsRead') : t('notificationsUnread')}`}
                                className={`group relative w-full rounded-xl border p-3.5 text-left shadow-sm transition-all hover:-translate-y-px hover:shadow-md focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 dark:focus-visible:ring-emerald-400 sm:p-4 ${item.is_read ? 'border-stone-200 bg-white hover:border-emerald-200 dark:border-stone-800 dark:bg-[#101814] dark:hover:border-emerald-900' : 'border-emerald-200 bg-emerald-50/70 hover:border-emerald-300 dark:border-emerald-900/80 dark:bg-emerald-950/20 dark:hover:border-emerald-800'}`}
                              >
                                <div className="flex items-start gap-3">
                                  <span className={`relative mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${tone}`}>
                                    <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                                    {!item.is_read && <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-emerald-600 ring-2 ring-emerald-50 dark:bg-emerald-400 dark:ring-[#101814]" />}
                                  </span>
                                  <div className="min-w-0 flex-1">
                                    <div className="flex items-start justify-between gap-2">
                                      <div className="line-clamp-2 text-sm font-semibold leading-snug text-stone-900 dark:text-stone-100">{item.title}</div>
                                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${item.is_read ? 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300' : 'bg-emerald-700 text-white'}`}>{item.is_read ? t('notificationsRead') : t('notificationsUnread')}</span>
                                    </div>
                                    <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400">{notificationCategory(item.notification_type)}</div>
                                    <p className="mt-2 line-clamp-2 whitespace-pre-line break-words text-sm leading-relaxed text-stone-700 dark:text-stone-300">{item.message}</p>
                                    <div className="mt-3 flex flex-wrap items-center justify-between gap-x-2 gap-y-1 text-[11px] text-stone-500 dark:text-stone-400"><span className="inline-flex items-center gap-1.5"><Calendar className="h-3.5 w-3.5" aria-hidden="true" />{notificationDate(item.created_at)}</span><span className="font-semibold text-emerald-800 transition-colors group-hover:text-emerald-950 group-focus-visible:text-emerald-950 dark:text-emerald-300 dark:group-hover:text-emerald-200">{t('notificationsOpen')} <span aria-hidden="true">→</span></span></div>
                                  </div>
                                </div>
                              </button>
                            </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </section>
                )}
              </div>
            )}
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
                {pageTitle}
              </h1>
              {subtitle && (
                <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400 max-w-3xl leading-relaxed">
                  {pageSubtitle}
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
