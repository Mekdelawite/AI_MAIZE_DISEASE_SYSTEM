
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { RefreshCw, ScanLine, Trash2 } from 'lucide-react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { apiDownloadBlob } from '../services/api';
import { diagnosisService } from '../services/diagnosisService';
import {
  offlineDiagnosisStore,
  type OfflineDiagnosisRecord,
} from '../services/offlineDiagnosisStore';
import { DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime } from '../utils/media';

type HistoryRow = {
  key: string;
  recordId: string | number;
  disease: string;
  confidence: number;
  createdAt: string;
  modelName: string;
  imageUrl?: string;
  localImage?: Blob;
  pending: boolean;
  serverItem?: DiagnosisHistoryItem;
};

const HistoryImage: React.FC<{
  imageUrl?: string;
  localImage?: Blob;
}> = ({ imageUrl, localImage }) => {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    setSrc(null);
    setFailed(false);

    if (localImage) {
      objectUrl = URL.createObjectURL(localImage);
      setSrc(objectUrl);
    } else if (imageUrl) {
      apiDownloadBlob(imageUrl)
        .then(({ blob }) => {
          objectUrl = URL.createObjectURL(blob);
          if (cancelled) {
            URL.revokeObjectURL(objectUrl);
          } else {
            setSrc(objectUrl);
          }
        })
        .catch(() => {
          if (!cancelled) setFailed(true);
        });
    } else {
      setFailed(true);
    }

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [imageUrl, localImage]);

  return src && !failed ? (
    <img
      src={src}
      alt="Uploaded maize leaf"
      loading="lazy"
      className="h-12 w-14 rounded-md object-cover bg-stone-900"
    />
  ) : (
    <div
      className="h-12 w-14 rounded-md bg-stone-100 dark:bg-stone-800"
      aria-label="Leaf image unavailable"
    />
  );
};

