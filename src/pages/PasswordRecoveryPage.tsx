import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { PublicLayout } from '../components/layout/PublicLayout';
import { useApp } from '../context/AppContext';
import { authService } from '../services/authService';

export const PasswordRecoveryPage: React.FC = () => {
  const { t, notify } = useApp();
  const navigate = useNavigate();

  const [step, setStep] = useState<'request' | 'confirm'>('request');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [serverFeedback, setServerFeedback] = useState<string | null>(null);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setServerFeedback(null);

    if (!phoneNumber.trim()) {
      setErrorMessage('Please enter your registered phone number.');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.requestPasswordReset(phoneNumber);
      setServerFeedback(
        res?.message || 'Server accepted password reset request. Enter the OTP received via SMS below.'
      );
      setStep('confirm');
    } catch (err: any) {
      setErrorMessage(err?.message || 'Password reset OTP request failed on server.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setServerFeedback(null);

    if (!phoneNumber.trim() || !otp.trim() || !newPassword) {
      setErrorMessage('Phone number, OTP, and new password are required.');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.confirmPasswordReset({
        phone_number: phoneNumber,
        otp,
        new_password: newPassword,
      });
      setServerFeedback(res?.message || 'Password updated on server. Redirecting to sign in...');
      notify('Password reset confirmed by server.', 'success');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to confirm password reset.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PublicLayout>
      <div className="max-w-md mx-auto px-6 py-12 sm:py-16">
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
          <h1 className="text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
            {t('recoveryTitle')}
          </h1>
          <p className="mt-1.5 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
            {t('recoverySubtitle')}
          </p>

          <div className="mt-4 flex items-center gap-1 p-1 rounded-lg bg-stone-100 dark:bg-stone-800">
            <button
              type="button"
              onClick={() => setStep('request')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                step === 'request'
                  ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                  : 'text-stone-600 dark:text-stone-400'
              }`}
            >
              1. Request OTP
            </button>
            <button
              type="button"
              onClick={() => setStep('confirm')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                step === 'confirm'
                  ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                  : 'text-stone-600 dark:text-stone-400'
              }`}
            >
              2. Confirm OTP
            </button>
          </div>

          {errorMessage && (
            <div
              className="mt-4 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 p-3.5 flex items-start gap-2.5 text-xs text-red-800 dark:text-red-200"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>{errorMessage}</div>
            </div>
          )}

          {serverFeedback && (
            <div
              className="mt-4 rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 p-3.5 flex items-start gap-2.5 text-xs text-emerald-900 dark:text-emerald-200"
              role="status"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <div>{serverFeedback}</div>
            </div>
          )}

          {step === 'request' ? (
            <form onSubmit={handleRequestOtp} className="mt-6 space-y-4">
              <div>
                <label htmlFor="rec-phone" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('phoneLabel')}
                </label>
                <input
                  id="rec-phone"
                  type="tel"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder={t('phonePlaceholder')}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {loading ? 'Requesting OTP...' : t('requestOtpBtn')}
              </button>
            </form>
          ) : (
            <form onSubmit={handleConfirmReset} className="mt-6 space-y-4">
              <div>
                <label htmlFor="conf-phone" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('phoneLabel')}
                </label>
                <input
                  id="conf-phone"
                  type="tel"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder={t('phonePlaceholder')}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div>
                <label htmlFor="conf-otp" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('otpLabel')}
                </label>
                <input
                  id="conf-otp"
                  type="text"
                  required
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="Enter SMS code"
                  className="w-full px-3.5 py-2.5 text-sm font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div>
                <label htmlFor="conf-newpass" className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5">
                  {t('newPasswordLabel')}
                </label>
                <input
                  id="conf-newpass"
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
              >
                {loading ? 'Updating Password...' : t('confirmResetBtn')}
              </button>
            </form>
          )}

          <div className="mt-6 pt-5 border-t border-stone-200 dark:border-stone-800 text-center text-xs text-stone-600 dark:text-stone-400">
            <Link to="/login" className="font-semibold text-emerald-800 dark:text-emerald-400 hover:underline">
              {t('back')} to {t('signIn')}
            </Link>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};
