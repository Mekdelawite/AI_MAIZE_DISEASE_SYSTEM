import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, RefreshCw, Server, X, XCircle } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const LoadingSkeleton: React.FC<{ rows?: number; className?: string }> = ({
  rows = 4,
  className = '',
}) => {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-live="polite" aria-label="Loading content">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-14 w-full rounded-lg bg-stone-200/70 dark:bg-stone-800/60 animate-pulse border border-stone-200/50 dark:border-stone-800"
        />
      ))}
    </div>
  );
};

export const EmptyState: React.FC<{
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}> = ({ title, description, actionLabel, onAction }) => {
  return (
    <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-8 text-center">
      <h3 className="text-base font-semibold text-stone-900 dark:text-stone-100">{title}</h3>
      <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400 max-w-md mx-auto leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-5">
          <button
            type="button"
            onClick={onAction}
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-medium text-white bg-emerald-800 hover:bg-emerald-700 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {actionLabel}
          </button>
        </div>
      )}
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message: string;
  onRetry?: () => void;
  isNetworkError?: boolean;
}> = ({ title = 'Unable to load data from server', message, onRetry }) => {
  const { apiBaseUrl, updateApiBaseUrl, notify } = useApp();
  const [editingUrl, setEditingUrl] = useState(false);
  const [customUrl, setCustomUrl] = useState(apiBaseUrl);

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    updateApiBaseUrl(customUrl);
    setEditingUrl(false);
    notify(`API Base URL updated to ${customUrl || 'http://127.0.0.1:5000'}`, 'info');
    if (onRetry) onRetry();
  };

  return (
    <div
      className="rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50/60 dark:bg-red-950/20 p-6"
      role="alert"
    >
      <div className="flex items-start gap-3.5">
        <AlertTriangle className="w-5 h-5 text-red-700 dark:text-red-400 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-red-900 dark:text-red-200">{title}</h3>
          <p className="mt-1 text-sm text-red-800 dark:text-red-300 leading-relaxed">{message}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-stone-600 dark:text-stone-400">
            <span>Target Flask API:</span>
            <code className="font-mono text-stone-800 dark:text-stone-200">{apiBaseUrl}</code>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-white bg-red-800 hover:bg-red-700 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Request</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setCustomUrl(apiBaseUrl);
                setEditingUrl((prev) => !prev);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 hover:bg-stone-50 dark:hover:bg-stone-800 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Server className="w-3.5 h-3.5" />
              <span>Configure API Endpoint</span>
            </button>
          </div>

          {editingUrl && (
            <form onSubmit={handleSaveUrl} className="mt-4 pt-4 border-t border-red-200/70 dark:border-red-900/50 flex flex-wrap items-center gap-2">
              <label htmlFor="api-base-url-input" className="sr-only">
                Flask Backend Base URL
              </label>
              <input
                id="api-base-url-input"
                type="url"
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                placeholder="http://127.0.0.1:5000"
                className="flex-1 min-w-[240px] px-3 py-1.5 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100"
              />
              <button
                type="submit"
                className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-800 hover:bg-emerald-700 rounded-lg whitespace-nowrap shrink-0 cursor-pointer"
              >
                Apply URL
              </button>
              <button
                type="button"
                onClick={() => {
                  updateApiBaseUrl(null);
                  setEditingUrl(false);
                  if (onRetry) onRetry();
                }}
                className="px-3 py-1.5 text-xs font-medium text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-100 whitespace-nowrap shrink-0 cursor-pointer"
              >
                Reset Default
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export const ConfirmDialog: React.FC<{
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'primary';
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'primary',
  loading = false,
  onConfirm,
  onCancel,
}) => {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="w-full max-w-md rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 shadow-xl">
        <h3 id="confirm-dialog-title" className="text-base font-semibold text-stone-900 dark:text-stone-100">
          {title}
        </h3>
        <p className="mt-2 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">{description}</p>
        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            disabled={loading}
            onClick={onCancel}
            className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 hover:bg-stone-200 dark:hover:bg-stone-700 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={onConfirm}
            className={`px-4 py-2 text-xs font-medium text-white rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50 ${
              variant === 'danger'
                ? 'bg-red-700 hover:bg-red-600'
                : 'bg-emerald-800 hover:bg-emerald-700'
            }`}
          >
            {loading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export const ToastContainer: React.FC = () => {
  const { toasts, dismissToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const Icon =
          toast.variant === 'success'
            ? CheckCircle2
            : toast.variant === 'error'
            ? XCircle
            : toast.variant === 'warning'
            ? AlertTriangle
            : Info;

        const colorClasses =
          toast.variant === 'success'
            ? 'border-emerald-300 dark:border-emerald-800 bg-emerald-950 text-emerald-50'
            : toast.variant === 'error'
            ? 'border-red-300 dark:border-red-800 bg-red-950 text-red-50'
            : toast.variant === 'warning'
            ? 'border-amber-300 dark:border-amber-800 bg-amber-950 text-amber-50'
            : 'border-stone-300 dark:border-stone-700 bg-stone-900 text-stone-100';

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${colorClasses}`}
          >
            <Icon className="w-4 h-4 shrink-0 mt-0.5" />
            <p className="flex-1 text-xs leading-relaxed">{toast.message}</p>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              className="text-current opacity-70 hover:opacity-100 cursor-pointer"
              aria-label="Dismiss notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