export const DiagnosisHistoryPage: React.FC = () => {
  const { t, notify } = useApp();
  const { user } = useAuth();
  const userId = user?.id;
  const navigate = useNavigate();

  const [items, setItems] = useState<HistoryRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTargetId, setDeleteTargetId] =
    useState<string | number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);

    let serverRows: HistoryRow[] = [];
    let serverError: unknown = null;

    try {
      const data = await diagnosisService.getHistoryWithCount(20);

      serverRows = data.items.map((item, index) => {
        const id = item.diagnosis_id ?? item.id ?? `server-${index}`;

        return {
          key: `server-${String(id)}`,
          recordId: id,
          disease: item.disease_class || item.class_name || 'Unknown',
          confidence: Number(item.confidence ?? 0),
          createdAt: item.created_at ?? '',
          modelName: item.model_name || item.model_version || 'MobileNetV2',
          imageUrl: item.image_url,
          pending: false,
          serverItem: item,
        };
      });
    } catch (err) {
      serverError = err;
    }

    let localRows: HistoryRow[] = [];

    try {
      const localRecords: OfflineDiagnosisRecord[] = userId === undefined
        ? []
        : await offlineDiagnosisStore.getAll(userId);

      localRows = localRecords.map((record) => ({
        key: `local-${record.operation_id}`,
        recordId: record.operation_id,
        disease: record.className,
        confidence: record.confidence,
        createdAt: record.created_at,
        modelName: 'MobileNetV2 (Offline)',
        localImage: record.image,
        pending: record.sync_status === 'pending',
      }));
    } catch (err) {
      console.error('Could not load local diagnosis history:', err);
    }

    // A successfully synced local diagnosis may also exist on the server.
    // Hide the local copy when the server already contains the same result.
    const serverSignatures = new Set(
      serverRows.map(
        (row) =>
          `${row.disease}|${row.createdAt}|${row.confidence.toFixed(5)}`,
      ),
    );

    const uniqueLocalRows = localRows.filter(
      (row) =>
        row.pending ||
        !serverSignatures.has(
          `${row.disease}|${row.createdAt}|${row.confidence.toFixed(5)}`,
        ),
    );

    const combined = [...serverRows, ...uniqueLocalRows].sort(
      (a, b) =>
        new Date(b.createdAt).getTime() -
        new Date(a.createdAt).getTime(),
    );

    setItems(combined);
    setTotalCount(combined.length);

    if (serverError && combined.length === 0) {
      setError(
        serverError instanceof Error
          ? serverError.message
          : 'Unable to load diagnosis history.',
      );
    }

    setLoading(false);
  }, [userId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleConfirmDelete = async () => {
    if (deleteTargetId === null) return;

    const target = items.find(
      (item) => item.recordId === deleteTargetId,
    );

    if (!target || target.pending || !target.serverItem) {
      notify(
        'This is a locally saved diagnosis. Local deletion is not enabled yet.',
        'error',
      );
      setDeleteTargetId(null);
      return;
    }

    setDeleting(true);

    try {
      await diagnosisService.deleteHistoryItem(deleteTargetId);

      setItems((prev) =>
        prev.filter((item) => item.key !== target.key),
      );
      setTotalCount((prev) => Math.max(0, prev - 1));
      notify(`Diagnosis record #${deleteTargetId} deleted on server.`, 'success');
      setDeleteTargetId(null);
    } catch (err: any) {
      notify(err?.message || 'Failed to delete diagnosis record.', 'error');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AppShell
      title={t('navHistory')}
      subtitle="View saved maize leaf classifications, Grad-CAM heatmaps, and associated treatment advisories."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadHistory()}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>

          <Link
            to="/farmer/diagnose"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg whitespace-nowrap"
          >
            <ScanLine className="w-3.5 h-3.5" />
            <span>{t('diagnoseLeaf')}</span>
          </Link>
        </div>
      }
    >
      {!loading && !error && (
        <p
          className="mb-4 text-sm text-stone-600 dark:text-stone-300"
          aria-live="polite"
        >
          {totalCount} saved diagnosis {totalCount === 1 ? 'record' : 'records'}
          {' · '}
          {items.filter((item) => item.pending).length} pending sync
        </p>
      )}

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState
          title="Could not load diagnosis history"
          message={error}
          onRetry={() => void loadHistory()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="No saved diagnosis records found"
          description="Your completed online and offline maize leaf diagnoses will appear here."
          actionLabel={t('diagnoseLeaf')}
          onAction={() => navigate('/farmer/diagnose')}
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 dark:text-stone-400 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">Leaf</th>
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Disease / Classification</th>
                  <th className="py-3 px-4 text-right">Confidence</th>
                  <th className="py-3 px-4">Model</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Sync status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-stone-200 dark:divide-stone-800 text-sm">
                {items.map((item, index) => (
                  <tr
                    key={item.key}
                    role={item.serverItem ? 'link' : undefined}
                    tabIndex={item.serverItem ? 0 : undefined}
                    aria-label={
                      item.serverItem
                        ? `View diagnosis record ${item.recordId}`
                        : undefined
                    }
                    onClick={(event) => {
                      if (
                        item.serverItem &&
                        !(event.target as HTMLElement).closest('a, button')
                      ) {
                        navigate(`/farmer/history/${item.recordId}`);
                      }
                    }}
                    onKeyDown={(event) => {
                      if (
                        item.serverItem &&
                        event.target === event.currentTarget &&
                        event.key === 'Enter'
                      ) {
                        navigate(`/farmer/history/${item.recordId}`);
                      }
                    }}
                    className={`hover:bg-stone-50/80 dark:hover:bg-stone-800/40 transition-colors ${item.serverItem ? 'cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700' : ''}`}
                  >
                    <td className="py-2 px-4">
                      <HistoryImage
                        imageUrl={item.imageUrl}
                        localImage={item.localImage}
                      />
                    </td>

                    <td className="py-3.5 px-4 font-mono tabular-nums text-xs text-stone-500">
                      {item.pending
                        ? `Local ${index + 1}`
                        : `#${item.recordId}`}
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-stone-900 dark:text-stone-100">
                      {item.disease}
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono tabular-nums text-emerald-800 dark:text-emerald-400 font-medium">
                      {formatConfidence(item.confidence)}
                    </td>

                    <td className="py-3.5 px-4 text-xs text-stone-600 dark:text-stone-400">
                      {item.modelName}
                    </td>

                    <td className="py-3.5 px-4 text-xs font-mono tabular-nums text-stone-600 dark:text-stone-400">
                      {formatDateTime(item.createdAt)}
                    </td>

                    <td className="py-3.5 px-4">
                      {item.pending ? (
                        <span className="inline-flex rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                          Pending sync
                        </span>
                      ) : (
                        <span className="text-xs text-emerald-700 dark:text-emerald-400">
                          Available
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      {item.serverItem && (
                        <div className="inline-flex items-center gap-3">
                          <Link
                            to={`/farmer/history/${item.recordId}`}
                            className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 hover:underline whitespace-nowrap"
                          >
                            {t('viewDetails')}
                          </Link>

                          <button
                            type="button"
                            onClick={() => setDeleteTargetId(item.recordId)}
                            className="text-stone-400 hover:text-red-600 dark:hover:text-red-400 cursor-pointer"
                            aria-label={`Delete diagnosis record ${item.recordId}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}

                      {item.pending && (
                        <span className="text-xs text-stone-500">
                          Saved on device
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={deleteTargetId !== null}
        title="Delete Diagnosis Record"
        description={`Are you sure you want to permanently delete diagnosis record #${deleteTargetId} from the server?`}
        confirmLabel={t('delete')}
        cancelLabel={t('cancel')}
        variant="danger"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />
    </AppShell>
  );
};
