import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle2, Eye, EyeOff, MapPin } from 'lucide-react';
import { PublicLayout } from '../components/layout/PublicLayout';
import { useApp } from '../context/AppContext';
import { authService } from '../services/authService';

const ETHIOPIAN_REGIONS = [
  'Oromia',
  'Amhara',
  'SNNPR',
  'Sidama',
  'South West Ethiopia',
  'Tigray',
  'Benishangul-Gumuz',
  'Gambela',
  'Somali',
  'Afar',
  'Harari',
  'Dire Dawa',
  'Addis Ababa',
];

export const RegisterPage: React.FC = () => {
  const { t, language, notify } = useApp();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [region, setRegion] = useState('Oromia');
  const [woreda, setWoreda] = useState('');
  const [kebele, setKebele] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<'en' | 'am'>(language);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [smsOptIn, setSmsOptIn] = useState(true);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      notify('Geolocation is not supported by your browser.', 'warning');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        notify('Coordinates captured from device GPS.', 'info');
      },
      () => {
        notify('Unable to read device GPS coordinates. You may enter them manually.', 'warning');
      }
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!fullName.trim()) {
      setErrorMessage('Full name is required.');
      return;
    }
    if (!phoneNumber.trim()) {
      setErrorMessage('Phone number is required.');
      return;
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters.');
      return;
    }
    if (!region.trim() || !woreda.trim()) {
      setErrorMessage('Region and Woreda are required.');
      return;
    }

    const parsedLat = latitude.trim() ? Number(latitude) : undefined;
    const parsedLng = longitude.trim() ? Number(longitude) : undefined;

    if (parsedLat !== undefined && (Number.isNaN(parsedLat) || parsedLat < -90 || parsedLat > 90)) {
      setErrorMessage('Latitude must be a valid coordinate between -90 and 90.');
      return;
    }
    if (parsedLng !== undefined && (Number.isNaN(parsedLng) || parsedLng < -180 || parsedLng > 180)) {
      setErrorMessage('Longitude must be a valid coordinate between -180 and 180.');
      return;
    }

    setLoading(true);
    try {
      await authService.register({
        full_name: fullName,
        phone_number: phoneNumber,
        password,
        region,
        woreda,
        kebele: kebele.trim() || undefined,
        preferred_language: preferredLanguage,
        latitude: parsedLat,
        longitude: parsedLng,
        sms_opt_in: smsOptIn,
      });

      setSuccessMessage('Farmer account registered on the server. Redirecting to sign in...');
      notify('Farmer account registered. Please sign in.', 'success');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Registration failed on server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PublicLayout>
      <div className="max-w-xl mx-auto px-6 py-12">
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
          <h1 className="text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
            {t('registerTitle')}
          </h1>
          <p className="mt-1.5 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
            {t('registerSubtitle')}
          </p>

          {errorMessage && (
            <div
              className="mt-4 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 p-3.5 flex items-start gap-2.5 text-xs text-red-800 dark:text-red-200"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>{errorMessage}</div>
            </div>
          )}

          {successMessage && (
            <div
              className="mt-4 rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 p-3.5 flex items-start gap-2.5 text-xs text-emerald-900 dark:text-emerald-200"
              role="status"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <div>{successMessage}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="reg-fullname" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('fullNameLabel')} *
                </label>
                <input
                  id="reg-fullname"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Abebe Kebede"
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div>
                <label htmlFor="reg-phone" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('phoneLabel')} *
                </label>
                <input
                  id="reg-phone"
                  type="tel"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder={t('phonePlaceholder')}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="reg-password" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('passwordLabel')} *
                </label>
                <div className="relative">
                  <input
                    id="reg-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 6 characters"
                    className="w-full px-3.5 py-2 pr-10 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 cursor-pointer"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="reg-lang" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('preferredLangLabel')}
                </label>
                <select
                  id="reg-lang"
                  value={preferredLanguage}
                  onChange={(e) => setPreferredLanguage(e.target.value as 'en' | 'am')}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                >
                  <option value="en">English (en)</option>
                  <option value="am">አማርኛ / Amharic (am)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="reg-region" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('regionLabel')} *
                </label>
                <select
                  id="reg-region"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                >
                  {ETHIOPIAN_REGIONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="reg-woreda" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('woredaLabel')} *
                </label>
                <input
                  id="reg-woreda"
                  type="text"
                  required
                  value={woreda}
                  onChange={(e) => setWoreda(e.target.value)}
                  placeholder="e.g. Bako Tibe"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div>
                <label htmlFor="reg-kebele" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('kebeleLabel')}
                </label>
                <input
                  id="reg-kebele"
                  type="text"
                  value={kebele}
                  onChange={(e) => setKebele(e.target.value)}
                  placeholder="Optional"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>
            </div>

            <div className="pt-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-stone-700 dark:text-stone-300">
                  Farm Coordinates (Optional — used for local weather)
                </span>
                <button
                  type="button"
                  onClick={handleDetectLocation}
                  className="inline-flex items-center gap-1 text-xs text-emerald-800 dark:text-emerald-400 hover:underline cursor-pointer"
                >
                  <MapPin className="w-3.5 h-3.5" />
                  <span>Use Device GPS</span>
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="reg-lat" className="sr-only">
                    {t('latitudeLabel')}
                  </label>
                  <input
                    id="reg-lat"
                    type="text"
                    inputMode="decimal"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="Latitude (e.g. 9.1245)"
                    className="w-full px-3.5 py-2 text-sm font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label htmlFor="reg-lng" className="sr-only">
                    {t('longitudeLabel')}
                  </label>
                  <input
                    id="reg-lng"
                    type="text"
                    inputMode="decimal"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="Longitude (e.g. 37.0561)"
                    className="w-full px-3.5 py-2 text-sm font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>
            </div>

            <div className="pt-1">
              <label className="flex items-start gap-2.5 text-xs text-stone-700 dark:text-stone-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={smsOptIn}
                  onChange={(e) => setSmsOptIn(e.target.checked)}
                  className="mt-0.5 rounded border-stone-300 text-emerald-800 focus:ring-emerald-700"
                />
                <span>{t('smsOptInLabel')}</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
            >
              {loading ? 'Creating Farmer Account...' : t('register')}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-stone-200 dark:border-stone-800 text-center text-xs text-stone-600 dark:text-stone-400">
            <span>{t('haveAccountPrompt')} </span>
            <Link to="/login" className="font-semibold text-emerald-800 dark:text-emerald-400 hover:underline">
              {t('signIn')}
            </Link>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};
