
import React, { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  MapPin,
  ShieldCheck,
} from 'lucide-react';

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

const OTP_LENGTH = 6;

export const RegisterPage: React.FC = () => {
  const { t, language, notify } = useApp();
  const navigate = useNavigate();

  // Registration form fields
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [region, setRegion] = useState('Oromia');
  const [woreda, setWoreda] = useState('');
  const [kebele, setKebele] = useState('');
  const [preferredLanguage, setPreferredLanguage] =
    useState<'en' | 'am'>(language);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [smsOptIn, setSmsOptIn] = useState(true);

  // OTP flow
  const [showVerificationScreen, setShowVerificationScreen] =
    useState(false);
  const [otp, setOtp] = useState('');
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  // Feedback
  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);
  const [successMessage, setSuccessMessage] =
    useState<string | null>(null);

  // Request guards and verification snapshot
  const otpRequestRef = useRef(false);
  const otpVerifyRef = useRef(false);
  const registrationRef = useRef(false);
  const phoneSnapshotRef = useRef('');
  const otpAttemptRef = useRef(0);

  const handlePhoneChange = (value: string) => {
    if (value.trim() !== phoneNumber.trim()) {
      otpAttemptRef.current += 1;
      phoneSnapshotRef.current = '';

      setOtp('');
      setPhoneVerified(false);
      setShowVerificationScreen(false);
    }

    setPhoneNumber(value);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      notify(
        'Geolocation is not supported by your browser.',
        'warning',
      );
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));

        notify('Coordinates captured from device GPS.', 'info');
      },
      () => {
        notify(
          'Unable to read device GPS coordinates. You may enter them manually.',
          'warning',
        );
      },
    );
  };

  const validateForm = (): boolean => {
    if (!fullName.trim()) {
      setErrorMessage('Full name is required.');
      return false;
    }

    if (!phoneNumber.trim()) {
      setErrorMessage('Phone number is required.');
      return false;
    }

    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters.');
      return false;
    }

    if (!region.trim() || !woreda.trim()) {
      setErrorMessage('Region and Woreda are required.');
      return false;
    }

    const parsedLat = latitude.trim()
      ? Number(latitude)
      : undefined;

    const parsedLng = longitude.trim()
      ? Number(longitude)
      : undefined;

    if (
      parsedLat !== undefined &&
      (!Number.isFinite(parsedLat) ||
        parsedLat < -90 ||
        parsedLat > 90)
    ) {
      setErrorMessage('Latitude must be between -90 and 90.');
      return false;
    }

    if (
      parsedLng !== undefined &&
      (!Number.isFinite(parsedLng) ||
        parsedLng < -180 ||
        parsedLng > 180)
    ) {
      setErrorMessage('Longitude must be between -180 and 180.');
      return false;
    }

    if (
      (parsedLat === undefined) !==
      (parsedLng === undefined)
    ) {
      setErrorMessage(
        'Enter both latitude and longitude, or leave both empty.',
      );
      return false;
    }

    return true;
  };

  // STEP 1: Request the OTP and show only the verification screen.
  const handleRequestOTP = async () => {
    if (
      otpRequestRef.current ||
      otpVerifyRef.current ||
      registrationRef.current
    ) {
      return;
    }

    const phone = phoneNumber.trim();

    if (!phone) {
      setErrorMessage('Phone number is required.');
      return;
    }

    otpRequestRef.current = true;
    setOtpLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await authService.requestRegistrationOTP(phone);

      phoneSnapshotRef.current = phone;
      setOtp('');
      setPhoneVerified(false);
      setShowVerificationScreen(true);

      setSuccessMessage(
        'Verification code sent. Check your SMS messages.',
      );

      notify(
        'Verification code sent. Check your SMS messages.',
        'success',
      );
    } catch (err: any) {
      setErrorMessage(
        err?.message ||
          'Could not send verification code. Please try again.',
      );
    } finally {
      otpRequestRef.current = false;
      setOtpLoading(false);
    }
  };

  // STEP 3: Create the account using the verified phone number.
  // The explicit verifiedPhone argument avoids stale React state.
  const createAccount = async (verifiedPhone: string) => {
    if (registrationRef.current) return;

    if (
      !verifiedPhone ||
      verifiedPhone !== phoneSnapshotRef.current ||
      verifiedPhone !== phoneNumber.trim()
    ) {
      setErrorMessage(
        'Phone verification no longer matches this number. Please request a new code.',
      );
      return;
    }

    registrationRef.current = true;
    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage('Phone verified. Creating your account...');

    try {
      const parsedLat = latitude.trim()
        ? Number(latitude)
        : undefined;

      const parsedLng = longitude.trim()
        ? Number(longitude)
        : undefined;

      const result = await authService.register({
        full_name: fullName.trim(),
        phone_number: verifiedPhone,
        password,
        region: region.trim(),
        woreda: woreda.trim(),
        kebele: kebele.trim() || undefined,
        preferred_language: preferredLanguage,
        latitude: parsedLat,
        longitude: parsedLng,
        sms_opt_in: smsOptIn,
      });

      if (result?.success === false || result?.error) {
        throw new Error(
          result?.message ||
            result?.error ||
            'The server could not create your account.',
        );
      }

      setPhoneVerified(true);
      setSuccessMessage(
        'Registration successful! Your account has been created. Redirecting to login...',
      );

      notify(
        'Registration successful! You can now log in.',
        'success',
      );

      window.setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
    } catch (err: any) {
      setErrorMessage(
        err?.message ||
          'Phone verification succeeded, but account creation failed.',
      );
      setSuccessMessage(null);
    } finally {
      registrationRef.current = false;
      setLoading(false);
    }
  };

  // STEP 2: Verify OTP. Account creation starts immediately after
  // the backend confirms verification.
  const handleVerifyOTP = async (code: string) => {
    if (
      otpVerifyRef.current ||
      registrationRef.current ||
      code.length !== OTP_LENGTH
    ) {
      return;
    }

    const verifiedPhone = phoneSnapshotRef.current;

    if (
      !verifiedPhone ||
      verifiedPhone !== phoneNumber.trim()
    ) {
      setErrorMessage(
        'Phone number changed. Please request a new verification code.',
      );
      return;
    }

    otpVerifyRef.current = true;
    const currentAttempt = ++otpAttemptRef.current;

    setOtpLoading(true);
    setErrorMessage(null);
    setSuccessMessage('Verifying your phone number...');

    let verificationSucceeded = false;

    try {
      const result =
        await authService.verifyRegistrationOTP(
          verifiedPhone,
          code,
        );

      if (currentAttempt !== otpAttemptRef.current) {
        return;
      }

      const data =
        result?.data?.data ??
        result?.data ??
        result;

      // Accept only an explicit successful verification response.
      const verified =
        data?.verified === true ||
        data?.phone_verified === true;

      if (!verified) {
        throw new Error(
          data?.message ||
            'The server did not confirm phone verification.',
        );
      }

      verificationSucceeded = true;
      setPhoneVerified(true);
      setSuccessMessage(
        'Phone verified successfully! Creating your account...',
      );

      notify('Phone number verified successfully.', 'success');
    } catch (err: any) {
      if (currentAttempt === otpAttemptRef.current) {
        setErrorMessage(
          err?.message ||
            'Invalid or expired verification code. Please try again.',
        );
        setSuccessMessage(null);
      }
    } finally {
      otpVerifyRef.current = false;
      setOtpLoading(false);
    }

    // IMPORTANT:
    // Do this after the verification request finishes, without relying
    // on the asynchronous phoneVerified state update.
    if (
      verificationSucceeded &&
      currentAttempt === otpAttemptRef.current
    ) {
      await createAccount(verifiedPhone);
    }
  };

  const handleOTPChange = (value: string) => {
    const code = value.replace(/\D/g, '').slice(0, OTP_LENGTH);

    setOtp(code);
    setErrorMessage(null);
    setSuccessMessage(null);

    if (code.length === OTP_LENGTH) {
      void handleVerifyOTP(code);
    }
  };

  // FIRST submission sends the OTP; it does not create an account.
  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>,
  ) => {
    e.preventDefault();

    if (loading || otpLoading) return;

    setErrorMessage(null);
    setSuccessMessage(null);

    if (!validateForm()) return;

    await handleRequestOTP();
  };

  const handleBackToRegistration = () => {
    if (otpLoading || loading) return;

    otpAttemptRef.current += 1;
    phoneSnapshotRef.current = '';

    setOtp('');
    setPhoneVerified(false);
    setShowVerificationScreen(false);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  return (
    <PublicLayout>
      <div className="max-w-xl mx-auto px-6 py-12">
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
          <h1 className="text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
            {showVerificationScreen
              ? 'Verify Your Phone'
              : t('registerTitle')}
          </h1>

          <p className="mt-1.5 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
            {showVerificationScreen
              ? 'One final step to create your farmer account.'
              : t('registerSubtitle')}
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

          {!showVerificationScreen ? (
            <form
              onSubmit={handleSubmit}
              className="mt-6 space-y-4"
              noValidate
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="reg-fullname"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('fullNameLabel')} *
                  </label>

                  <input
                    id="reg-fullname"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Abebe Kebede"
                    autoComplete="name"
                    disabled={otpLoading || loading}
                    className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-phone"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('phoneLabel')} *
                  </label>

                  <input
                    id="reg-phone"
                    type="tel"
                    required
                    value={phoneNumber}
                    onChange={(e) =>
                      handlePhoneChange(e.target.value)
                    }
                    placeholder={t('phonePlaceholder')}
                    autoComplete="tel"
                    disabled={otpLoading || loading}
                    className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="reg-password"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('passwordLabel')} *
                  </label>

                  <div className="relative">
                    <input
                      id="reg-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      autoComplete="new-password"
                      disabled={otpLoading || loading}
                      className="w-full px-3.5 py-2 pr-10 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                    />

                    <button
                      type="button"
                      onClick={() =>
                        setShowPassword((p) => !p)
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 cursor-pointer"
                      aria-label={
                        showPassword
                          ? 'Hide password'
                          : 'Show password'
                      }
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="reg-lang"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('preferredLangLabel')}
                  </label>

                  <select
                    id="reg-lang"
                    value={preferredLanguage}
                    onChange={(e) =>
                      setPreferredLanguage(
                        e.target.value as 'en' | 'am',
                      )
                    }
                    disabled={otpLoading || loading}
                    className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  >
                    <option value="en">English (en)</option>
                    <option value="am">አማርኛ / Amharic (am)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label
                    htmlFor="reg-region"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('regionLabel')} *
                  </label>

                  <select
                    id="reg-region"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    disabled={otpLoading || loading}
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
                  <label
                    htmlFor="reg-woreda"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('woredaLabel')} *
                  </label>

                  <input
                    id="reg-woreda"
                    type="text"
                    required
                    value={woreda}
                    onChange={(e) => setWoreda(e.target.value)}
                    placeholder="e.g. Bako Tibe"
                    disabled={otpLoading || loading}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-kebele"
                    className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                  >
                    {t('kebeleLabel')}
                  </label>

                  <input
                    id="reg-kebele"
                    type="text"
                    value={kebele}
                    onChange={(e) => setKebele(e.target.value)}
                    placeholder="Optional"
                    disabled={otpLoading || loading}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="pt-2">
                <div className="flex items-center justify-between mb-1.5 gap-3">
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
                      disabled={otpLoading || loading}
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
                      disabled={otpLoading || loading}
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
                    disabled={otpLoading || loading}
                    className="mt-0.5 rounded border-stone-300 text-emerald-800 focus:ring-emerald-700"
                  />

                  <span>{t('smsOptInLabel')}</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={otpLoading || loading}
                className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {otpLoading
                  ? 'Sending verification code...'
                  : t('register')}
              </button>
            </form>
          ) : (
            <div className="mt-6 space-y-5">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950">
                  <ShieldCheck className="h-7 w-7 text-emerald-700 dark:text-emerald-400" />
                </div>

                <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100">
                  Verify your phone number
                </h2>

                <p className="mt-2 text-sm text-stone-600 dark:text-stone-400">
                  We sent a verification code to{' '}
                  <strong>{phoneSnapshotRef.current}</strong>.
                  Enter the six-digit code to create your account.
                </p>
              </div>

              <div>
                <label
                  htmlFor="registration-otp"
                  className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-2"
                >
                  SMS verification code
                </label>

                <input
                  id="registration-otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={OTP_LENGTH}
                  value={otp}
                  onChange={(e) => handleOTPChange(e.target.value)}
                  placeholder="Enter 6-digit code"
                  autoFocus
                  disabled={otpLoading || loading}
                  className="w-full rounded-lg border border-stone-300 bg-white px-4 py-4 text-center text-2xl font-semibold tracking-[0.5em] dark:border-stone-700 dark:bg-stone-900 disabled:opacity-60"
                />
              </div>

              {(otpLoading || loading) && (
                <div className="flex items-center justify-center gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                  <span className="animate-spin rounded-full h-4 w-4 border-2 border-emerald-700 border-t-transparent" />
                  {loading
                    ? 'Creating your farmer account...'
                    : 'Verifying your code...'}
                </div>
              )}

              <button
                type="button"
                onClick={handleRequestOTP}
                disabled={otpLoading || loading}
                className="w-full rounded-lg border border-stone-300 px-4 py-2.5 text-sm font-semibold text-stone-700 hover:bg-stone-50 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-900 disabled:opacity-50"
              >
                Resend verification code
              </button>

              <button
                type="button"
                onClick={handleBackToRegistration}
                disabled={otpLoading || loading}
                className="w-full text-sm text-stone-600 hover:underline dark:text-stone-400 disabled:opacity-50"
              >
                Back to registration
              </button>
            </div>
          )}

          <div className="mt-6 pt-5 border-t border-stone-200 dark:border-stone-800 text-center text-xs text-stone-600 dark:text-stone-400">
            <span>{t('haveAccountPrompt')} </span>

            <Link
              to="/login"
              className="font-semibold text-emerald-800 dark:text-emerald-400 hover:underline"
            >
              {t('signIn')}
            </Link>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};
