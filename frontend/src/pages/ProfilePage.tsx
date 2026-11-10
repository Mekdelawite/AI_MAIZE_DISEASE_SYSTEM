import React, { useCallback, useEffect, useState } from 'react';
import { Bell, BellOff, CheckCircle2, Edit3, Loader2, MapPin, RefreshCw, Trash2, WifiOff } from 'lucide-react';
import { ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { notificationService } from '../services/notificationService';
import { profileService } from '../services/profileService';
import { offlineDiagnosisStore } from '../services/offlineDiagnosisStore';
import { FarmerNotificationPreferences, ProfileResponseData } from '../types/api';

const PROFILE_CACHE_PREFIX = 'maizecare_profile_v1_';
const DEFAULT_NOTIFICATION_PREFERENCES: FarmerNotificationPreferences = {
  categories: {
    crop_activity: { in_app: true, sms: true, push: false }, weather_alert: { in_app: true, sms: true, push: false },
    soil_water_alert: { in_app: true, sms: true, push: false }, agricultural_advisory: { in_app: true, sms: true, push: false },
    important_alerts: { in_app: true, sms: true, push: false },
  },
  reminder_days_before: 0, quiet_hours: { enabled: false, start: '21:00', end: '07:00' }, timezone: 'Africa/Addis_Ababa',
};
const notificationCategories = ['crop_activity', 'weather_alert', 'soil_water_alert', 'agricultural_advisory', 'important_alerts'] as const;

function decodeVapidKey(value: string): ArrayBuffer {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const decoded = window.atob(normalized + '='.repeat((4 - normalized.length % 4) % 4));
  const buffer = new ArrayBuffer(decoded.length);
  new Uint8Array(buffer).set(
    Uint8Array.from(decoded, (character) => character.charCodeAt(0)),
  );
  return buffer;
}

function normalizeNotificationPreferences(
  value?: FarmerNotificationPreferences,
): FarmerNotificationPreferences {
  return {
    ...DEFAULT_NOTIFICATION_PREFERENCES,
    ...value,
    categories: Object.fromEntries(
      notificationCategories.map((category) => [
        category,
        {
          ...DEFAULT_NOTIFICATION_PREFERENCES.categories[category],
          ...(value?.categories?.[category] ?? {}),
        },
      ]),
    ) as FarmerNotificationPreferences['categories'],
    quiet_hours: {
      ...DEFAULT_NOTIFICATION_PREFERENCES.quiet_hours,
      ...value?.quiet_hours,
    },
  };
}

function readCachedProfile(userId: string | number | undefined): ProfileResponseData | null {
  if (userId === undefined) return null;

  try {
    const cached = localStorage.getItem(`${PROFILE_CACHE_PREFIX}${userId}`);
    if (!cached) return null;

    const parsed: unknown = JSON.parse(cached);
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      !('user' in parsed) ||
      typeof parsed.user !== 'object' ||
      parsed.user === null ||
      !('id' in parsed.user) ||
      String(parsed.user.id) !== String(userId)
    ) {
      return null;
    }

    return parsed as ProfileResponseData;
  } catch {
    return null;
  }
}

