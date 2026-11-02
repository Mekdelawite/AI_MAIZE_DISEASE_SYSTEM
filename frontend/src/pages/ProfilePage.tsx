import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Edit3, MapPin, RefreshCw, WifiOff } from 'lucide-react';
import { ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { profileService } from '../services/profileService';
import { FarmerNotificationPreferences, ProfileResponseData } from '../types/api';

const PROFILE_CACHE_PREFIX = 'maizecare_profile_v1_';
const DEFAULT_NOTIFICATION_PREFERENCES: FarmerNotificationPreferences = {
  categories: {
    crop_activity: { in_app: true, sms: true }, weather_alert: { in_app: true, sms: true },
    soil_water_alert: { in_app: true, sms: true }, agricultural_advisory: { in_app: true, sms: true },
    important_alerts: { in_app: true, sms: true },
  },
  reminder_days_before: 0, quiet_hours: { enabled: false, start: '21:00', end: '07:00' }, timezone: 'Africa/Addis_Ababa',
};
const notificationCategories = ['crop_activity', 'weather_alert', 'soil_water_alert', 'agricultural_advisory', 'important_alerts'] as const;

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
  const { user, refreshUser } = useAuth();

  const [data, setData] = useState<ProfileResponseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);

  // Form fields
  const [fullName, setFullName] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<'en' | 'am'>('en');
  const [region, setRegion] = useState('');
  const [woreda, setWoreda] = useState('');
  const [kebele, setKebele] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [smsOptIn, setSmsOptIn] = useState(false);
  const [notificationPreferences, setNotificationPreferences] = useState<FarmerNotificationPreferences>(DEFAULT_NOTIFICATION_PREFERENCES);

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
    setSmsOptIn(Boolean(fp?.sms_opt_in));
    setNotificationPreferences(fp?.notification_preferences || DEFAULT_NOTIFICATION_PREFERENCES);
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

  const handleUseGps = () => {
    if (!navigator.geolocation) {
      notify(t('profileGpsUnsupported'), 'warning');
      return;
    }
    const hasSavedGpsLocation =
      data?.farmer_profile?.latitude !== undefined &&
      data.farmer_profile.latitude !== null &&
      data?.farmer_profile?.longitude !== undefined &&
      data.farmer_profile.longitude !== null;
    if (hasSavedGpsLocation && !window.confirm(t('profileGpsReplaceConfirm'))) return;

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        notify(t('profileGpsCaptured'), 'info');
      },
      (error) => {
        const message = error.code === 1
          ? t('profileGpsDenied')
          : error.code === 2
            ? t('profileGpsUnavailable')
            : error.code === 3
              ? t('profileGpsTimeout')
              : t('profileGpsError');
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

  return (
    <AppShell
      title={t('navProfile')}
      subtitle="Manage your personal information, regional woreda assignment, GPS coordinates for local weather, and SMS alert preferences."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadProfile}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          {data && !editing && isOnline && (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer"
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
        <div className="max-w-3xl space-y-6">
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
            className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-6"
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
                    className="inline-flex items-center gap-1 text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline cursor-pointer"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>{t('profileCaptureGps')}</span>
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
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="text-left text-stone-500"><th className="py-2 pr-3">{t('notificationCategory')}</th><th className="px-2 py-2">{t('notificationInApp')}</th><th className="px-2 py-2">{t('notificationSms')}</th></tr></thead>
                  <tbody>{notificationCategories.map((category) => (
                    <tr key={category} className="border-t border-stone-100 dark:border-stone-800">
                      <th scope="row" className="py-3 pr-3 text-left font-medium text-stone-800 dark:text-stone-200">{t(`notificationCategory_${category}`)}</th>
                      {(['in_app', 'sms'] as const).map((channel) => (
                        <td key={channel} className="px-2 py-3"><label className="inline-flex items-center gap-2 cursor-pointer">
                          <input type="checkbox" disabled={!editing || saving || !isOnline || (channel === 'sms' && !smsOptIn)} checked={notificationPreferences.categories[category][channel]} onChange={(event) => setNotificationPreferences((current) => ({ ...current, categories: { ...current.categories, [category]: { ...current.categories[category], [channel]: event.target.checked } } }))} className="rounded border-stone-300 text-emerald-800 focus:ring-emerald-700" />
                          <span className="sr-only">{t(`notificationCategory_${category}`)} {t(channel === 'in_app' ? 'notificationInApp' : 'notificationSms')}</span>
                        </label></td>
                      ))}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              <p className="text-[11px] text-stone-500 dark:text-stone-400">{t('notificationSmsMasterHelp')}</p>
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
        </div>
      )}
    </AppShell>
  );
};
