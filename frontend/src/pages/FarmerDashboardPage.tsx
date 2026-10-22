import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Calendar,
  CloudSun,
  History,
  BellRing,
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
import { notificationService, FarmerNotification } from '../services/notificationService';
import { syncService } from '../services/syncService';
import { weatherService } from '../services/weatherService';
import {
  CropCalendarData,
  DiagnosisHistoryItem,
  DiscussionPost,
  ProfileResponseData,
  QueuedSyncItem,
  WeatherData,
} from '../types/api';
import { formatConfidence, formatDateTime } from '../utils/media';

export const FarmerDashboardPage: React.FC = () => {
  const { t, notify } = useApp();
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
  const [offlineQueue, setOfflineQueue] = useState<QueuedSyncItem[]>([]);
  const [regionalAlerts, setRegionalAlerts] = useState<FarmerNotification[]>([]);

  const loadDashboardData = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    setOfflineQueue(syncService.getQueue());

    // Load recent diagnoses
    try {
      const result = await diagnosisService.getHistoryWithCount(5);
      setHistory(result.items);
      setHistoryCount(result.totalCount);
    } catch (err: any) {
      setHistoryError(err?.message || 'Unable to load diagnosis history.');
    } finally {
      setHistoryLoading(false);
    }

    // Load profile, weather, calendar, and discussion in parallel without blocking primary view
    profileService
      .getProfile()
      .then((res) => setProfileData(res))
      .catch(() => {});

    weatherService
      .getFarmerWeather('metric')
      .then((res) => {
        setWeather(res);
        setWeatherError(null);
      })
      .catch((err: any) => {
        setWeatherError(err?.message || 'Weather unavailable');
      });

    weatherService
      .getCropCalendar()
      .then((res) => setCalendar(res))
      .catch(() => {});

    discussionService
      .getPosts({ page: 1, per_page: 3 })
      .then((res) => setPosts(res.posts.slice(0, 3)))
      .catch(() => {});
    notificationService.getFarmerNotifications().then(setRegionalAlerts).catch(() => {});
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const latestDiagnosis = history[0] || null;
  const farmerProfile = profileData?.farmer_profile;
  const hasCoordinates =
    farmerProfile?.latitude !== undefined &&
    farmerProfile?.latitude !== null &&
    farmerProfile?.longitude !== undefined &&
    farmerProfile?.longitude !== null;

  const calendarStages = calendar?.stages || calendar?.calendar || [];

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
      title={`Welcome${user?.full_name ? `, ${user.full_name}` : ''}`}
      subtitle="Start a new maize leaf diagnosis, review treatment guidance, check local weather and crop stages, or ask a question on the community board."
      actions={
        <Link
          to="/farmer/diagnose"
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors whitespace-nowrap shrink-0"
        >
          <ScanLine className="w-3.5 h-3.5" />
          <span>{t('diagnoseLeaf')}</span>
        </Link>
      }
    >
      {regionalAlerts.length > 0 && <section className="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-5 dark:border-amber-900 dark:bg-amber-950/30">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-amber-950 dark:text-amber-100"><BellRing className="h-4 w-4" />Regional alerts</h2>
        <ul className="space-y-3">{regionalAlerts.slice(0, 5).map((alert) => <li key={alert.id} className="border-t border-amber-200 pt-3 first:border-0 first:pt-0 dark:border-amber-900"><p className="text-xs font-semibold text-amber-950 dark:text-amber-100">{alert.title}</p><p className="mt-1 whitespace-pre-line text-sm text-stone-800 dark:text-stone-200">{alert.message}</p><Link to="/farmer/discussion" className="mt-1 inline-block text-xs font-semibold text-emerald-800 underline dark:text-emerald-300">View community post</Link></li>)}</ul>
      </section>}
      {/* Quick Action Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link
          to="/farmer/diagnose"
          className="rounded-xl border border-emerald-800/30 dark:border-emerald-700/40 bg-emerald-900 text-white p-5 flex flex-col justify-between hover:bg-emerald-800 transition-colors"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-emerald-200">Primary Action</span>
            <ScanLine className="w-5 h-5 text-amber-300" />
          </div>
          <div className="mt-4">
            <h2 className="text-base font-bold font-display">{t('diagnoseLeaf')}</h2>
            <p className="mt-1 text-xs text-emerald-100/90">
              Upload a leaf photo for AI classification & Grad-CAM
            </p>
          </div>
        </Link>

        <Link
          to="/farmer/history"
          className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 flex flex-col justify-between hover:border-stone-300 dark:hover:border-stone-700 transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>Saved Records</span>
            <History className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
          </div>
          <div className="mt-4">
            <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
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
          className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 flex flex-col justify-between hover:border-stone-300 dark:hover:border-stone-700 transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>Field Conditions</span>
            <CloudSun className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="mt-4">
            <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
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
          to="/farmer/discussion"
          className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 flex flex-col justify-between hover:border-stone-300 dark:hover:border-stone-700 transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>Extension Support</span>
            <MessageSquare className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
          </div>
          <div className="mt-4">
            <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
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
        {/* Left Column: Latest & Recent Diagnoses */}
        <div className="lg:col-span-7 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
              Recent Leaf Diagnoses
            </h2>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={loadDashboardData}
                className="inline-flex items-center gap-1 text-xs text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-100 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>{t('refresh')}</span>
              </button>
              <Link
                to="/farmer/history"
                className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline"
              >
                View all
              </Link>
            </div>
          </div>

          {historyLoading ? (
            <LoadingSkeleton rows={3} />
          ) : historyError ? (
            <ErrorState
              title="Could not fetch recent diagnoses"
              message={historyError}
              onRetry={loadDashboardData}
            />
          ) : history.length === 0 ? (
            <EmptyState
              title="No leaf diagnoses recorded yet"
              description="Upload a maize leaf photo to classify potential foliar diseases and receive treatment recommendations from the server."
              actionLabel={t('diagnoseLeaf')}
              onAction={() => navigate('/farmer/diagnose')}
            />
          ) : (
            <div className="space-y-4">
              {latestDiagnosis && (
                <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500 dark:text-stone-400">
                    <span>Latest Diagnosis</span>
                    <span className="font-mono tabular-nums">{formatDateTime(latestDiagnosis.created_at)}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-baseline justify-between gap-4">
                    <h3 className="text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
                      {latestDiagnosis.disease_class || latestDiagnosis.class_name || 'Classified Leaf'}
                    </h3>
                    <span className="text-sm font-mono tabular-nums font-semibold text-emerald-800 dark:text-emerald-400">
                      Confidence: {formatConfidence(latestDiagnosis.confidence)}
                    </span>
                  </div>
                  {latestDiagnosis.advisory?.description && (
                    <p className="mt-2 text-sm text-stone-600 dark:text-stone-400 line-clamp-2 leading-relaxed">
                      {latestDiagnosis.advisory.description}
                    </p>
                  )}
                  <div className="mt-4 pt-4 border-t border-stone-200/70 dark:border-stone-800 flex items-center justify-between gap-3">
                    <span className="text-xs text-stone-500 font-mono">
                      ID: {latestDiagnosis.diagnosis_id ?? latestDiagnosis.id}
                    </span>
                    <div className="flex items-center gap-3">
                      <Link
                        to={`/farmer/history/${latestDiagnosis.diagnosis_id ?? latestDiagnosis.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 dark:text-emerald-400 hover:underline"
                      >
                        <span>View Treatment & Explainability</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                      <button
                        type="button"
                        onClick={() => setDeleteTargetId(latestDiagnosis.diagnosis_id ?? latestDiagnosis.id)}
                        aria-label={`Delete diagnosis record ${latestDiagnosis.diagnosis_id ?? latestDiagnosis.id}`}
                        className="text-stone-400 hover:text-red-600 dark:hover:text-red-400 cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {history.slice(1).length > 0 && (
                <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] divide-y divide-stone-200 dark:divide-stone-800">
                  {history.slice(1).map((item) => {
                    const id = item.diagnosis_id ?? item.id;
                    return (
                      <div key={String(id)} className="p-4 flex items-center justify-between gap-4">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-stone-900 dark:text-stone-100 truncate">
                            {item.disease_class || item.class_name}
                          </p>
                          <p className="text-xs text-stone-500 dark:text-stone-400 font-mono tabular-nums">
                            {formatDateTime(item.created_at)} · Confidence {formatConfidence(item.confidence)}
                          </p>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <Link
                            to={`/farmer/history/${id}`}
                            className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline whitespace-nowrap"
                          >
                            {t('viewDetails')}
                          </Link>
                          <button
                            type="button"
                            onClick={() => setDeleteTargetId(id)}
                            aria-label={`Delete diagnosis record ${id}`}
                            className="text-stone-400 hover:text-red-600 dark:hover:text-red-400 cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

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
              <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] divide-y divide-stone-200 dark:divide-stone-800">
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
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
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
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
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
                    {weather.temperature ?? weather.temp ?? '—'}°C
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
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
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
            {calendarStages.length > 0 ? (
              <div className="mt-3 space-y-2">
                {calendarStages.slice(0, 2).map((stage, idx) => (
                  <div key={idx} className="text-xs border-t border-stone-100 dark:border-stone-800 pt-2">
                    <p className="font-semibold text-stone-900 dark:text-stone-100">
                      {stage.stage_name || stage.name || stage.phase}
                    </p>
                    <p className="text-stone-500 dark:text-stone-400">
                      {Array.isArray(stage.months) ? stage.months.join(', ') : stage.months || stage.description}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                Open the Crop Calendar page to load stage-specific maize guidance for your saved region and woreda.
              </p>
            )}
          </div>

          {/* Offline Synchronization Status */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
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
                Manage Queue
              </Link>
            </div>
            <p className="mt-2 text-xs text-stone-600 dark:text-stone-400 leading-relaxed tabular-nums">
              {offlineQueue.length === 0
                ? 'No offline leaf images currently queued on this device.'
                : `${offlineQueue.filter((i) => i.status === 'queued').length} queued · ${
                    offlineQueue.filter((i) => i.status === 'failed').length
                  } failed · ${offlineQueue.filter((i) => i.status === 'succeeded').length} synced`}
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
