import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, Eye, EyeOff, Layout, Server } from 'lucide-react';
import { PublicLayout } from '../components/layout/PublicLayout';
import { getDefaultHomeForRole } from '../components/layout/ProtectedRoute';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { t, notify, apiBaseUrl, updateApiBaseUrl } = useApp();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [customApiUrl, setCustomApiUrl] = useState(apiBaseUrl);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!phoneNumber.trim()) {
      setErrorMessage('Please enter your registered phone number.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setLoading(true);
    try {
      const user = await login({ phone_number: phoneNumber.trim(), password });
      notify(`Signed in as ${user.full_name || user.phone_number || user.role}`, 'success');
      const fromPath = (location.state as any)?.from?.pathname;
      if (fromPath && fromPath !== '/login') {
        navigate(fromPath, { replace: true });
      } else {
        navigate(getDefaultHomeForRole(user.role), { replace: true });
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Sign in failed. Please check your credentials and server connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PublicLayout>
      <div className="max-w-md mx-auto px-6 py-12 sm:py-16">
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
          <h1 className="text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
            {t('loginTitle')}
          </h1>
          <p className="mt-1.5 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
            {t('loginSubtitle')}
          </p>

          {errorMessage && (
            <div
              className="mt-4 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 p-3.5 flex items-start gap-2.5 text-xs text-red-800 dark:text-red-200"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1">{errorMessage}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
            <div>
              <label
                htmlFor="login-phone"
                className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
              >
                {t('phoneLabel')}
              </label>
              <input
                id="login-phone"
                type="tel"
                autoComplete="tel"
                required
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder={t('phonePlaceholder')}
                className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 focus:outline-none focus:ring-2 focus:ring-emerald-700"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="login-password"
                  className="block text-xs font-medium text-stone-700 dark:text-stone-300"
                >
                  {t('passwordLabel')}
                </label>
                <Link
                  to="/recover-password"
                  className="text-xs text-emerald-800 dark:text-emerald-400 hover:underline"
                >
                  {t('forgotPasswordLink')}
                </Link>
              </div>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t('passwordPlaceholder')}
                  className="w-full px-3.5 py-2.5 pr-10 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 focus:outline-none focus:ring-2 focus:ring-emerald-700"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-800 dark:hover:text-stone-200 cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
            >
              {loading ? 'Signing in...' : t('signIn')}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-stone-200 dark:border-stone-800 text-center text-xs text-stone-600 dark:text-stone-400">
            <span>{t('noAccountPrompt')} </span>
            <Link
              to="/register"
              className="font-semibold text-emerald-800 dark:text-emerald-400 hover:underline"
            >
              {t('register')}
            </Link>
          </div>
        </div>

        {/* Backend Endpoint Configuration & Academic Route Inspector */}
        <div className="mt-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 text-xs space-y-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-stone-700 dark:text-stone-300 font-medium">
              <Server className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
              <span>Flask API:</span>
              <code className="font-mono text-stone-900 dark:text-stone-100">{apiBaseUrl}</code>
            </div>
            <button
              type="button"
              onClick={() => {
                setCustomApiUrl(apiBaseUrl);
                setShowApiConfig((prev) => !prev);
              }}
              className="text-emerald-800 dark:text-emerald-400 hover:underline cursor-pointer whitespace-nowrap"
            >
              {showApiConfig ? 'Close' : 'Change URL'}
            </button>
          </div>

          {showApiConfig && (
            <div className="flex items-center gap-2 pt-2">
              <input
                type="url"
                value={customApiUrl}
                onChange={(e) => setCustomApiUrl(e.target.value)}
                placeholder="http://127.0.0.1:5000"
                className="flex-1 px-2.5 py-1.5 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
              />
              <button
                type="button"
                onClick={() => {
                  updateApiBaseUrl(customApiUrl);
                  setShowApiConfig(false);
                  notify(`Flask API URL set to ${customApiUrl || 'http://127.0.0.1:5000'}`, 'info');
                }}
                className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-800 rounded-lg cursor-pointer"
              >
                Save
              </button>
            </div>
          )}

          <div className="pt-3 border-t border-stone-200/70 dark:border-stone-800">
            <div className="flex items-center gap-2 text-stone-700 dark:text-stone-300 font-medium mb-1">
              <Layout className="w-4 h-4 text-amber-600" />
              <span>Workspace Login Shortcuts</span>
            </div>
            <p className="text-stone-500 dark:text-stone-400 leading-relaxed mb-3">
              Choose a workspace below. You must sign in with an account authorized for that workspace before continuing.
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
              onClick={() => navigate('/farmer/dashboard')}
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors cursor-pointer whitespace-nowrap"
              >
                Farmer UI
              </button>
              <button
                type="button"
                onClick={() => navigate('/extension/dashboard')}
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors cursor-pointer whitespace-nowrap"
              >
                Extension UI
              </button>
              <button
                type="button"
                onClick={() => navigate('/admin/dashboard')}
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors cursor-pointer whitespace-nowrap"
              >
                Admin UI
              </button>
            </div>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};