export const ProfilePage: React.FC = () => {
  const { t, setLanguage, notify, isOnline } = useApp();
  const { user, refreshUser, logout } = useAuth();

  const [data, setData] = useState<ProfileResponseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deletingAccount, setDeletingAccount] = useState(false);

  // Form fields
  const [fullName, setFullName] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<'en' | 'am'>('en');
  const [region, setRegion] = useState('');
  const [woreda, setWoreda] = useState('');
  const [kebele, setKebele] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [gpsStatus, setGpsStatus] = useState<
    'idle' | 'detecting' | 'detected' | 'denied' | 'unavailable' | 'timeout' | 'error' | 'unsupported' | 'insecure'
  >('idle');
  const [smsOptIn, setSmsOptIn] = useState(false);
  const [notificationPreferences, setNotificationPreferences] = useState<FarmerNotificationPreferences>(DEFAULT_NOTIFICATION_PREFERENCES);
  const [pushStatus, setPushStatus] = useState<
    'loading' | 'enabled' | 'disabled' | 'unsupported' | 'denied' | 'unconfigured' | 'error'
  >('loading');
  const [pushBusy, setPushBusy] = useState(false);
  const [pushError, setPushError] = useState<string | null>(null);

  const syncFormFromResponse = (res: ProfileResponseData) => {
    const u = res.user;
    const fp = res.farmer_profile;
    const savedLanguage = (fp?.preferred_language || u?.preferred_language || 'en') as 'en' | 'am';
    setFullName(fp?.full_name || u?.full_name || u?.name || '');
    setPreferredLanguage(savedLanguage);
    setLanguage(savedLanguage);
    setRegion(fp?.region || u?.region || '');
    setWoreda(fp?.woreda || u?.woreda || '');
    setKebele(fp?.kebele || u?.kebele || '');
    setLatitude(fp?.latitude !== undefined && fp?.latitude !== null ? String(fp.latitude) : '');
    setLongitude(fp?.longitude !== undefined && fp?.longitude !== null ? String(fp.longitude) : '');
    setGpsStatus('idle');
    setSmsOptIn(Boolean(fp?.sms_opt_in));
    setNotificationPreferences(normalizeNotificationPreferences(fp?.notification_preferences));
  };

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSaveSuccess(null);

    const showSavedProfile = (message: string): boolean => {
      const fallback =
        readCachedProfile(user?.id) ??
        (user ? { user, farmer_profile: null } : null);

      if (!fallback) return false;

      setData(fallback);
      syncFormFromResponse(fallback);
      setProfileNotice(message);
      return true;
    };

    if (!isOnline) {
      if (
        !showSavedProfile(
          'No internet connection. Showing saved profile details; editing and saving require internet access.',
        )
      ) {
        setError('No internet connection, and no saved profile is available on this device yet.');
      }
      setLoading(false);
      return;
    }

    try {
      const res = await profileService.getProfile();
      setData(res);
      syncFormFromResponse(res);
      setProfileNotice(null);
      if (user?.id !== undefined) {
        try {
          localStorage.setItem(
            `${PROFILE_CACHE_PREFIX}${user.id}`,
            JSON.stringify(res),
          );
        } catch {
          // Keep the online profile usable if browser storage is unavailable.
        }
      }
    } catch (err: any) {
      if (
        !showSavedProfile(
          'The profile server is unavailable. Showing saved details; reconnect to edit or save changes.',
        )
      ) {
        setError(err?.message || 'Unable to load farmer profile from server.');
      }
    } finally {
      setLoading(false);
    }
  }, [isOnline, user]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (!isOnline) setEditing(false);
  }, [isOnline]);

  useEffect(() => {
    let active = true;
    if (
      user?.role !== 'farmer' ||
      !('serviceWorker' in navigator) ||
      !('PushManager' in window) ||
      !('Notification' in window) ||
      !window.isSecureContext
    ) {
      setPushStatus('unsupported');
      return;
    }

    void (async () => {
      try {
        const [config, registration] = await Promise.all([
          notificationService.getPushConfig(),
          navigator.serviceWorker.getRegistration(),
        ]);
        if (!active) return;
        if (!config.enabled || !config.public_key) {
          setPushStatus('unconfigured');
          return;
        }
        if (!registration) {
          setPushStatus('disabled');
          return;
        }
        const subscription = await registration.pushManager.getSubscription();
        if (!active) return;
        setPushStatus(
          subscription
            ? 'enabled'
            : Notification.permission === 'denied'
              ? 'denied'
              : 'disabled',
        );
      } catch (error) {
        console.error('Could not inspect farmer push-notification status:', error);
        if (active) {
          setPushStatus('error');
          setPushError(t('pushStatusError'));
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [user?.role, t]);

  const savePushPreferences = async (enabled: boolean) => {
    const categories = Object.fromEntries(
      notificationCategories.map((category) => [
        category,
        { ...notificationPreferences.categories[category], push: enabled },
      ]),
    ) as FarmerNotificationPreferences['categories'];
    const updatedPreferences = { ...notificationPreferences, categories };
    const updatedProfile = await profileService.updateProfile({
      notification_preferences: updatedPreferences,
    });
    setNotificationPreferences(updatedPreferences);
    setData((current) => current
      ? {
          ...current,
          farmer_profile: {
            ...(current.farmer_profile ?? {}),
            notification_preferences: updatedPreferences,
          },
        }
      : updatedProfile);
  };

  const handleEnablePush = async () => {
    setPushBusy(true);
    setPushError(null);
    let subscription: PushSubscription | null = null;
    try {
      if (
        !('serviceWorker' in navigator) ||
        !('PushManager' in window) ||
        !('Notification' in window) ||
        !window.isSecureContext
      ) {
        setPushStatus('unsupported');
        return;
      }

      const config = await notificationService.getPushConfig();
      if (!config.enabled || !config.public_key) {
        setPushStatus('unconfigured');
        return;
      }
      const registration = await navigator.serviceWorker.getRegistration();
      if (!registration) {
        setPushStatus('unsupported');
        setPushError(t('pushServiceWorkerMissing'));
        return;
      }

      const permission = Notification.permission === 'granted'
        ? 'granted'
        : await Notification.requestPermission();
      if (permission !== 'granted') {
        setPushStatus(permission === 'denied' ? 'denied' : 'disabled');
        return;
      }

      subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: decodeVapidKey(config.public_key),
        });
      }
      await notificationService.savePushSubscription(subscription.toJSON());
      await savePushPreferences(true);
      setPushStatus('enabled');
    } catch (error) {
      if (subscription) {
        try {
          await notificationService.removePushSubscription(subscription.endpoint);
        } catch (cleanupError) {
          console.error('Could not remove an incomplete server push subscription:', cleanupError);
        }
        try {
          await subscription.unsubscribe();
        } catch (cleanupError) {
          console.error('Could not unsubscribe an incomplete browser push subscription:', cleanupError);
        }
      }
      console.error('Could not enable farmer push notifications:', error);
      setPushStatus('error');
      setPushError(error instanceof Error ? error.message : t('pushStatusError'));
    } finally {
      setPushBusy(false);
    }
  };

  const handleDisablePush = async () => {
    setPushBusy(true);
    setPushError(null);
    try {
      await savePushPreferences(false);
      const registration = await navigator.serviceWorker.getRegistration();
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) {
        let removalError: unknown;
        try {
          await notificationService.removePushSubscription(subscription.endpoint);
        } catch (error) {
          removalError = error;
        }
        const unsubscribed = await subscription.unsubscribe();
        if (removalError) throw removalError;
        if (!unsubscribed) throw new Error(t('pushUnsubscribeFailed'));
      }
      setPushStatus('disabled');
    } catch (error) {
      console.error('Could not disable farmer push notifications:', error);
      setPushStatus('error');
      setPushError(error instanceof Error ? error.message : t('pushStatusError'));
    } finally {
      setPushBusy(false);
    }
  };

  const handleUseGps = () => {
    if (!window.isSecureContext) {
      setGpsStatus('insecure');
      notify(t('profileGpsSecureContext'), 'warning');
      return;
    }

    if (!navigator.geolocation) {
      setGpsStatus('unsupported');
      notify(t('profileGpsUnsupported'), 'warning');
      return;
    }
    const hasSavedGpsLocation =
      data?.farmer_profile?.latitude !== undefined &&
      data.farmer_profile.latitude !== null &&
      data?.farmer_profile?.longitude !== undefined &&
      data.farmer_profile.longitude !== null;
    if (hasSavedGpsLocation && !window.confirm(t('profileGpsReplaceConfirm'))) return;

    setGpsStatus('detecting');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        setGpsStatus('detected');
        notify(t('profileGpsCaptured'), 'info');
      },
      (error) => {
        const status = error.code === 1
          ? 'denied'
          : error.code === 2
            ? 'unavailable'
            : error.code === 3
              ? 'timeout'
              : 'error';
        setGpsStatus(status);
        const message = t({
          denied: 'profileGpsDenied',
          unavailable: 'profileGpsUnavailable',
          timeout: 'profileGpsTimeout',
          error: 'profileGpsError',
        }[status]);
        notify(message, 'warning');
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(null);

    if (!isOnline) {
      notify('An internet connection is required to save profile changes.', 'warning');
      setEditing(false);
      return;
    }

    const parsedLat = latitude.trim() ? Number(latitude) : null;
    const parsedLng = longitude.trim() ? Number(longitude) : null;

    if (parsedLat !== null && (Number.isNaN(parsedLat) || parsedLat < -90 || parsedLat > 90)) {
      notify('Latitude must be between -90 and 90.', 'error');
      return;
    }
    if (parsedLng !== null && (Number.isNaN(parsedLng) || parsedLng < -180 || parsedLng > 180)) {
      notify('Longitude must be between -180 and 180.', 'error');
      return;
    }

    setSaving(true);
    try {
      const updated = await profileService.updateProfile({
        full_name: fullName.trim(),
        preferred_language: preferredLanguage,
        region: region.trim(),
        woreda: woreda.trim(),
        kebele: kebele.trim() || undefined,
        latitude: parsedLat,
        longitude: parsedLng,
        sms_opt_in: smsOptIn,
        ...(user?.role === 'farmer' ? { notification_preferences: notificationPreferences } : {}),
      });

      setData(updated);
      syncFormFromResponse(updated);
      const refreshedUser = await refreshUser();
      setLanguage(refreshedUser?.preferred_language || updated.user?.preferred_language || preferredLanguage);
      setEditing(false);
      setSaveSuccess('Profile updated and confirmed by the server.');
      notify('Farmer profile updated on server.', 'success');
    } catch (err: any) {
      notify(err?.message || 'Failed to update profile on server.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const savedLatitude = data?.farmer_profile?.latitude;
  const savedLongitude = data?.farmer_profile?.longitude;
  const hasSavedCoordinates = savedLatitude != null && savedLongitude != null;
  const coordinatesChanged =
    latitude !== (savedLatitude == null ? '' : String(savedLatitude)) ||
    longitude !== (savedLongitude == null ? '' : String(savedLongitude));
  const gpsStatusKey = gpsStatus === 'detecting'
    ? 'profileGpsDetecting'
    : gpsStatus === 'denied'
      ? 'profileGpsDenied'
      : gpsStatus === 'unavailable'
        ? 'profileGpsUnavailable'
        : gpsStatus === 'timeout'
          ? 'profileGpsTimeout'
          : gpsStatus === 'unsupported'
            ? 'profileGpsUnsupported'
            : gpsStatus === 'insecure'
              ? 'profileGpsSecureContext'
              : gpsStatus === 'error'
                ? 'profileGpsError'
                : null;
  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isOnline || !user?.id) {
      notify(t('profileDeleteAccountOnlineRequired'), 'warning');
      return;
    }
    if (!deletePassword) {
      notify('Enter your password to confirm account deletion.', 'warning');
      return;
    }

    setDeletingAccount(true);
    try {
      await profileService.deleteAccount(deletePassword);
      try {
        await offlineDiagnosisStore.deleteForUser(user.id);
      } catch (cleanupError) {
        console.warn('Could not clear all local offline diagnoses after account deletion:', cleanupError);
      }
      localStorage.removeItem(`maizecare_profile_v1_${user.id}`);
      localStorage.removeItem('maize_offline_user');
      notify(t('profileDeleteAccountSuccess'), 'success');
      setDeleteDialogOpen(false);
      logout();
    } catch (err: any) {
      notify(err?.message || 'Unable to delete your account.', 'error');
    } finally {
      setDeletingAccount(false);
    }
  };

  return (
    <AppShell
      title={t('navProfile')}
      subtitle="Manage your personal information, regional woreda assignment, GPS coordinates for local weather, and SMS alert preferences."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadProfile}
            className="inline-flex min-h-11 items-center gap-1.5 rounded-xl px-2.5 py-2 text-xs font-medium text-stone-700 transition hover:bg-stone-100 dark:text-stone-200 dark:hover:bg-stone-800 sm:px-3"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          {data && !editing && isOnline && (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-[#14532D] px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-[#0f4324]"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Edit Profile</span>
            </button>
          )}
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error || !data ? (
        <ErrorState
          title="Could not load farmer profile"
          message={error || 'Profile payload empty.'}
          onRetry={loadProfile}
        />
      ) : (
        <div className="w-full max-w-3xl space-y-6">
          <section className="farmer-card flex min-w-0 items-center gap-4 p-5 sm:p-6">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-xl font-bold text-[#14532D] dark:bg-emerald-950 dark:text-emerald-200">
              {(fullName || user?.full_name || user?.name || 'F').trim().charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0">
              <p className="break-words text-lg font-bold text-stone-900 dark:text-stone-100">
                {fullName || user?.full_name || user?.name || t('navProfile')}
              </p>
              <p className="mt-1 break-words text-sm text-stone-500 dark:text-stone-400">
                {[region || data.farmer_profile?.region, woreda || data.farmer_profile?.woreda].filter(Boolean).join(' · ') || t('regionLabel')}
              </p>
            </div>
          </section>

          {profileNotice && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/20 p-4 flex items-start gap-2.5 text-xs text-amber-900 dark:text-amber-200" role="status">
              <WifiOff className="w-4 h-4 shrink-0" />
              <span>{profileNotice}</span>
            </div>
          )}

          {saveSuccess && (
            <div className="rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 p-4 flex items-center gap-2.5 text-xs text-emerald-900 dark:text-emerald-200">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{saveSuccess}</span>
            </div>
          )}

          {!data.farmer_profile && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/20 p-4 text-xs text-amber-900 dark:text-amber-200">
              No extended farmer profile record was returned for this account. Saving the form below will submit your profile details to <code className="font-mono">PUT /api/profile</code>.
            </div>
          )}

          <form
            onSubmit={handleSave}
            className="farmer-form farmer-card min-w-0 space-y-6 p-4 sm:p-7"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label htmlFor="prof-name" className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
                  {t('fullNameLabel')}
                </label>
                <input
                  id="prof-name"
                  type="text"
                  disabled={!editing || saving || !isOnline}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
                  {t('phoneLabel')} (Read-only)
                </label>
                <input
                  type="text"
                  disabled
                  value={data.user?.phone_number || data.user?.phone || '—'}
                  className="w-full px-3.5 py-2 text-sm font-mono rounded-lg border border-stone-200 dark:border-stone-800 bg-stone-100 dark:bg-stone-900/50 text-stone-500"
                />
              </div>

              <div>
                <label htmlFor="prof-lang" className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
                  {t('preferredLangLabel')}
                </label>
                <select
                  id="prof-lang"
                  disabled={!editing || saving || !isOnline}
                  value={preferredLanguage}
                  onChange={(e) => {
                    const nextLanguage = e.target.value as 'en' | 'am';
                    setPreferredLanguage(nextLanguage);
                    setLanguage(nextLanguage);
                  }}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                >
                  <option value="en">English (en)</option>
                  <option value="am">አማርኛ / Amharic (am)</option>
                </select>
              </div>

              <div>
                <label htmlFor="prof-region" className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
                  {t('regionLabel')}
                </label>
                <input
                  id="prof-region"
                  type="text"
                  disabled={!editing || saving || !isOnline}
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                />
              </div>

              <div>
                <label htmlFor="prof-woreda" className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
                  {t('woredaLabel')}
                </label>
                <input
                  id="prof-woreda"
                  type="text"
                  disabled={!editing || saving || !isOnline}
                  value={woreda}
                  onChange={(e) => setWoreda(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                />
              </div>

              <div>
                <label htmlFor="prof-kebele" className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
                  {t('kebeleLabel')}
                </label>
                <input
                  id="prof-kebele"
                  type="text"
                  disabled={!editing || saving || !isOnline}
                  value={kebele}
                  onChange={(e) => setKebele(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-stone-200 dark:border-stone-800">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-stone-700 dark:text-stone-300">
                  {t('profileGpsCoordinates')}
                </span>
                {editing && isOnline && (
                  <button
                    type="button"
                    onClick={handleUseGps}
                    disabled={saving || gpsStatus === 'detecting'}
                    aria-busy={gpsStatus === 'detecting'}
                    className="inline-flex min-h-11 items-center gap-1 text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline disabled:cursor-wait disabled:opacity-60"
                  >
                    {gpsStatus === 'detecting'
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      : <MapPin className="w-3.5 h-3.5" />}
                    <span>{t(gpsStatus === 'detecting' ? 'profileGpsDetecting' : 'profileCaptureGps')}</span>
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div>
                  <label htmlFor="prof-lat" className="block text-xs text-stone-500 mb-1">
                    {t('latitudeLabel')}
                  </label>
                  <input
                    id="prof-lat"
                    type="text"
                    disabled={!editing || saving || !isOnline}
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="e.g. 9.1245"
                    className="w-full px-3.5 py-2 text-sm font-mono tabular-nums rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                  />
                </div>
                <div>
                  <label htmlFor="prof-lng" className="block text-xs text-stone-500 mb-1">
                    {t('longitudeLabel')}
                  </label>
                  <input
                    id="prof-lng"
                    type="text"
                    disabled={!editing || saving || !isOnline}
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="e.g. 37.0561"
                    className="w-full px-3.5 py-2 text-sm font-mono tabular-nums rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 disabled:bg-stone-100 dark:disabled:bg-stone-900/50"
                  />
                </div>
              </div>
              <p className="mt-3 text-xs text-stone-600 dark:text-stone-400" role="status" aria-live="polite">
                {coordinatesChanged
                  ? t(gpsStatus === 'detected' ? 'profileGpsCaptured' : 'profileGpsManualUnsaved')
                  : hasSavedCoordinates
                    ? t('profileGpsSaved')
                    : t('profileGpsNotSet')}
              </p>
              {gpsStatusKey && gpsStatus !== 'detecting' && (
                <p className="mt-2 text-xs text-amber-800 dark:text-amber-300" role="status" aria-live="polite">
                  {t(gpsStatusKey)}
                </p>
              )}
            </div>

            <div className="pt-4 border-t border-stone-200 dark:border-stone-800">
              <label className="flex items-start gap-2.5 text-xs text-stone-700 dark:text-stone-300 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={!editing || saving || !isOnline}
                  checked={smsOptIn}
                  onChange={(e) => setSmsOptIn(e.target.checked)}
                  className="mt-0.5 rounded border-stone-300 text-emerald-800"
                />
                <span>{t('smsOptInLabel')}</span>
              </label>
            </div>

            {user?.role === 'farmer' && <section className="pt-5 border-t border-stone-200 dark:border-stone-800 space-y-4" aria-labelledby="notification-preferences-title">
              <div>
                <h2 id="notification-preferences-title" className="text-sm font-semibold text-stone-900 dark:text-stone-100">{t('notificationPreferencesTitle')}</h2>
                <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">{t('notificationPreferencesHelp')}</p>
              </div>
              <div className="rounded-xl border border-stone-200 bg-stone-50 p-4 dark:border-stone-800 dark:bg-stone-900/40">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-3">
                    {pushStatus === 'enabled'
                      ? <Bell className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700 dark:text-emerald-300" aria-hidden="true" />
                      : <BellOff className="mt-0.5 h-5 w-5 shrink-0 text-stone-500" aria-hidden="true" />}
                    <div>
                      <p className="text-sm font-semibold text-stone-900 dark:text-stone-100">{t('pushSettingsTitle')}</p>
                      <p className="mt-1 text-xs text-stone-600 dark:text-stone-400">{t('pushBenefit')}</p>
                      <p className="mt-2 text-xs font-medium text-stone-700 dark:text-stone-300" role="status" aria-live="polite">
                        {t({
                          loading: 'pushStatusLoading',
                          enabled: 'pushStatusEnabled',
                          disabled: 'pushStatusDisabled',
                          unsupported: 'pushStatusUnsupported',
                          denied: 'pushStatusDenied',
                          unconfigured: 'pushStatusUnconfigured',
                          error: 'pushStatusError',
                        }[pushStatus])}
                      </p>
                    </div>
                  </div>
                  {pushStatus === 'enabled' ? (
                    <button
                      type="button"
                      disabled={pushBusy || !isOnline}
                      onClick={() => void handleDisablePush()}
                      className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg border border-stone-300 px-4 py-2 text-xs font-semibold text-stone-700 hover:bg-white disabled:opacity-50 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
                    >
                      {pushBusy ? t('pushWorking') : t('pushDisable')}
                    </button>
                  ) : pushStatus === 'disabled' || pushStatus === 'denied' || pushStatus === 'error' ? (
                    <button
                      type="button"
                      disabled={pushBusy || !isOnline}
                      onClick={() => void handleEnablePush()}
                      className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg bg-emerald-900 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
                    >
                      {pushBusy ? t('pushWorking') : t('pushEnable')}
                    </button>
                  ) : null}
                </div>
                {pushError && <p className="mt-3 text-xs text-red-700 dark:text-red-300" role="alert">{pushError}</p>}
              </div>
              <div className="max-w-full overflow-x-auto">
                <table className="w-full table-fixed text-xs">
                  <thead><tr className="text-left text-stone-500"><th className="w-2/5 break-words py-2 pr-2">{t('notificationCategory')}</th><th className="w-1/5 break-words px-1 py-2">{t('notificationInApp')}</th><th className="w-1/5 break-words px-1 py-2">{t('notificationSms')}</th><th className="w-1/5 break-words px-1 py-2">{t('notificationPush')}</th></tr></thead>
                  <tbody>{notificationCategories.map((category) => (
                    <tr key={category} className="border-t border-stone-100 dark:border-stone-800">
                      <th scope="row" className="break-words py-3 pr-3 text-left font-medium text-stone-800 dark:text-stone-200">{t(`notificationCategory_${category}`)}</th>
                      {(['in_app', 'sms', 'push'] as const).map((channel) => (
                        <td key={channel} className="px-1 py-3"><label className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 cursor-pointer">
                          <input type="checkbox" disabled={!editing || saving || !isOnline || (channel === 'sms' && !smsOptIn) || (channel === 'push' && pushStatus !== 'enabled')} checked={notificationPreferences.categories[category][channel]} onChange={(event) => setNotificationPreferences((current) => ({ ...current, categories: { ...current.categories, [category]: { ...current.categories[category], [channel]: event.target.checked } } }))} className="h-4 w-4 rounded border-stone-300 text-emerald-800 focus:ring-emerald-700" />
                          <span className="sr-only">{t(`notificationCategory_${category}`)} {t(channel === 'in_app' ? 'notificationInApp' : channel === 'sms' ? 'notificationSms' : 'notificationPush')}</span>
                        </label></td>
                      ))}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              <p className="text-[11px] text-stone-500 dark:text-stone-400">{t('notificationSmsMasterHelp')}</p>
              <p className="text-[11px] text-stone-500 dark:text-stone-400">{t('notificationPushMasterHelp')}</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">{t('notificationReminderTiming')}
                  <select disabled={!editing || saving || !isOnline} value={notificationPreferences.reminder_days_before} onChange={(event) => setNotificationPreferences((current) => ({ ...current, reminder_days_before: Number(event.target.value) as 0 | 1 | 2 | 3 }))} className="mt-1.5 w-full rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2">
                    {[0, 1, 2, 3].map((days) => <option key={days} value={days}>{t(`notificationReminder_${days}`)}</option>)}
                  </select>
                </label>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">{t('notificationTimezone')}
                  <input disabled={!editing || saving || !isOnline} value={notificationPreferences.timezone} onChange={(event) => setNotificationPreferences((current) => ({ ...current, timezone: event.target.value }))} maxLength={64} className="mt-1.5 w-full rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2" />
                </label>
              </div>
              <div className="grid gap-4 sm:grid-cols-[1fr_1fr_1fr] items-end">
                <label className="flex items-center gap-2 text-xs font-medium text-stone-700 dark:text-stone-300"><input type="checkbox" disabled={!editing || saving || !isOnline} checked={notificationPreferences.quiet_hours.enabled} onChange={(event) => setNotificationPreferences((current) => ({ ...current, quiet_hours: { ...current.quiet_hours, enabled: event.target.checked } }))} className="rounded border-stone-300 text-emerald-800" />{t('notificationQuietHours')}</label>
                {(['start', 'end'] as const).map((field) => <label key={field} className="block text-xs font-medium text-stone-700 dark:text-stone-300">{t(field === 'start' ? 'notificationQuietStart' : 'notificationQuietEnd')}<input type="time" disabled={!editing || saving || !isOnline || !notificationPreferences.quiet_hours.enabled} value={notificationPreferences.quiet_hours[field]} onChange={(event) => setNotificationPreferences((current) => ({ ...current, quiet_hours: { ...current.quiet_hours, [field]: event.target.value } }))} className="mt-1.5 w-full rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2" /></label>)}
              </div>
              <p className="text-[11px] text-amber-800 dark:text-amber-300">{t('notificationCriticalPolicy')}</p>
            </section>}

            {editing && (
              <div className="pt-4 border-t border-stone-200 dark:border-stone-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  disabled={saving || !isOnline}
                  onClick={() => {
                    syncFormFromResponse(data);
                    setEditing(false);
                  }}
                  className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 rounded-lg cursor-pointer"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={saving || !isOnline}
                  className="px-5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50 cursor-pointer"
                >
                  {saving ? 'Saving to Server...' : t('saveChanges')}
                </button>
              </div>
            )}
          </form>
          {user?.role === 'farmer' && (
            <section className="rounded-xl border border-red-200 dark:border-red-900/70 bg-red-50/60 dark:bg-red-950/20 p-5 sm:p-6" aria-labelledby="delete-account-title">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 id="delete-account-title" className="text-sm font-semibold text-red-900 dark:text-red-200">{t('profileDeleteAccountTitle')}</h2>
                  <p className="mt-1 max-w-xl text-xs leading-relaxed text-red-800 dark:text-red-300">{t('profileDeleteAccountDescription')}</p>
                  {!isOnline && <p className="mt-2 text-xs font-medium text-red-700 dark:text-red-300">{t('profileDeleteAccountOnlineRequired')}</p>}
                </div>
                <button type="button" disabled={!isOnline} onClick={() => setDeleteDialogOpen(true)} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-xs font-semibold text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50">
                  <Trash2 className="h-4 w-4" /> {t('profileDeleteAccountAction')}
                </button>
              </div>
            </section>
          )}
        </div>
      )}
      {deleteDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs" role="dialog" aria-modal="true" aria-labelledby="confirm-delete-account-title">
          <form onSubmit={handleDeleteAccount} className="w-full max-w-md rounded-xl border border-stone-200 bg-white p-6 shadow-xl dark:border-stone-800 dark:bg-[#121A16]">
            <h2 id="confirm-delete-account-title" className="text-base font-bold text-stone-900 dark:text-stone-100">{t('profileDeleteAccountConfirmTitle')}</h2>
            <p className="mt-2 text-sm leading-relaxed text-stone-600 dark:text-stone-400">{t('profileDeleteAccountConfirmDescription')}</p>
            <label htmlFor="delete-account-password" className="mt-5 block text-xs font-medium text-stone-700 dark:text-stone-300">{t('profileDeleteAccountPassword')}</label>
            <input id="delete-account-password" type="password" autoComplete="current-password" required value={deletePassword} onChange={(event) => setDeletePassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm dark:border-stone-700 dark:bg-stone-900" />
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" disabled={deletingAccount} onClick={() => { setDeleteDialogOpen(false); setDeletePassword(''); }} className="rounded-lg bg-stone-100 px-4 py-2 text-xs font-medium text-stone-700 disabled:opacity-50 dark:bg-stone-800 dark:text-stone-300">Cancel</button>
              <button type="submit" disabled={deletingAccount || !deletePassword} className="rounded-lg bg-red-700 px-4 py-2 text-xs font-semibold text-white hover:bg-red-600 disabled:opacity-50">{deletingAccount ? t('profileDeleteAccountSubmitting') : t('profileDeleteAccountConfirm')}</button>
            </div>
          </form>
        </div>
      )}
    </AppShell>
  );
};
