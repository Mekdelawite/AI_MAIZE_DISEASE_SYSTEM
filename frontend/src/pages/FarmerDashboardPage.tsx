import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Calendar,
  CloudSun,
  History,
  MapPin,
  MessageSquare,
  RefreshCw,
  ScanLine,
  Trash2,
  UserCheck,
  WifiOff,
} from 'lucide-react';
import { ConfirmDialog, EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { diagnosisService } from '../services/diagnosisService';
import { discussionService } from '../services/discussionService';
import { profileService } from '../services/profileService';
import { offlineDiagnosisStore, type OfflineDiagnosisRecord } from '../services/offlineDiagnosisStore';
import { weatherService } from '../services/weatherService';
import maizeBanner640 from '../assets/images/farmer_dashboard_maize_banner_640.webp';
import maizeBanner1280 from '../assets/images/farmer_dashboard_maize_banner_1280.webp';
import {
  CropCalendarData,
  DiagnosisHistoryItem,
  DiscussionPost,
  ProfileResponseData,
  WeatherData,
} from '../types/api';
import { formatConfidence, formatDateTime } from '../utils/media';

export const FarmerDashboardPage: React.FC = () => {
  const { t, notify, language, isOnline } = useApp();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [history, setHistory] = useState<DiagnosisHistoryItem[]>([]);
  const [historyCount, setHistoryCount] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | number | null>(null);
  const [deletingHistory, setDeletingHistory] = useState(false);

  const [profileData, setProfileData] = useState<ProfileResponseData | null>(null);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [weatherError, setWeatherError] = useState<string | null>(null);

  const [calendar, setCalendar] = useState<CropCalendarData | null>(null);
  const [posts, setPosts] = useState<DiscussionPost[]>([]);
  const [offlineQueue, setOfflineQueue] = useState<OfflineDiagnosisRecord[]>([]);
  const dashboardRequestId = useRef(0);

  const loadDashboardData = useCallback(async () => {
    const requestId = ++dashboardRequestId.current;
    setHistoryLoading(true);
    setHistoryError(null);

    if (!isOnline) {
      setHistory([]);
      setHistoryCount(0);
      setHistoryLoading(false);
      setProfileData(null);
      setWeather(null);
      setWeatherError(t('calendarOffline'));
      setCalendar(null);
      setPosts([]);
      return;
    }

    // Start independent dashboard requests together so history does not delay
    // profile, weather, calendar, or discussion data.
    profileService
      .getProfile()
      .then((res) => {
        if (requestId === dashboardRequestId.current) setProfileData(res);
      })
      .catch(() => {
        if (requestId === dashboardRequestId.current) setProfileData(null);
      });

    weatherService
      .getFarmerWeather('metric')
      .then((res) => {
        if (requestId === dashboardRequestId.current) {
          setWeather(res);
          setWeatherError(null);
        }
      })
      .catch((err: any) => {
        if (requestId === dashboardRequestId.current) {
          setWeather(null);
          setWeatherError(err?.message || 'Weather unavailable');
        }
      });

    weatherService
      .getCropCalendar()
      .then((res) => {
        if (requestId === dashboardRequestId.current) setCalendar(res);
      })
      .catch(() => {
        if (requestId === dashboardRequestId.current) setCalendar(null);
      });

    discussionService
      .getPosts({ page: 1, per_page: 3 })
      .then((res) => {
        if (requestId === dashboardRequestId.current) {
          setPosts(res.posts.slice(0, 3));
        }
      })
      .catch(() => {
        if (requestId === dashboardRequestId.current) setPosts([]);
      });

    try {
      const result = await diagnosisService.getHistoryWithCount(5);
      if (requestId === dashboardRequestId.current) {
        setHistory(result.items);
        setHistoryCount(result.totalCount);
      }
    } catch (err: any) {
      if (requestId === dashboardRequestId.current) {
        setHistoryError(err?.message || 'Unable to load diagnosis history.');
      }
    } finally {
      if (requestId === dashboardRequestId.current) {
        setHistoryLoading(false);
      }
    }
  }, [isOnline, t]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    if (user?.role !== 'farmer' || user.id === undefined || user.id === null) {
      setOfflineQueue([]);
      return;
    }

    let active = true;
    const refreshOfflineQueue = async () => {
      try {
        const records = await offlineDiagnosisStore.getAll(user.id);
        if (active) setOfflineQueue(records);
      } catch (error) {
        console.error('Could not load the farmer offline diagnosis queue:', error);
      }
    };

    void refreshOfflineQueue();
    window.addEventListener(
      'maizecare:offline-diagnosis-queue-changed',
      refreshOfflineQueue,
    );
    window.addEventListener(
      'maizecare:offline-diagnosis-sync-status',
      refreshOfflineQueue,
    );
    return () => {
      active = false;
      window.removeEventListener(
        'maizecare:offline-diagnosis-queue-changed',
        refreshOfflineQueue,
      );
      window.removeEventListener(
        'maizecare:offline-diagnosis-sync-status',
        refreshOfflineQueue,
      );
    };
  }, [user?.id, user?.role]);

  const farmerProfile = profileData?.farmer_profile;
  const hasCoordinates =
    farmerProfile?.latitude !== undefined &&
    farmerProfile?.latitude !== null &&
    farmerProfile?.longitude !== undefined &&
    farmerProfile?.longitude !== null;

  const currentCropStage = calendar?.current_stage;
  const upcomingReminders = calendar?.upcoming_reminders ?? [];
  const recentDiagnosisId = history[0]?.diagnosis_id ?? history[0]?.id;

  const handleDeleteHistory = async () => {
    if (deleteTargetId === null) return;
    setDeletingHistory(true);
    try {
      await diagnosisService.deleteHistoryItem(deleteTargetId);
      setHistory((current) => current.filter((item) =>
        String(item.diagnosis_id ?? item.id) !== String(deleteTargetId)
      ));
      setHistoryCount((count) => Math.max(0, count - 1));
      notify(`Diagnosis record #${deleteTargetId} deleted.`, 'success');
      setDeleteTargetId(null);
    } catch (err: any) {
      notify(err?.message || 'Failed to delete diagnosis record.', 'error');
    } finally {
      setDeletingHistory(false);
    }
  };

  return (
    <AppShell
      title={language === 'am' ? 'የአርሶ አደር ዳሽቦርድ' : 'Farmer Dashboard'}
      subtitle={language === 'am'
        ? 'የምርመራ ታሪክዎን፣ የአየር ሁኔታንና የሰብል መረጃን ይመልከቱ።'
        : 'Review your diagnosis history, local weather and maize crop information.'}
    >
      <section
        className="relative mb-6 overflow-hidden rounded-[1.75rem] bg-[#14532D] text-white shadow-[0_16px_44px_rgba(20,83,45,0.18)] sm:mb-8"
      >
        <img
          src={maizeBanner640}
          srcSet={`${maizeBanner640} 640w, ${maizeBanner1280} 1280w`}
          sizes="100vw"
          alt=""
          aria-hidden="true"
          loading="eager"
          fetchPriority="high"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover object-[center_58%]"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage: 'linear-gradient(90deg, rgba(20, 83, 45, 0.96) 0%, rgba(20, 83, 45, 0.91) 54%, rgba(20, 83, 45, 0.74) 100%)',
          }}
        />
        <div className="relative grid min-h-[340px] gap-7 p-5 sm:min-h-[300px] sm:grid-cols-[1.2fr_0.8fr] sm:items-center sm:gap-8 sm:p-8 lg:p-10">
          <div className="min-w-0">
            <span className="inline-flex items-center rounded-full bg-white/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-emerald-50 ring-1 ring-white/15">
              {language === 'am' ? 'የእርሻ ሁኔታዎ' : 'Your field at a glance'}
            </span>
            <h2 className="mt-4 break-words text-[1.7rem] font-bold leading-tight tracking-tight text-white font-display sm:text-4xl">
              {language === 'am' ? 'እንኳን ደህና መጡ' : 'Hello'}{user?.full_name ? `, ${user.full_name}` : ''}
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-emerald-50/90 sm:text-base">
              {language === 'am'
                ? 'የበቆሎ ቅጠልዎን ይመርምሩ እና ለእርሻዎ ተግባራዊ ምክር ያግኙ።'
                : 'Check a maize leaf and get practical guidance for your farm.'}
            </p>
            <Link
              to="/farmer/diagnose"
              className="mt-5 inline-flex min-h-12 items-center gap-2.5 rounded-xl bg-white px-5 py-3 text-sm font-bold text-[#14532D] shadow-lg shadow-emerald-950/10 transition hover:bg-lime-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              <ScanLine className="h-5 w-5" />
              <span>{t('diagnoseMaizeLeaf')}</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-1">
            <div className="min-w-0 rounded-2xl bg-white/10 p-4 ring-1 ring-white/15 backdrop-blur-sm">
              <p className="flex items-center gap-2 text-xs font-medium text-emerald-100">
                <MapPin className="h-4 w-4 shrink-0" />
                {language === 'am' ? 'አካባቢ' : 'Farm location'}
              </p>
              <p className="mt-2 break-words text-sm font-semibold text-white">
                {farmerProfile?.woreda || user?.woreda || farmerProfile?.region || user?.region || (language === 'am' ? 'አልተዘጋጀም' : 'Not set')}
              </p>
              {(farmerProfile?.region || user?.region) && (farmerProfile?.woreda || user?.woreda) && (
                <p className="mt-0.5 truncate text-xs text-emerald-100/80">{farmerProfile?.region || user?.region}</p>
              )}
            </div>
            <div className="min-w-0 rounded-2xl bg-white/10 p-4 ring-1 ring-white/15 backdrop-blur-sm">
              <p className="flex items-center gap-2 text-xs font-medium text-emerald-100">
                <CloudSun className="h-4 w-4 shrink-0" />
                {language === 'am' ? 'የአየር ሁኔታ' : 'Local weather'}
              </p>
              <p className="mt-2 break-words text-sm font-semibold text-white">
                {weather && (weather.temperature !== undefined || weather.temp !== undefined)
                  ? `${weather.temperature ?? weather.temp}°C`
                  : weatherError || (language === 'am' ? 'አይገኝም' : 'Unavailable')}
              </p>
              {weather && (
                <p className="mt-0.5 truncate text-xs text-emerald-100/80">
                  {weather.description || weather.condition || weather.city || weather.woreda || ''}
                </p>
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="mb-7 grid grid-cols-2 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
        <Link
          to="/farmer/history"
          className="farmer-card flex min-h-32 min-w-0 flex-col justify-between p-4 transition hover:-translate-y-0.5 hover:shadow-md sm:p-5"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>Saved Records</span>
            <History className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
          </div>
          <div className="mt-4">
            <h2 className="break-words text-sm font-bold text-stone-900 dark:text-stone-100 font-display sm:text-base">
              {t('navHistory')}
            </h2>
            <p className="mt-1 text-xs text-stone-600 dark:text-stone-400 tabular-nums">
              {historyLoading
                ? 'Checking server...'
                : historyError
                  ? 'Count unavailable'
                  : `${historyCount} saved record${historyCount === 1 ? '' : 's'}`}
            </p>
          </div>
        </Link>

        <Link
          to="/farmer/weather"
          className="farmer-card flex min-h-32 min-w-0 flex-col justify-between p-4 transition hover:-translate-y-0.5 hover:shadow-md sm:p-5"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>Field Conditions</span>
            <CloudSun className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="mt-4">
            <h2 className="break-words text-sm font-bold text-stone-900 dark:text-stone-100 font-display sm:text-base">
              {t('navWeather')}
            </h2>
            <p className="mt-1 text-xs text-stone-600 dark:text-stone-400 tabular-nums">
              {weather && (weather.temperature !== undefined || weather.temp !== undefined)
                ? `${weather.temperature ?? weather.temp}°C · ${weather.description || weather.condition || 'Live'}`
                : 'Check woreda weather'}
            </p>
          </div>
        </Link>

        <Link
          to="/farmer/calendar"
          className="farmer-card flex min-h-32 min-w-0 flex-col justify-between p-4 transition hover:-translate-y-0.5 hover:shadow-md sm:p-5"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>{language === 'am' ? 'የአሁኑ የሰብል ደረጃ' : 'Current crop stage'}</span>
            <Calendar className="h-4 w-4 text-emerald-800 dark:text-emerald-400" />
          </div>
          <div className="mt-4">
            <h2 className="break-words text-sm font-bold text-stone-900 dark:text-stone-100 font-display sm:text-base">
              {currentCropStage?.label || t('navCalendar')}
            </h2>
            <p className="mt-1 line-clamp-2 text-xs text-stone-600 dark:text-stone-400">
              {currentCropStage?.activities?.[0] || (language === 'am' ? 'የሰብል ምክሮችን ይመልከቱ' : 'View stage-based crop guidance')}
            </p>
          </div>
        </Link>

        <Link
          to="/farmer/discussion"
          className="farmer-card flex min-h-32 min-w-0 flex-col justify-between p-4 transition hover:-translate-y-0.5 hover:shadow-md sm:p-5"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>Extension Support</span>
            <MessageSquare className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
          </div>
          <div className="mt-4">
            <h2 className="break-words text-sm font-bold text-stone-900 dark:text-stone-100 font-display sm:text-base">
              {t('navDiscussion')}
            </h2>
            <p className="mt-1 text-xs text-stone-600 dark:text-stone-400">
              Ask questions & read extension advisories
            </p>
          </div>
        </Link>
      </div>

      {/* Main Two-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Recent Diagnoses & Community */}
        <div className="lg:col-span-7 space-y-6">
          <section
            role={recentDiagnosisId !== undefined && recentDiagnosisId !== null ? 'link' : undefined}
            tabIndex={recentDiagnosisId !== undefined && recentDiagnosisId !== null ? 0 : undefined}
            aria-label={language === 'am' ? 'የቅርብ ጊዜ ምርመራዎች፤ የቅርብ ጊዜውን ምርመራ ለመክፈት ካርዱን ያግብሩ' : 'Recent leaf diagnoses. Activate the card to open the latest diagnosis.'}
            onClick={(event) => {
              if (recentDiagnosisId === undefined || recentDiagnosisId === null || (event.target as HTMLElement).closest('a, button')) return;
              navigate(`/farmer/history/${encodeURIComponent(String(recentDiagnosisId))}`);
            }}
            onKeyDown={(event) => {
              if (recentDiagnosisId === undefined || recentDiagnosisId === null || event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return;
              event.preventDefault();
              navigate(`/farmer/history/${encodeURIComponent(String(recentDiagnosisId))}`);
            }}
            className={`farmer-card overflow-hidden transition ${history.length > 0 ? 'cursor-pointer hover:border-emerald-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 dark:hover:border-emerald-800' : ''}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 bg-stone-50/70 px-5 py-4 dark:border-stone-800 dark:bg-stone-900/30 sm:px-6">
              <div>
                <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">Recent Leaf Diagnoses</h2>
                <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">Open the latest diagnosis or select a record below.</p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={loadDashboardData}
                  aria-label={t('refresh')}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-stone-200 text-stone-600 transition hover:bg-white hover:text-stone-900 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-white"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
                <Link to="/farmer/history" className="text-xs font-semibold text-emerald-800 hover:underline dark:text-emerald-400">
                  View all
                </Link>
              </div>
            </div>

            {historyLoading ? (
              <div className="p-5"><LoadingSkeleton rows={3} /></div>
            ) : historyError ? (
              <div className="p-5"><ErrorState title="Could not fetch recent diagnoses" message={historyError} onRetry={loadDashboardData} /></div>
            ) : history.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  title="No leaf diagnoses recorded yet"
                  description="Upload a maize leaf photo to classify potential foliar diseases and receive treatment recommendations from the server."
                  actionLabel={t('diagnoseLeaf')}
                  onAction={() => navigate('/farmer/diagnose')}
                />
              </div>
            ) : (
              <div className="divide-y divide-stone-100 dark:divide-stone-800">
                {history.map((item, index) => {
                  const id = item.diagnosis_id ?? item.id;
                  return (
                    <div key={String(id)} className="group flex items-stretch gap-2 px-3 py-2 transition hover:bg-emerald-50/60 dark:hover:bg-emerald-950/20 sm:px-5">
                      <Link
                        to={`/farmer/history/${id}`}
                        aria-label={`Open diagnosis details for ${item.disease_class || item.class_name || 'leaf diagnosis'}`}
                        className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl p-2.5 outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 sm:gap-4 sm:p-3"
                      >
                        <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${index === 0 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300' : 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300'}`}>
                          <ScanLine className="h-5 w-5" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="truncate text-sm font-semibold text-stone-900 dark:text-stone-100">
                              {item.disease_class || item.class_name || 'Classified Leaf'}
                            </span>
                            {index === 0 && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">Latest</span>}
                          </span>
                          <span className="mt-1 block truncate text-xs text-stone-500 dark:text-stone-400">
                            {formatDateTime(item.created_at)} · Confidence {formatConfidence(item.confidence)}
                          </span>
                        </span>
                        <span className="hidden shrink-0 items-center gap-1 text-xs font-semibold text-emerald-800 group-hover:underline dark:text-emerald-400 sm:inline-flex">
                          {t('viewDetails')} <ArrowRight className="h-3.5 w-3.5" />
                        </span>
                      </Link>
                      <button
                        type="button"
                        onClick={() => setDeleteTargetId(id)}
                        aria-label={`Delete diagnosis record ${id}`}
                        className="my-auto inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-stone-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Community Discussion Preview */}
          <div className="pt-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                Community Discussion Board
              </h2>
              <Link
                to="/farmer/discussion"
                className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline"
              >
                Open Board
              </Link>
            </div>
            {posts.length === 0 ? (
              <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 text-xs text-stone-600 dark:text-stone-400 flex items-center justify-between gap-4">
                <span>No discussion posts loaded yet. Ask a question or view regional extension updates.</span>
                <Link
                  to="/farmer/discussion"
                  className="px-3 py-1.5 font-medium text-white bg-emerald-800 rounded-lg whitespace-nowrap shrink-0"
                >
                  Ask Question
                </Link>
              </div>
            ) : (
              <div className="farmer-card divide-y divide-stone-100 overflow-hidden dark:divide-stone-800">
                {posts.map((post) => (
                  <div key={String(post.id)} className="p-4">
                    <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
                      <span>{post.post_type || 'question'}</span>
                      <span aria-hidden="true">·</span>
                      <span>{post.author_name || 'Community Member'}</span>
                      <span aria-hidden="true">·</span>
                      <span className="font-mono tabular-nums">{formatDateTime(post.created_at)}</span>
                    </div>
                    <Link
                      to="/farmer/discussion"
                      className="mt-1 block text-sm font-semibold text-stone-900 dark:text-stone-100 hover:text-emerald-800 dark:hover:text-emerald-400"
                    >
                      {post.title}
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Profile Completeness, Weather, Calendar & Offline Queue */}
        <div className="lg:col-span-5 space-y-6">
          {/* Profile & Location Status */}
          <div className="farmer-card min-w-0 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-medium text-emerald-800 dark:text-emerald-400">
                <UserCheck className="w-4 h-4" />
                <span>Farmer Profile & Location</span>
              </div>
              <Link
                to="/farmer/profile"
                className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline"
              >
                Edit Profile
              </Link>
            </div>
            <div className="mt-3 text-sm text-stone-800 dark:text-stone-200 space-y-1">
              <p>
                <span className="text-stone-500">Region / Woreda: </span>
                <span className="font-medium">
                  {farmerProfile?.region || user?.region || 'Not set'} ·{' '}
                  {farmerProfile?.woreda || user?.woreda || 'Not set'}
                </span>
              </p>
              <p className="flex items-center gap-1.5 text-xs text-stone-600 dark:text-stone-400">
                <MapPin className="w-3.5 h-3.5 shrink-0" />
                {hasCoordinates ? (
                  <span className="font-mono tabular-nums">
                    GPS: {farmerProfile?.latitude}, {farmerProfile?.longitude}
                  </span>
                ) : (
                  <span>Coordinates not configured — add coordinates in Profile for precise local weather.</span>
                )}
              </p>
            </div>
          </div>

          {/* Weather Preview Card */}
          <div className="farmer-card min-w-0 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-stone-900 dark:text-stone-100 font-display">
                Local Farm Weather
              </h3>
              <Link
                to="/farmer/weather"
                className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline"
              >
                Full Weather
              </Link>
            </div>
            {weather ? (
              <div className="mt-4">
                <div className="flex items-baseline justify-between">
                  <span className="text-3xl font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                    {weather.temperature ?? weather.temp ?? t('calendarUnavailable')}
                    {weather.temperature !== undefined || weather.temp !== undefined ? '°C' : ''}
                  </span>
                  <span className="text-xs text-stone-600 dark:text-stone-400">
                    {weather.city || weather.woreda || weather.region || 'Configured Location'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-stone-600 dark:text-stone-400">
                  {weather.description || weather.condition || 'Live reading'}
                  {weather.humidity !== undefined ? ` · Humidity: ${weather.humidity}%` : ''}
                </p>
              </div>
            ) : (
              <p className="mt-3 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                {weatherError || 'Configure your farm coordinates or search by city on the Weather page.'}
              </p>
            )}
          </div>

          {/* Crop Calendar Preview */}
          <div className="farmer-card min-w-0 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
                <h3 className="text-sm font-bold text-stone-900 dark:text-stone-100 font-display">
                  Maize Crop Calendar
                </h3>
              </div>
              <Link
                to="/farmer/calendar"
                className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline"
              >
                View Schedule
              </Link>
            </div>
            {currentCropStage ? (
              <div className="mt-4 rounded-2xl bg-emerald-50/80 p-4 dark:bg-emerald-950/25">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
                  {language === 'am' ? 'የአሁኑ ደረጃ' : 'Current growth stage'}
                </p>
                <p className="mt-1 break-words text-base font-bold text-stone-900 dark:text-stone-100">
                  {currentCropStage.label}
                </p>
                <p className="mt-1 text-xs text-stone-600 dark:text-stone-400">
                  {currentCropStage.month_name}
                  {currentCropStage.activities?.[0] ? ` · ${currentCropStage.activities[0]}` : ''}
                </p>
              </div>
            ) : (
              <p className="mt-3 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                Open the Crop Calendar page to load stage-specific maize guidance for your saved region and woreda.
              </p>
            )}
          </div>

          {(upcomingReminders.length > 0 || calendar?.regional_guidance) && (
            <section className="farmer-card min-w-0 p-4 sm:p-6" aria-label={language === 'am' ? 'የእርሻ ምክሮችና ማሳሰቢያዎች' : 'Field guidance and reminders'}>
              <h3 className="text-sm font-bold text-stone-900 dark:text-stone-100 font-display">
                {language === 'am' ? 'ለእርሻዎ የተመረጡ ምክሮች' : 'Guidance for your farm'}
              </h3>
              {calendar?.regional_guidance && (
                <p className="mt-2 break-words text-sm leading-relaxed text-stone-600 dark:text-stone-300">
                  {calendar.regional_guidance}
                </p>
              )}
              {upcomingReminders.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {upcomingReminders.slice(0, 3).map((reminder) => (
                    <li key={`${reminder.activity_key}-${reminder.scheduled_date}`} className="flex min-w-0 items-start gap-3 rounded-2xl bg-[#F7F8F4] p-3 dark:bg-stone-900/70">
                      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-lime-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        <Calendar className="h-4 w-4" aria-hidden="true" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block break-words text-sm font-semibold text-stone-800 dark:text-stone-200">
                          {language === 'am' ? reminder.title_am : reminder.title}
                        </span>
                        <span className="mt-0.5 block text-xs text-stone-500 dark:text-stone-400">
                          {formatDateTime(reminder.scheduled_date)}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {/* Offline Synchronization Status */}
          <div className="farmer-card min-w-0 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <WifiOff className="w-4 h-4 text-stone-600 dark:text-stone-400" />
                <h3 className="text-sm font-bold text-stone-900 dark:text-stone-100 font-display">
                  Offline Sync Queue
                </h3>
              </div>
              <Link
                to="/farmer/diagnose"
                className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline"
              >
                {t('offlineSyncQueueTitle')}
              </Link>
            </div>
            <p className="mt-2 text-xs text-stone-600 dark:text-stone-400 leading-relaxed tabular-nums">
              {offlineQueue.length === 0
                ? t('noOfflineDiagnoses')
                : `${offlineQueue.filter((record) => record.sync_status === 'pending').length} ${t('pendingDiagnosesLabel')} · ${
                    offlineQueue.filter((record) => record.sync_status === 'synced').length
                  } ${t('synchronizedDiagnosesCount')}`}
            </p>
          </div>
        </div>
      </div>
      <ConfirmDialog
        open={deleteTargetId !== null}
        title="Delete Diagnosis Record"
        description={`Are you sure you want to permanently delete diagnosis record #${deleteTargetId}?`}
        confirmLabel={t('delete')}
        cancelLabel={t('cancel')}
        variant="danger"
        loading={deletingHistory}
        onConfirm={handleDeleteHistory}
        onCancel={() => setDeleteTargetId(null)}
      />
    </AppShell>
  );
};
