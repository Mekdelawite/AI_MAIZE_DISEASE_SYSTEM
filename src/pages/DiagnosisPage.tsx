import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  CloudUpload,
  FileImage,
  Loader2,
  RefreshCw,
  ScanLine,
  Trash2,
  WifiOff,
} from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { diagnosisService } from '../services/diagnosisService';
import { syncService } from '../services/syncService';
import { QueuedSyncItem } from '../types/api';
import { formatDateTime } from '../utils/media';

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const ALLOWED_EXTENSIONS = /\.(jpg|jpeg|png|webp)$/i;
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export const DiagnosisPage: React.FC = () => {
  const { t, language, isOnline, notify } = useApp();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [diagLanguage, setDiagLanguage] = useState<'en' | 'am'>(language);
  const [explain, setExplain] = useState<boolean>(true);
  const [isDragging, setIsDragging] = useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [slowRequestWarning, setSlowRequestWarning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Offline Queue State
  const [queue, setQueue] = useState<QueuedSyncItem[]>(() => syncService.getQueue());
  const [batchSyncing, setBatchSyncing] = useState(false);

  useEffect(() => {
    setDiagLanguage(language);
  }, [language]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const validateAndSelectFile = (file: File) => {
    setErrorMsg(null);
    if (!ALLOWED_TYPES.includes(file.type) && !ALLOWED_EXTENSIONS.test(file.name)) {
      setErrorMsg('Unsupported file format. Please select a JPG, JPEG, PNG, or WEBP image.');
      return;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorMsg(
        `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 5 MB maximum upload limit.`
      );
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      validateAndSelectFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (analyzing) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      validateAndSelectFile(file);
    }
  };

  const handleRemoveImage = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setErrorMsg(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAnalyzeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || analyzing) return;

    setAnalyzing(true);
    setSlowRequestWarning(false);
    setErrorMsg(null);

    const slowTimer = setTimeout(() => {
      setSlowRequestWarning(true);
    }, 8000);

    try {
      const result = await diagnosisService.runCompleteDiagnosis({
        image: selectedFile,
        language: diagLanguage,
        explain,
      });

      notify('Maize leaf diagnosis completed by server.', 'success');
      navigate('/farmer/diagnose/result', {
        state: {
          result,
          uploadedPreviewUrl: previewUrl,
          requestLanguage: diagLanguage,
          requestedExplain: explain,
        },
      });
    } catch (err: any) {
      setErrorMsg(
        err?.message ||
          'Diagnosis request failed. If internet connectivity is unstable, you can queue this image for offline synchronization below.'
      );
    } finally {
      clearTimeout(slowTimer);
      setAnalyzing(false);
    }
  };

  const handleQueueOffline = async () => {
    if (!selectedFile) return;
    try {
      const item = await syncService.enqueueDiagnosis({
        file: selectedFile,
        language: diagLanguage,
        explain,
      });
      setQueue(syncService.getQueue());
      notify(`Queued leaf image (${item.operation_id}) for synchronization.`, 'info');
      handleRemoveImage();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Could not queue image in local storage.');
    }
  };

  const handleSyncSingle = async (operationId: string) => {
    try {
      setQueue((prev) =>
        prev.map((i) => (i.operation_id === operationId ? { ...i, status: 'syncing' } : i))
      );
      const updated = await syncService.syncSingleItem(operationId);
      setQueue(syncService.getQueue());
      notify(`Operation ${operationId} synchronized with server.`, 'success');
      if (updated.serverResult) {
        navigate('/farmer/diagnose/result', {
          state: {
            result: updated.serverResult,
            uploadedPreviewUrl: updated.imageDataUrl,
            requestLanguage: updated.language,
            requestedExplain: updated.explain,
          },
        });
      }
    } catch (err: any) {
      setQueue(syncService.getQueue());
      notify(err?.message || `Failed to sync ${operationId}`, 'error');
    }
  };

  const handleSyncBatch = async () => {
    if (batchSyncing) return;
    setBatchSyncing(true);
    try {
      const { syncedCount, failedCount } = await syncService.syncBatch();
      setQueue(syncService.getQueue());
      if (syncedCount > 0) {
        notify(`Batch sync finished: ${syncedCount} succeeded, ${failedCount} failed.`, 'success');
      } else {
        notify(`Batch sync completed with ${failedCount} failed operation(s).`, 'warning');
      }
    } catch (err: any) {
      setQueue(syncService.getQueue());
      notify(err?.message || 'Batch synchronization failed.', 'error');
    } finally {
      setBatchSyncing(false);
    }
  };

  const eligibleForBatchCount = queue.filter((i) => i.status === 'queued' || i.status === 'failed').length;

  return (
    <AppShell title={t('diagnosisPageTitle')} subtitle={t('diagnosisPageSubtitle')}>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Upload & Configuration Form */}
        <div className="lg:col-span-7 space-y-6">
          <form
            onSubmit={handleAnalyzeSubmit}
            className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-6"
          >
            {/* Dropzone or Image Preview */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="sr-only"
                id="leaf-image-upload"
                disabled={analyzing}
              />

              {!selectedFile ? (
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (!analyzing) setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => !analyzing && fileInputRef.current?.click()}
                  className={`rounded-xl border-2 border-dashed p-10 text-center transition-colors cursor-pointer ${
                    isDragging
                      ? 'border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/30'
                      : 'border-stone-300 dark:border-stone-700 hover:border-emerald-700 dark:hover:border-emerald-600 bg-[#FAF8F5] dark:bg-[#151F1A]'
                  }`}
                >
                  <CloudUpload className="w-10 h-10 text-emerald-800 dark:text-emerald-400 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-stone-900 dark:text-stone-100">
                    {t('uploadDropTitle')}
                  </p>
                  <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-400">
                    {t('uploadDropHint')}
                  </p>
                  <div className="mt-5">
                    <span className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg">
                      <FileImage className="w-3.5 h-3.5" />
                      <span>{t('selectImageBtn')}</span>
                    </span>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-stone-200 dark:border-stone-800 overflow-hidden bg-stone-950">
                  <div className="relative aspect-4/3 max-h-[360px] w-full flex items-center justify-center">
                    {previewUrl && (
                      <img
                        src={previewUrl}
                        alt="Selected maize leaf preview"
                        className="max-h-[360px] w-auto object-contain"
                      />
                    )}
                  </div>
                  <div className="p-4 bg-white dark:bg-[#151F1A] border-t border-stone-200 dark:border-stone-800 flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-stone-900 dark:text-stone-100 truncate">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-stone-500 font-mono tabular-nums">
                        {(selectedFile.size / 1024).toFixed(1)} KB · {selectedFile.type || 'image'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={analyzing}
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-1.5 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer disabled:opacity-50"
                      >
                        {t('replaceImageBtn')}
                      </button>
                      <button
                        type="button"
                        disabled={analyzing}
                        onClick={handleRemoveImage}
                        className="px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 cursor-pointer disabled:opacity-50"
                      >
                        {t('removeImageBtn')}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Configuration Controls */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-stone-200 dark:border-stone-800">
              <div>
                <label
                  htmlFor="diag-lang"
                  className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1.5"
                >
                  Advisory Response Language
                </label>
                <select
                  id="diag-lang"
                  disabled={analyzing}
                  value={diagLanguage}
                  onChange={(e) => setDiagLanguage(e.target.value as 'en' | 'am')}
                  className="w-full px-3.5 py-2 text-xs font-medium rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                >
                  <option value="en">English (en)</option>
                  <option value="am">አማርኛ / Amharic (am)</option>
                </select>
              </div>

              <div className="flex flex-col justify-center">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    disabled={analyzing}
                    checked={explain}
                    onChange={(e) => setExplain(e.target.checked)}
                    className="mt-0.5 rounded border-stone-300 text-emerald-800 focus:ring-emerald-700"
                  />
                  <div>
                    <span className="block text-xs font-medium text-stone-900 dark:text-stone-100">
                      {t('explainToggleLabel')}
                    </span>
                    <span className="block text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                      {t('explainToggleHint')}
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* Error State */}
            {errorMsg && (
              <div
                className="rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 p-4 flex items-start gap-3 text-xs text-red-800 dark:text-red-200"
                role="alert"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1 space-y-2">
                  <p>{errorMsg}</p>
                  {selectedFile && (
                    <button
                      type="button"
                      onClick={handleQueueOffline}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 font-medium text-amber-900 bg-amber-100 hover:bg-amber-200 rounded-md cursor-pointer"
                    >
                      <WifiOff className="w-3.5 h-3.5" />
                      <span>Save to Offline Sync Queue Instead</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Processing Indicator (Honest, no fake percentage) */}
            {analyzing && (
              <div
                className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/60 dark:bg-emerald-950/20 p-5"
                role="status"
                aria-live="polite"
              >
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-emerald-800 dark:text-emerald-400 animate-spin shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-emerald-950 dark:text-emerald-200">
                      {t('analyzingTitle')}
                    </p>
                    <p className="mt-0.5 text-xs text-emerald-800 dark:text-emerald-300/90">
                      {t('analyzingSubtitle')}
                    </p>
                    {slowRequestWarning && (
                      <p className="mt-2 text-xs text-amber-800 dark:text-amber-300">
                        Still waiting for backend model inference and advisory generation...
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Submit & Offline Queue Actions */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={!selectedFile || analyzing}
                className="flex-1 min-w-[200px] inline-flex items-center justify-center gap-2 py-3 px-5 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors disabled:opacity-50 cursor-pointer whitespace-nowrap"
              >
                <ScanLine className="w-4 h-4" />
                <span>{analyzing ? 'Analyzing on Server...' : t('analyzeLeafBtn')}</span>
              </button>

              <button
                type="button"
                disabled={!selectedFile || analyzing}
                onClick={handleQueueOffline}
                className="inline-flex items-center justify-center gap-2 py-3 px-4 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors disabled:opacity-50 cursor-pointer whitespace-nowrap"
              >
                <WifiOff className="w-4 h-4" />
                <span>{t('queueOfflineBtn')}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Right: Field Capture Guidance & Offline Synchronization Manager */}
        <div className="lg:col-span-5 space-y-6">
          {/* Instructions */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
            <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
              Leaf Photography Guidelines
            </h2>
            <ul className="mt-3 space-y-2.5 text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
              <li>
                1. Center a single maize leaf clearly in natural daylight without harsh camera flash glare.
              </li>
              <li>
                2. Include both symptomatic lesions and adjacent leaf tissue so MobileNetV2 and Grad-CAM can evaluate pattern boundaries.
              </li>
              <li>
                3. Avoid blurry images or shots containing multiple overlapping plants or soil clutter.
              </li>
            </ul>
            <div className="mt-4 pt-4 border-t border-stone-200/70 dark:border-stone-800 text-xs text-stone-500 dark:text-stone-400">
              <strong>Note on Internet Access:</strong> Live MobileNetV2 classification and Grad-CAM generation execute on the Flask backend server. When offline, queue images below and synchronize when connectivity returns.
            </div>
          </div>

          {/* Offline Queue Panel (POST /api/sync & POST /api/sync/batch) */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                  Offline Synchronization Queue
                </h2>
                <p className="text-xs text-stone-500 dark:text-stone-400">
                  Endpoints: <code className="font-mono">/api/sync</code> &{' '}
                  <code className="font-mono">/api/sync/batch</code> (max 10)
                </p>
              </div>
              {eligibleForBatchCount > 0 && (
                <button
                  type="button"
                  disabled={batchSyncing || !isOnline}
                  onClick={handleSyncBatch}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-800 hover:bg-emerald-700 rounded-lg disabled:opacity-50 cursor-pointer whitespace-nowrap"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${batchSyncing ? 'animate-spin' : ''}`} />
                  <span>Sync Batch ({Math.min(10, eligibleForBatchCount)})</span>
                </button>
              )}
            </div>

            {queue.length === 0 ? (
              <p className="mt-4 text-xs text-stone-500 dark:text-stone-400">
                No queued offline operations. Use “{t('queueOfflineBtn')}” when working without internet access.
              </p>
            ) : (
              <div className="mt-4 space-y-3">
                {queue.map((item) => (
                  <div
                    key={item.operation_id}
                    className="rounded-lg border border-stone-200 dark:border-stone-800 p-3 flex items-start gap-3"
                  >
                    <img
                      src={item.imageDataUrl}
                      alt={item.fileName}
                      className="w-12 h-12 rounded object-cover shrink-0 bg-stone-900"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold text-stone-900 dark:text-stone-100 truncate">
                          {item.fileName}
                        </p>
                        <span className="text-xs font-mono text-stone-500">{item.status}</span>
                      </div>
                      <p className="text-[11px] font-mono text-stone-500 truncate">
                        {item.operation_id} · {item.language.toUpperCase()} · {formatDateTime(item.createdAt)}
                      </p>
                      {item.errorMessage && (
                        <p className="mt-1 text-xs text-red-700 dark:text-red-400">{item.errorMessage}</p>
                      )}
                      <div className="mt-2 flex items-center gap-3">
                        {(item.status === 'queued' || item.status === 'failed') && (
                          <button
                            type="button"
                            onClick={() => handleSyncSingle(item.operation_id)}
                            className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline cursor-pointer"
                          >
                            {item.status === 'failed' ? 'Retry Sync' : 'Sync Now'}
                          </button>
                        )}
                        {item.status === 'succeeded' && item.serverResult && (
                          <button
                            type="button"
                            onClick={() =>
                              navigate('/farmer/diagnose/result', {
                                state: {
                                  result: item.serverResult,
                                  uploadedPreviewUrl: item.imageDataUrl,
                                  requestLanguage: item.language,
                                  requestedExplain: item.explain,
                                },
                              })
                            }
                            className="inline-flex items-center gap-1 text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline cursor-pointer"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Open Result</span>
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setQueue(syncService.removeItem(item.operation_id))}
                          className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-red-700 cursor-pointer"
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>Remove</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
};
