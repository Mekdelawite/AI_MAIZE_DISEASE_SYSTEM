import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { PublicLayout } from '../components/layout/PublicLayout';
import { useApp } from '../context/AppContext';
import { authService } from '../services/authService';

export const ExtensionAgentActivationPage: React.FC = () => {
  const { notify } = useApp();
  const navigate = useNavigate();
  const [contact, setContact] = useState('');
  const [code, setCode] = useState('');
  const [activationToken, setActivationToken] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleVerifyCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setLoading(true);
    try {
      const result = await authService.verifyExtensionAgentActivation(contact, code);
      setActivationToken(result.activation_token);
      setSuccessMessage('Contact verified. Choose a password to activate your account.');
    } catch (cause: unknown) {
      setErrorMessage(cause instanceof Error ? cause.message : 'Activation code verification failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    if (!activationToken) {
      setErrorMessage('Verify your activation code before setting a password.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('The passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const result = await authService.completeExtensionAgentActivation(activationToken, password);
      setActivationToken(null);
      setPassword('');
      setConfirmPassword('');
      setSuccessMessage(result?.message || 'Account activated. You can now sign in.');
      notify('Extension-agent account activated.', 'success');
      window.setTimeout(() => navigate('/login', { replace: true }), 1200);
    } catch (cause: unknown) {
      setErrorMessage(cause instanceof Error ? cause.message : 'Could not activate the account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PublicLayout>
      <div className="max-w-md mx-auto px-6 py-12 sm:py-16">
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
          <h1 className="text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
            Activate Extension Agent Account
          </h1>
          <p className="mt-2 text-xs leading-relaxed text-stone-600 dark:text-stone-400">
            Enter the email address or phone number registered by your agricultural office and the code sent by the administrator.
          </p>

          {errorMessage && (
            <div className="mt-4 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 p-3.5 flex items-start gap-2.5 text-xs text-red-800 dark:text-red-200" role="alert">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>{errorMessage}</div>
            </div>
          )}
          {successMessage && (
            <div className="mt-4 rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 p-3.5 flex items-start gap-2.5 text-xs text-emerald-900 dark:text-emerald-200" role="status">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <div>{successMessage}</div>
            </div>
          )}

          {!activationToken ? (
            <form onSubmit={handleVerifyCode} className="mt-6 space-y-4">
              <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                Registered email or phone number
                <input
                  type="text"
                  required
                  autoComplete="email"
                  value={contact}
                  onChange={(event) => setContact(event.target.value)}
                  className="mt-1 w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </label>
              <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                One-time activation code
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="mt-1 w-full px-3.5 py-2.5 text-sm font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </label>
              <button type="submit" disabled={loading} className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50">
                {loading ? 'Verifying code...' : 'Verify code'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSetPassword} className="mt-6 space-y-4">
              <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                Create password
                <input
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="mt-1 w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </label>
              <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                Confirm password
                <input
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  className="mt-1 w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </label>
              <button type="submit" disabled={loading} className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50">
                {loading ? 'Activating account...' : 'Create password and activate'}
              </button>
            </form>
          )}

          <div className="mt-6 pt-5 border-t border-stone-200 dark:border-stone-800 text-center text-xs text-stone-600 dark:text-stone-400">
            <Link to="/login" className="font-semibold text-emerald-800 dark:text-emerald-400 hover:underline">
              Return to sign in
            </Link>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};
