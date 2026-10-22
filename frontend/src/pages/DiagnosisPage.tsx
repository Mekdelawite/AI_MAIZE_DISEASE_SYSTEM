import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  CloudUpload,
  FileImage,
  Loader2,
  RefreshCw,
  ScanLine,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react';

import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { diagnosisService } from '../services/diagnosisService';
import { localDiagnosisService, type LocalDiagnosisResult } from '../services/localDiagnosisService';
import { syncService } from '../services/syncService';
import type { QueuedSyncItem } from '../types/api';
import { formatDateTime } from '../utils/media';
import { ApiError } from '../services/api';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

const ALLOWED_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
];

const ALLOWED_EXTENSIONS = /\.(jpe?g|png|webp)$/i;

export default function DiagnosisPage() {
  const navigate = useNavigate();
  const { t, notify, language, isOnline } = useApp();
  const { user } = useAuth();
  const diagnosisLanguage = user?.preferred_language ?? language;

  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [explain, setExplain] = useState(true);

  const [isDragging, setIsDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [slowRequestWarning, setSlowRequestWarning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [localAnalyzing, setLocalAnalyzing] = useState(false);
  const [localResult, setLocalResult] = useState<LocalDiagnosisResult | null>(null);
  const [modelCached, setModelCached] = useState<boolean | null>(null);

  const [queue, setQueue] = useState<QueuedSyncItem[]>(() =>
    syncService.getQueue()
  );
  const [batchSyncing, setBatchSyncing] = useState(false);

  useEffect(() => {
    let active = true;
    void localDiagnosisService.isModelCached().then((cached) => {
      if (active) setModelCached(cached);
    });
    return () => {
      active = false;
    };
  }, [isOnline]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }

      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
    };
  }, [previewUrl]);

  const refreshQueue = () => {
    setQueue(syncService.getQueue());
  };

  const validateAndSelectFile = (file: File) => {
    setErrorMsg(null);
    setLocalResult(null);

    const validType = ALLOWED_TYPES.includes(file.type);
    const validExtension = ALLOWED_EXTENSIONS.test(file.name);

    if (!validType && !validExtension) {
      setErrorMsg('Please select a JPG, PNG, or WEBP image.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMsg('The image must be 5 MB or smaller.');
      return;
    }

    if (file.size === 0) {
      setErrorMsg('The selected image is empty. Please choose another image.');
      return;
    }

    const newPreviewUrl = URL.createObjectURL(file);

    setPreviewUrl((oldUrl) => {
      if (oldUrl) {
        URL.revokeObjectURL(oldUrl);
      }

      return newPreviewUrl;
    });

    setSelectedFile(file);
  };

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (file) {
      validateAndSelectFile(file);
    }

    // Allow selecting the same image again.
    event.target.value = '';
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);

    if (analyzing) return;

    const file = event.dataTransfer.files?.[0];

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
    setLocalResult(null);

    if (galleryInputRef.current) {
      galleryInputRef.current.value = '';
    }

  };

  const stopCamera = () => {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    setCameraOpen(false);
  };

  const openCamera = async () => {
    setCameraError(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(
        'Camera access is unavailable. Use localhost or HTTPS and a supported browser.'
      );
      return;
    }

    try {
      stopCamera();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });

      cameraStreamRef.current = stream;
      setCameraOpen(true);
    } catch {
      setCameraError(
        'Unable to open the camera. Check browser permissions and ensure no other application is using it.'
      );
    }
  };

  const handleCapturePhoto = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError('The camera preview is not ready yet. Please try again.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');

    if (!context) {
      setCameraError('Unable to capture the camera image. Please try again.');
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError('Unable to capture the camera image. Please try again.');
        return;
      }

      validateAndSelectFile(
        new File([blob], `maize-leaf-${Date.now()}.jpg`, {
          type: 'image/jpeg',
        })
      );
      stopCamera();
    }, 'image/jpeg', 0.92);
  };

  useEffect(() => {
    if (!cameraOpen || !videoRef.current || !cameraStreamRef.current) return;

    videoRef.current.srcObject = cameraStreamRef.current;
    void videoRef.current.play().catch(() => {
      setCameraError('Unable to start the camera preview.');
    });
  }, [cameraOpen]);
  const handleAnalyzeSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (!selectedFile || analyzing) {
      if (!selectedFile) {
        setErrorMsg('Please upload or capture a maize leaf image first.');
      }
      return;
    }

    const imageFile = selectedFile;
    setAnalyzing(true);
    setLocalAnalyzing(false);
    setErrorMsg(null);
    setLocalResult(null);
    setSlowRequestWarning(false);

    const warningTimer = window.setTimeout(() => {
      setSlowRequestWarning(true);
    }, 8000);

    try {
      await localDiagnosisService.validateImage(imageFile);

      if (!isOnline) {
        setLocalAnalyzing(true);
        const result = await localDiagnosisService.predict(imageFile, user?.id);
        setLocalResult(result);
        setModelCached(await localDiagnosisService.isModelCached());
        notify('Offline diagnosis completed using the local model.', 'success');
        return;
      }

      try {
        const result = await diagnosisService.runCompleteDiagnosis({
          image: imageFile,
          language: diagnosisLanguage,
          explain,
        });

        notify('Online diagnosis completed successfully.', 'success');

        navigate('/farmer/diagnose/result', {
          state: {
            result,
            uploadedPreviewUrl: previewUrl,
            requestLanguage: diagnosisLanguage,
            requestedExplain: explain,
            diagnosisMode: 'online',
          },
        });
        return;
      } catch (error: unknown) {
        if (!(error instanceof ApiError) || !error.isNetworkError) {
          throw error;
        }
      }

      setLocalAnalyzing(true);
      const result = await localDiagnosisService.predict(imageFile, user?.id);
      setLocalResult(result);
      setModelCached(await localDiagnosisService.isModelCached());
      notify(
        'Backend unavailable. Diagnosis completed using the local model.',
        'success',
      );
    } catch (error: unknown) {
      setErrorMsg(
        error instanceof Error
          ? error.message
          : 'Diagnosis failed. Please try again.',
      );
      setModelCached(await localDiagnosisService.isModelCached());
    } finally {
      window.clearTimeout(warningTimer);
      setAnalyzing(false);
      setLocalAnalyzing(false);
      setSlowRequestWarning(false);
    }
  };

  const handleQueueOffline = async () => {
    if (!selectedFile) {
      setErrorMsg('Please select an image first.');
      return;
    }

    try {
      await syncService.enqueueDiagnosis({
        file: selectedFile,
        language: diagnosisLanguage,
        explain,
      });

      refreshQueue();
      notify('Diagnosis saved to the offline queue.', 'success');
      handleRemoveImage();
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : 'Unable to save the diagnosis offline.';

      setErrorMsg(message);
    }
  };

  const handleSyncSingle = async (item: QueuedSyncItem) => {
    try {
      await syncService.syncSingleItem(item.operation_id);
      refreshQueue();

      notify('Queued diagnosis synchronization finished.', 'success');
    } catch (error: unknown) {
      refreshQueue();

      const message =
        error instanceof Error
          ? error.message
          : 'Unable to synchronize this diagnosis.';

      notify(message, 'error');
    }
  };

  const handleSyncBatch = async () => {
    if (batchSyncing) return;

    setBatchSyncing(true);

    try {
      await syncService.syncBatch();
      refreshQueue();
      notify('Offline queue synchronization finished.', 'success');
    } catch (error: unknown) {
      refreshQueue();

      const message =
        error instanceof Error
          ? error.message
          : 'Unable to synchronize the offline queue.';

      notify(message, 'error');
    } finally {
      setBatchSyncing(false);
    }
  };

  const handleOpenQueuedResult = (item: QueuedSyncItem) => {
    if (item.serverResult) {
      navigate('/farmer/diagnose/result', {
        state: {
          result: item.serverResult,
          requestLanguage: item.language,
          requestedExplain: explain,
        },
      });
    }
  };

  const handleRemoveQueuedItem = (operationId: string) => {
    try {
      syncService.removeItem(operationId);
      refreshQueue();
      notify('Queued item removed.', 'success');
    } catch {
      notify('Unable to remove this queued item.', 'error');
    }
  };

  const eligibleForBatchCount = queue.filter((item) =>
    ['queued', 'failed'].includes(item.status)
  ).length;

  return (
    <AppShell
      title={t('diagnosisPageTitle')}
      subtitle={t('diagnosisPageSubtitle')}
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] px-4 py-3 text-sm" role="status" aria-live="polite">
        <span className="inline-flex items-center gap-2 font-semibold text-stone-800 dark:text-stone-200">
          {isOnline ? <Wifi className="h-4 w-4 text-emerald-700" /> : <WifiOff className="h-4 w-4 text-amber-700" />}
          {isOnline ? t('onlineStatus') : t('offlineStatus')}
        </span>
        <span className="text-xs text-stone-600 dark:text-stone-400">
          {t('offlineModelStatus')}: {modelCached === null ? t('checkingModelStatus') : modelCached ? t('modelReadyOffline') : t('modelNeedsDownload')}
        </span>
      </div>

      {(cameraOpen || cameraError) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="camera-dialog-title"
            className="w-full max-w-2xl rounded-xl bg-white dark:bg-[#121A16] p-5 shadow-xl"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2
                id="camera-dialog-title"
                className="text-lg font-semibold text-stone-900 dark:text-stone-100"
              >
                Capture maize leaf image
              </h2>
              <button
                type="button"
                onClick={() => {
                  stopCamera();
                  setCameraError(null);
                }}
                className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-700 dark:border-stone-700 dark:text-stone-200"
              >
                Close
              </button>
            </div>

            {cameraOpen && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="aspect-video w-full rounded-lg bg-black object-contain"
              />
            )}

            {cameraError && (
              <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-300">
                {cameraError}
              </p>
            )}

            {cameraOpen && (
              <button
                type="button"
                onClick={handleCapturePhoto}
                className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-900 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800"
              >
                <Camera className="h-4 w-4" />
                Take Photo
              </button>
            )}
          </section>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: image selection and diagnosis */}
        <div className="lg:col-span-7 space-y-6">
          <form
            onSubmit={handleAnalyzeSubmit}
            className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-6"
          >
            {/* Upload input: choose an existing image */}
            <input
              ref={galleryInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="sr-only"
              id="leaf-gallery-select"
              aria-label="Upload maize leaf image"
              disabled={analyzing}
            />

            {!selectedFile ? (
              <div
                onDragOver={(event) => {
                  event.preventDefault();

                  if (!analyzing) {
                    setIsDragging(true);
                  }
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`rounded-xl border-2 border-dashed p-8 sm:p-10 text-center transition-colors ${
                  isDragging
                    ? 'border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/30'
                    : 'border-stone-300 dark:border-stone-700 bg-[#FAF8F5] dark:bg-[#151F1A]'
                }`}
              >
                <CloudUpload className="w-10 h-10 text-emerald-800 dark:text-emerald-400 mx-auto mb-3" />

                <p className="text-sm font-semibold text-stone-900 dark:text-stone-100">
                  {t('uploadDropTitle')}
                </p>

                <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-400">
                  {t('uploadDropHint')}
                </p>

                {/* Exactly two options */}
                <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                  <button
                    type="button"
                    disabled={analyzing}
                    onClick={() => galleryInputRef.current?.click()}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50"
                  >
                    <FileImage className="w-3.5 h-3.5" />
                    <span>Upload Image</span>
                  </button>

                  <button
                    type="button"
                    disabled={analyzing}
                    onClick={() => {
                      setErrorMsg(null);
                      void openCamera();
                    }}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-emerald-900 dark:text-emerald-300 border border-emerald-800 dark:border-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 rounded-lg disabled:opacity-50"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span>Capture with Camera</span>
                  </button>
                </div>

                <p className="mt-4 text-[11px] text-stone-500 dark:text-stone-400">
                  JPG, PNG or WEBP · Maximum 5 MB
                </p>

                <p className="mt-2 text-[11px] text-stone-500 dark:text-stone-400">
                  You can also drag and drop an image here.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-stone-200 dark:border-stone-800 overflow-hidden bg-stone-950">
                <div className="relative aspect-[4/3] max-h-[360px] w-full flex items-center justify-center">
                  {previewUrl && (
                    <img
                      src={previewUrl}
                      alt="Selected maize leaf preview"
                      className="max-h-[360px] max-w-full object-contain"
                    />
                  )}
                </div>

                <div className="p-4 bg-white dark:bg-[#151F1A] border-t border-stone-200 dark:border-stone-800 flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-stone-900 dark:text-stone-100 truncate">
                      {selectedFile.name}
                    </p>

                    <p className="text-xs text-stone-500 font-mono tabular-nums">
                      {(selectedFile.size / 1024).toFixed(1)} KB ·{' '}
                      {selectedFile.type || 'image'}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={analyzing}
                      onClick={() => galleryInputRef.current?.click()}
                      className="px-3 py-1.5 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 disabled:opacity-50"
                    >
                      Replace Image
                    </button>

                    <button
                      type="button"
                      disabled={analyzing}
                      onClick={() => {
                        setErrorMsg(null);
                        void openCamera();
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-950/30 disabled:opacity-50"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      Retake
                    </button>

                    <button
                      type="button"
                      disabled={analyzing}
                      onClick={handleRemoveImage}
                      className="px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Explainability */}
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={explain}
                onChange={(event) => setExplain(event.target.checked)}
                disabled={analyzing}
                className="mt-1 h-4 w-4 accent-emerald-800"
              />

              <span>
                <span className="block text-sm font-medium text-stone-900 dark:text-stone-100">
                  Show AI explanation (Grad-CAM)
                </span>
                <span className="block mt-1 text-xs text-stone-500 dark:text-stone-400">
                  Display the image regions that influenced the prediction.
                </span>
              </span>
            </label>

            {/* Error */}
            {errorMsg && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/20 p-3 text-sm text-red-800 dark:text-red-300"
              >
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <p>{errorMsg}</p>
              </div>
            )}

            {slowRequestWarning && analyzing && (
              <div className="flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-950/20 p-3 text-sm text-amber-800 dark:text-amber-300">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <p>
                  Diagnosis is taking longer than expected. Please keep this
                  page open while the request completes.
                </p>
              </div>
            )}

            {/* Main actions */}
<div className="flex flex-col sm:flex-row gap-3">
  <button
    type="submit"
    disabled={!selectedFile || analyzing || localAnalyzing}
    className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-900 hover:bg-emerald-800 text-white px-5 py-3 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
  >
    {analyzing || localAnalyzing ? (
      <>
        <Loader2 className="w-4 h-4 animate-spin" />
        {localAnalyzing
          ? 'Running local diagnosis...'
          : 'Checking connection and diagnosing...'}
      </>
    ) : (
      <>
        <ScanLine className="w-4 h-4" />
        Diagnose
      </>
    )}
  </button>

  <button
    type="button"
    disabled={!selectedFile || analyzing || localAnalyzing}
    onClick={handleQueueOffline}
    className="inline-flex items-center justify-center gap-2 rounded-lg border border-stone-300 dark:border-stone-700 text-stone-800 dark:text-stone-200 px-5 py-3 text-sm font-semibold hover:bg-stone-50 dark:hover:bg-stone-800 disabled:opacity-50 disabled:cursor-not-allowed"
  >
    <WifiOff className="w-4 h-4" />
    Save for Later
  </button>
</div>

            {localResult && (
              <section className="rounded-xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/70 dark:bg-emerald-950/20 p-5" aria-live="polite">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">{t('localResultTitle')}</p>
                    <h2 className="mt-1 text-xl font-bold text-stone-900 dark:text-stone-100">
                      {t(localResult.className === 'Northern Leaf Blight' ? 'aboutDiseaseNlb' : localResult.className === 'Common Rust' ? 'aboutDiseaseRust' : localResult.className === 'Gray Leaf Spot' ? 'aboutDiseaseGray' : 'aboutDiseaseHealthy')}
                    </h2>
                    <p className="mt-1 text-sm text-stone-700 dark:text-stone-300">{t('confidenceLabel')}: {(localResult.confidence * 100).toFixed(2)}%</p>
                  </div>
                  <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/50 px-3 py-1 text-xs font-semibold text-emerald-900 dark:text-emerald-200">{t('localOnlyBadge')}</span>
                </div>
                <ul className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-stone-700 dark:text-stone-300">
                  {localResult.probabilities.map((probability, index) => {
                    const labelKey = ['aboutDiseaseNlb', 'aboutDiseaseRust', 'aboutDiseaseGray', 'aboutDiseaseHealthy'][index];
                    return <li key={labelKey} className="flex justify-between gap-3 rounded-md bg-white/70 dark:bg-stone-900/50 px-3 py-2"><span>{t(labelKey)}</span><strong>{(probability * 100).toFixed(2)}%</strong></li>;
                  })}
                </ul>
                <p className="mt-4 text-xs leading-relaxed text-stone-600 dark:text-stone-400">{t('localResultLimitations')}</p>
              </section>
            )}
          </form>
        </div>

        {/* Right: guidance and offline queue */}
        <div className="lg:col-span-5 space-y-6">
          <section className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-emerald-700 dark:text-emerald-400" />
              <h2 className="font-semibold text-stone-900 dark:text-stone-100">
                Image capture tips
              </h2>
            </div>

            <ul className="space-y-3 text-sm text-stone-600 dark:text-stone-300">
              <li>• Photograph a maize leaf, not a person or another object.</li>
              <li>• Keep the leaf in focus and make symptoms clearly visible.</li>
              <li>• Use good natural lighting and avoid strong shadows.</li>
              <li>• Include the affected area of the leaf in the frame.</li>
              <li>• Use JPG, PNG, or WEBP images no larger than 5 MB.</li>
            </ul>
          </section>

          <section className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <WifiOff className="w-5 h-5 text-emerald-700 dark:text-emerald-400" />
                  <h2 className="font-semibold text-stone-900 dark:text-stone-100">
                    Offline diagnosis queue
                  </h2>
                </div>

                <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">
                  {queue.length} saved item(s)
                </p>
              </div>

              <button
                type="button"
                onClick={handleSyncBatch}
                disabled={batchSyncing || eligibleForBatchCount === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-900 hover:bg-emerald-800 text-white px-3 py-2 text-xs font-semibold disabled:opacity-50"
              >
                {batchSyncing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                Sync Queue
              </button>
            </div>

            {queue.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle2 className="w-8 h-8 mx-auto text-stone-300 dark:text-stone-600 mb-2" />
                <p className="text-sm text-stone-500 dark:text-stone-400">
                  No offline diagnoses waiting to sync.
                </p>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {queue.map((item) => (
                  <div
                    key={item.operation_id}
                    className="rounded-lg border border-stone-200 dark:border-stone-800 p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-stone-900 dark:text-stone-100 break-words">
                          {item.fileName || 'Maize leaf diagnosis'}
                        </p>

                        <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">
                          {item.createdAt
                            ? formatDateTime(item.createdAt)
                            : 'Saved locally'}
                        </p>

                        <p className="mt-2 text-xs text-stone-600 dark:text-stone-300">
                          Status: {item.status}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          handleRemoveQueuedItem(item.operation_id)
                        }
                        title="Remove queued item"
                        aria-label="Remove queued item"
                        className="shrink-0 p-1.5 rounded-md text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.serverResult && (
                        <button
                          type="button"
                          onClick={() => handleOpenQueuedResult(item)}
                          className="rounded-md border border-stone-300 dark:border-stone-700 px-3 py-1.5 text-xs font-medium text-stone-700 dark:text-stone-200"
                        >
                          View Result
                        </button>
                      )}

                      {['queued', 'failed'].includes(item.status) && (
                        <button
                          type="button"
                          onClick={() => handleSyncSingle(item)}
                          className="inline-flex items-center gap-1.5 rounded-md bg-emerald-900 hover:bg-emerald-800 px-3 py-1.5 text-xs font-semibold text-white"
                        >
                          <RefreshCw className="w-3 h-3" />
                          Sync Now
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
}
