import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  CloudUpload,
  FileImage,
  Loader2,
  ScanLine,
  Wifi,
  WifiOff,
} from 'lucide-react';

import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { diagnosisService } from '../services/diagnosisService';
import {
  InvalidMaizeLeafImageError,
  localDiagnosisService,
  type LocalDiagnosisResult,
} from '../services/localDiagnosisService';
import {
  createOfflineDiagnosisOperationId,
  offlineDiagnosisStore,
  type OfflineDiagnosisRecord,
} from '../services/offlineDiagnosisStore';
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
  const { t, notify, language, isOnline, connectionStatus } = useApp();
  const { user } = useAuth();
  const diagnosisLanguage = user?.preferred_language ?? language;

  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraRequesting, setCameraRequesting] = useState(false);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const cameraRequestIdRef = useRef(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageValidationStatus, setImageValidationStatus] = useState<
    'idle' | 'checking' | 'valid' | 'invalid'
  >('idle');
  const [explain, setExplain] = useState(true);

  const [isDragging, setIsDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [slowRequestWarning, setSlowRequestWarning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [localAnalyzing, setLocalAnalyzing] = useState(false);
  const [localResult, setLocalResult] = useState<LocalDiagnosisResult | null>(null);
  const [modelCached, setModelCached] = useState<boolean | null>(null);
  const [offlineRecords, setOfflineRecords] = useState<OfflineDiagnosisRecord[]>([]);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<
    'idle' | 'restored' | 'syncing' | 'succeeded' | 'failed'
  >('idle');
  const [diagnosisStatus, setDiagnosisStatus] = useState<
    'idle' | 'validating' | 'checking' | 'online' | 'offline' | 'completed' | 'pending'
  >('idle');
  const activeOperationIdRef = useRef<string | null>(null);

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
    if (user?.id === undefined || user.id === null) {
      setOfflineRecords([]);
      return;
    }

    let active = true;
    const refreshRecords = async () => {
      try {
        const records = await offlineDiagnosisStore.getAll(user.id);
        if (active) {
          setOfflineRecords(records);
          setQueueError(null);
          if (
            activeOperationIdRef.current &&
            records.some(
              (record) =>
                record.operation_id === activeOperationIdRef.current &&
                record.sync_status === 'synced',
            )
          ) {
            setDiagnosisStatus('completed');
          }
        }
      } catch (error) {
        console.error('Could not load the farmer offline diagnosis queue:', error);
        if (active) {
          setQueueError(
            error instanceof Error
              ? error.message
              : 'Unable to load offline diagnoses.',
          );
        }
      }
    };
    const handleSyncStatus = (event: Event) => {
      const status = (event as CustomEvent<{ status?: string }>).detail?.status;
      if (
        status === 'restored' ||
        status === 'syncing' ||
        status === 'succeeded' ||
        status === 'failed'
      ) {
        setSyncStatus(status);
      }
      void refreshRecords();
    };

    void refreshRecords();
    window.addEventListener(
      'maizecare:offline-diagnosis-queue-changed',
      refreshRecords,
    );
    window.addEventListener(
      'maizecare:offline-diagnosis-sync-status',
      handleSyncStatus,
    );

    return () => {
      active = false;
      window.removeEventListener(
        'maizecare:offline-diagnosis-queue-changed',
        refreshRecords,
      );
      window.removeEventListener(
        'maizecare:offline-diagnosis-sync-status',
        handleSyncStatus,
      );
    };
  }, [user?.id]);

  useEffect(() => {
    if (!previewUrl) return;
    return () => URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  useEffect(() => {
    return () => {
      cameraRequestIdRef.current += 1;
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
    };
  }, []);

  const validateAndSelectFile = (file: File) => {
    setErrorMsg(null);
    setLocalResult(null);
    setDiagnosisStatus('idle');
    setImageValidationStatus('idle');
    activeOperationIdRef.current = null;
    setSelectedFile(null);
    setPreviewUrl(null);

    const fileType = file.type.toLowerCase();
    const validType = ALLOWED_TYPES.includes(fileType);
    const validExtension = ALLOWED_EXTENSIONS.test(file.name);

    if (!validExtension || (fileType !== '' && !validType)) {
      setErrorMsg(t('imageTypeUnsupported'));
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMsg(t('imageTooLarge'));
      return;
    }

    if (file.size === 0) {
      setErrorMsg(t('imageEmpty'));
      return;
    }

    const newPreviewUrl = URL.createObjectURL(file);
    setPreviewUrl(newPreviewUrl);
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
    setSelectedFile(null);
    setPreviewUrl(null);
    setErrorMsg(null);
    setLocalResult(null);
    setDiagnosisStatus('idle');
    setImageValidationStatus('idle');
    activeOperationIdRef.current = null;

    if (galleryInputRef.current) {
      galleryInputRef.current.value = '';
    }

  };

  const stopCamera = () => {
    cameraRequestIdRef.current += 1;
    const stream = cameraStreamRef.current;
    stream?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    if (videoRef.current?.srcObject === stream) {
      videoRef.current.srcObject = null;
    }
    setCameraOpen(false);
    setCameraRequesting(false);
  };

  const openCamera = async () => {
    stopCamera();
    setCameraError(null);

    if (!window.isSecureContext) {
      setCameraError(t('cameraSecureContext'));
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(t('cameraUnavailable'));
      return;
    }

    const requestId = ++cameraRequestIdRef.current;
    setCameraRequesting(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });

      if (requestId !== cameraRequestIdRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      cameraStreamRef.current = stream;
      setCameraOpen(true);
    } catch (error: unknown) {
      if (requestId !== cameraRequestIdRef.current) return;
      const errorName = error instanceof Error ? error.name : '';
      const messageKey = errorName === 'NotAllowedError' || errorName === 'PermissionDeniedError'
        ? 'cameraPermissionDenied'
        : errorName === 'NotFoundError' || errorName === 'OverconstrainedError'
          ? 'cameraUnavailable'
          : errorName === 'NotReadableError'
            ? 'cameraBusy'
            : 'cameraOpenError';
      setCameraError(t(messageKey));
    } finally {
      if (requestId === cameraRequestIdRef.current) {
        setCameraRequesting(false);
      }
    }
  };

  const handleCapturePhoto = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError(t('cameraPreviewNotReady'));
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');

    if (!context) {
      setCameraError(t('cameraCaptureError'));
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError(t('cameraCaptureError'));
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
      setCameraError(t('cameraPreviewError'));
      stopCamera();
    });
  }, [cameraOpen]);
  const handleAnalyzeSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (!selectedFile || analyzing) {
      if (!selectedFile) {
        setErrorMsg(t('imageSelectRequired'));
      }
      return;
    }

    const imageFile = selectedFile;
    const operationId = createOfflineDiagnosisOperationId();
    activeOperationIdRef.current = operationId;
    const createdAt = new Date().toISOString();
    setAnalyzing(true);
    setLocalAnalyzing(false);
    setErrorMsg(null);
    setLocalResult(null);
    setSlowRequestWarning(false);
    setDiagnosisStatus('validating');
    setImageValidationStatus('checking');

    const warningTimer = window.setTimeout(() => {
      setSlowRequestWarning(true);
    }, 8000);

    try {
      await localDiagnosisService.validateImage(imageFile);
      setImageValidationStatus('valid');

      if (navigator.onLine && (await diagnosisService.isBackendAvailable())) {
        setDiagnosisStatus('online');

        try {
          const result = await diagnosisService.runCompleteDiagnosis({
            image: imageFile,
            language: diagnosisLanguage,
            explain,
            operationId,
          });

          setDiagnosisStatus('completed');
          notify(t('diagnosisCompleted'), 'success');
          navigate('/farmer/diagnose/result', {
            state: {
              result,
              uploadedImage: imageFile,
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
      }

      if (user?.id === undefined || user.id === null) {
        throw new Error('Sign in as a farmer before saving an offline diagnosis.');
      }

      setDiagnosisStatus('offline');
      setLocalAnalyzing(true);
      const result = await localDiagnosisService.predict(imageFile, user.id, {
        queueForSync: true,
        operationId,
        language: diagnosisLanguage,
        explain,
        createdAt,
      });
      setLocalResult(result);
      setModelCached(await localDiagnosisService.isModelCached());
      setDiagnosisStatus('pending');
      notify(t('savedLocallyWaiting'), 'info');
    } catch (error: unknown) {
      setDiagnosisStatus('idle');
      const invalidMaizeImage = error instanceof InvalidMaizeLeafImageError ||
        (error instanceof ApiError &&
          error.message.toLowerCase().includes('does not appear to show a maize leaf'));
      setImageValidationStatus(invalidMaizeImage ? 'invalid' : 'idle');
      setErrorMsg(invalidMaizeImage
        ? t('invalidMaizeLeafImage')
        : error instanceof Error &&
          error.message.toLowerCase().includes('could not be decoded')
          ? t('imageUnreadable')
          : error instanceof Error
            ? error.message
            : t('diagnosisFailed'));
      setModelCached(await localDiagnosisService.isModelCached());
    } finally {
      window.clearTimeout(warningTimer);
      setAnalyzing(false);
      setLocalAnalyzing(false);
      setSlowRequestWarning(false);
    }
  };

  return (
    <AppShell
      title={t('diagnosisPageTitle')}
      subtitle={t('diagnosisPageSubtitle')}
    >
      <div className="farmer-card mb-5 flex flex-wrap items-center justify-between gap-3 px-4 py-3.5 text-sm" role="status" aria-live="polite">
        <span className="inline-flex items-center gap-2 font-semibold text-stone-800 dark:text-stone-200">
          {isOnline ? <Wifi className="h-4 w-4 text-emerald-700" /> : <WifiOff className="h-4 w-4 text-amber-700" />}
          {t({
            checking: 'connectionCheckingStatus',
            online: 'onlineStatus',
            offline: 'offlineStatus',
            unavailable: 'connectionUnavailableStatus',
          }[connectionStatus])}
        </span>
        <div className="flex flex-col items-end gap-1 text-xs text-stone-600 dark:text-stone-400">
          {diagnosisStatus !== 'idle' && (
            <span>
              {t({
                validating: 'imageValidating',
                checking: 'checkingConnection',
                online: 'onlineDiagnosisInProgress',
                offline: 'offlineDiagnosisInProgress',
                completed: 'diagnosisCompleted',
                pending: 'savedLocallyWaiting',
              }[diagnosisStatus])}
            </span>
          )}
          {syncStatus !== 'idle' && (
            <span>
              {t({
                restored: 'internetRestoredSyncing',
                syncing: 'internetRestoredSyncing',
                succeeded: 'syncCompleted',
                failed: 'syncFailedWillRetry',
              }[syncStatus])}
            </span>
          )}
          <span>
            {t('offlineModelStatus')}: {modelCached === null ? t('checkingModelStatus') : modelCached ? t('modelReadyOffline') : t('modelNeedsDownload')}
          </span>
        </div>
      </div>

      {(cameraOpen || cameraError || cameraRequesting) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="camera-dialog-title"
            className="w-full max-w-2xl rounded-3xl bg-white p-4 shadow-xl dark:bg-[#121A16] sm:p-6"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2
                id="camera-dialog-title"
                className="text-lg font-semibold text-stone-900 dark:text-stone-100"
              >
                {t('cameraTitle')}
              </h2>
              <button
                type="button"
                onClick={() => {
                  stopCamera();
                  setCameraError(null);
                }}
                className="min-h-11 rounded-lg border border-stone-300 px-3 text-sm text-stone-700 dark:border-stone-700 dark:text-stone-200"
              >
                {t('cameraClose')}
              </button>
            </div>

            <p className="mb-4 text-sm text-stone-600 dark:text-stone-300">
              {t('cameraPermissionHint')}
            </p>

            {cameraOpen && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="aspect-video w-full rounded-lg bg-black object-contain"
              />
            )}

            {cameraRequesting && (
              <p className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-300" role="status" aria-live="polite">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('cameraOpening')}
              </p>
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
                aria-label={t('cameraTakePhoto')}
                className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-emerald-900 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800"
              >
                <Camera className="h-4 w-4" />
                {t('cameraTakePhoto')}
              </button>
            )}
            {cameraError && (
              <button
                type="button"
                onClick={() => {
                  stopCamera();
                  setCameraError(null);
                  galleryInputRef.current?.click();
                }}
                className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 dark:border-stone-700 dark:text-stone-200"
              >
                <FileImage className="h-4 w-4" />
                {t('chooseFromGallery')}
              </button>
            )}
          </section>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: image selection and diagnosis */}
        <div className="min-w-0 space-y-5 lg:col-span-7 lg:space-y-6">
          <form
            onSubmit={handleAnalyzeSubmit}
            className="farmer-card min-w-0 space-y-5 p-4 sm:space-y-6 sm:p-7"
          >
            {/* Upload input: choose an existing image */}
            <input
              ref={galleryInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="sr-only"
              id="leaf-gallery-select"
              aria-label={t('uploadImage')}
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
                className={`rounded-3xl border-2 border-dashed p-5 sm:p-10 text-center transition-colors ${
                  isDragging
                    ? 'border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/30'
                    : 'border-stone-300 dark:border-stone-700 bg-[#FAF8F5] dark:bg-[#151F1A]'
                }`}
              >
                <span className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-lime-100 text-[#14532D] dark:bg-emerald-950 dark:text-emerald-300">
                  <CloudUpload className="h-8 w-8" />
                </span>

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
                    className="inline-flex min-h-11 items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50"
                  >
                    <FileImage className="w-3.5 h-3.5" />
                    <span>{t('uploadImage')}</span>
                  </button>

                  <button
                    type="button"
                    disabled={analyzing}
                    onClick={() => {
                      setErrorMsg(null);
                      void openCamera();
                    }}
                    className="inline-flex min-h-11 items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-emerald-900 dark:text-emerald-300 border border-emerald-800 dark:border-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 rounded-lg disabled:opacity-50"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span>{t('captureWithCamera')}</span>
                  </button>
                </div>

                <p className="mt-4 text-[11px] text-stone-500 dark:text-stone-400">
                  {t('uploadDropHint')}
                </p>

                <p className="mt-2 text-[11px] text-stone-500 dark:text-stone-400">
                  {t('dragDropImageHint')}
                </p>
                <p className="mt-2 text-[11px] text-stone-500 dark:text-stone-400">
                  {t('imagePrivacyNote')}
                </p>
              </div>
            ) : (
              <div className="overflow-hidden rounded-3xl border border-stone-200 bg-stone-950 dark:border-stone-800">
                <div className="relative aspect-[4/3] max-h-[360px] w-full flex items-center justify-center">
                  {previewUrl && (
                    <img
                      src={previewUrl}
                      alt={t('selectedMaizeImage')}
                      className="max-h-[360px] max-w-full object-contain"
                      onError={() => {
                        setImageValidationStatus('invalid');
                        setErrorMsg(t('imageUnreadable'));
                      }}
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
                      className="inline-flex min-h-11 items-center rounded-xl px-3 text-xs font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50 dark:text-stone-200 dark:hover:bg-stone-800"
                    >
                      {t('replaceImage')}
                    </button>

                    <button
                      type="button"
                      disabled={analyzing}
                      onClick={() => {
                        setErrorMsg(null);
                        void openCamera();
                      }}
                      className="inline-flex min-h-11 items-center gap-1.5 rounded-xl px-3 text-xs font-medium text-emerald-800 hover:bg-emerald-50 disabled:opacity-50 dark:text-emerald-300 dark:hover:bg-emerald-950/30"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      {t('retakeImage')}
                    </button>

                    <button
                      type="button"
                      disabled={analyzing}
                      onClick={handleRemoveImage}
                      className="inline-flex min-h-11 items-center rounded-xl px-3 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/30"
                    >
                      {t('removeImage')}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {imageValidationStatus === 'checking' && (
              <p className="flex items-center gap-2 text-sm text-emerald-800 dark:text-emerald-300" role="status" aria-live="polite">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('imageValidating')}
              </p>
            )}
            {imageValidationStatus === 'valid' && (
              <p className="text-sm text-emerald-800 dark:text-emerald-300" role="status" aria-live="polite">
                {t('imageValidated')}
              </p>
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
                <p>{t('diagnosisSlowWarning')}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={!selectedFile || imageValidationStatus === 'invalid' || analyzing || localAnalyzing}
              className="w-full inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#14532D] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0f4324] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {analyzing || localAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t({
                    validating: 'imageValidating',
                    checking: 'checkingConnection',
                    online: 'onlineDiagnosisInProgress',
                    offline: 'offlineDiagnosisInProgress',
                    completed: 'diagnosisCompleted',
                    pending: 'savedLocallyWaiting',
                    idle: 'checkingConnection',
                  }[diagnosisStatus])}
                </>
              ) : (
                <>
                  <ScanLine className="w-4 h-4" />
                  {t('diagnoseMaizeLeaf')}
                </>
              )}
            </button>

            {localResult && (
              <section className="farmer-card bg-emerald-50/70 p-5 dark:border-emerald-900 dark:bg-emerald-950/20" aria-live="polite">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">{t('localResultTitle')}</p>
                    <h2 className="mt-1 text-xl font-bold text-stone-900 dark:text-stone-100">
                      {t(localResult.className === 'Northern Leaf Blight' ? 'aboutDiseaseNlb' : localResult.className === 'Common Rust' ? 'aboutDiseaseRust' : localResult.className === 'Gray Leaf Spot' ? 'aboutDiseaseGray' : 'aboutDiseaseHealthy')}
                    </h2>
                    <p className="mt-1 text-sm text-stone-700 dark:text-stone-300">{t('confidenceLabel')}: {(localResult.confidence * 100).toFixed(2)}%</p>
                  </div>
                  <span className="rounded-full bg-amber-100 dark:bg-amber-900/50 px-3 py-1 text-xs font-semibold text-amber-900 dark:text-amber-200">
                    {t(diagnosisStatus === 'completed' ? 'syncCompleted' : 'savedLocallyWaiting')}
                  </span>
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
        <div className="min-w-0 space-y-5 lg:col-span-5 lg:space-y-6">
          <section className="farmer-card p-5 sm:p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-emerald-700 dark:text-emerald-400" />
              <h2 className="font-semibold text-stone-900 dark:text-stone-100">
                {t('imageCaptureTipsTitle')}
              </h2>
            </div>

            <ul className="space-y-3 text-sm text-stone-600 dark:text-stone-300">
              <li>• {t('imageCaptureTipLeaf')}</li>
              <li>• {t('imageCaptureTipFocus')}</li>
              <li>• {t('imageCaptureTipLight')}</li>
              <li>• {t('imageCaptureTipFrame')}</li>
              <li>• {t('imageCaptureTipFormat')}</li>
            </ul>
          </section>

          <section className="farmer-card p-5 sm:p-6">
            <div className="flex items-center gap-2">
              <WifiOff className="w-5 h-5 text-emerald-700 dark:text-emerald-400" />
              <h2 className="font-semibold text-stone-900 dark:text-stone-100">
                {t('offlineSyncQueueTitle')}
              </h2>
            </div>
            <p className="mt-2 text-xs text-stone-600 dark:text-stone-400">
              {t('pendingDiagnosesLabel')}: {offlineRecords.filter((record) => record.sync_status === 'pending').length}
              {' · '}
              {t('synchronizedDiagnosesCount')}: {offlineRecords.filter((record) => record.sync_status === 'synced').length}
            </p>

            {queueError && (
              <p role="alert" className="mt-3 text-xs text-red-700 dark:text-red-300">
                {queueError}
              </p>
            )}

            {offlineRecords.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle2 className="w-8 h-8 mx-auto text-stone-300 dark:text-stone-600 mb-2" />
                <p className="text-sm text-stone-500 dark:text-stone-400">
                  {t('noOfflineDiagnoses')}
                </p>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {offlineRecords.slice(0, 5).map((record) => (
                  <div
                    key={record.operation_id}
                    className="rounded-lg border border-stone-200 dark:border-stone-800 p-3"
                  >
                    <p className="text-sm font-medium text-stone-900 dark:text-stone-100 break-words">
                      {record.file_name || t('diagnoseMaizeLeaf')}
                    </p>
                    <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">
                      {formatDateTime(record.created_at)}
                    </p>
                    <p className="mt-2 text-xs text-stone-700 dark:text-stone-300">
                      {t(
                        record.className === 'Northern Leaf Blight'
                          ? 'aboutDiseaseNlb'
                          : record.className === 'Common Rust'
                            ? 'aboutDiseaseRust'
                            : record.className === 'Gray Leaf Spot'
                              ? 'aboutDiseaseGray'
                              : 'aboutDiseaseHealthy',
                      )}{' '}
                      · {t('confidenceLabel')}: {(record.confidence * 100).toFixed(2)}%
                    </p>
                    <p className="mt-1 text-xs font-medium text-stone-600 dark:text-stone-400">
                      {t(record.sync_status === 'synced' ? 'syncCompleted' : 'savedLocallyWaiting')}
                    </p>
                    {record.sync_error && record.sync_status === 'pending' && (
                      <p className="mt-1 text-xs text-amber-800 dark:text-amber-300">
                        {t('syncFailedWillRetry')}: {record.sync_error}
                      </p>
                    )}
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
