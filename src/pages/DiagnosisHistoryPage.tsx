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
import { diagnosisService } from '../services/diagnosisService';
import { DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime } from '../utils/media';

export const DiagnosisHistoryPage: React.FC = () => {
  const { t, notify } = useApp();
  const navigate = useNavigate();

  const [items, setItems] = useState<DiagnosisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await diagnosisService.getHistory(20);
      setItems(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load diagnosis history from server.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleConfirmDelete = async () => {
    if (deleteTargetId === null) return;
    setDeleting(true);
    try {
      await diagnosisService.deleteHistoryItem(deleteTargetId);
      setItems((prev) => prev.filter((item) => (item.diagnosis_id ?? item.id) !== deleteTargetId));
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
            onClick={loadHistory}
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
      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState title="Could not load diagnosis history" message={error} onRetry={loadHistory} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No saved diagnosis records found"
          description="Your completed maize leaf diagnoses from POST /api/diagnosis/complete will appear here."
          actionLabel={t('diagnoseLeaf')}
          onAction={() => navigate('/farmer/diagnose')}
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 dark:text-stone-400 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Disease / Classification</th>
                  <th className="py-3 px-4 text-right">Confidence</th>
                  <th className="py-3 px-4">Model</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800 text-sm">
                {items.map((item) => {
                  const recordId = item.diagnosis_id ?? item.id;
                  return (
                    <tr
                      key={String(recordId)}
                      className="hover:bg-stone-50/80 dark:hover:bg-stone-800/40 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono tabular-nums text-xs text-stone-500">
                        #{recordId}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-stone-900 dark:text-stone-100">
                        {item.disease_class || item.class_name || 'Unknown'}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono tabular-nums text-emerald-800 dark:text-emerald-400 font-medium">
                        {formatConfidence(item.confidence)}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-stone-600 dark:text-stone-400">
                        {item.model_name || item.model_version || 'MobileNetV2'}
                      </td>
                      <td className="py-3.5 px-4 text-xs font-mono tabular-nums text-stone-600 dark:text-stone-400">
                        {formatDateTime(item.created_at)}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="inline-flex items-center gap-3">
                          <Link
                            to={`/farmer/history/${recordId}`}
                            className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 hover:underline whitespace-nowrap"
                          >
                            {t('viewDetails')}
                          </Link>
                          <button
                            type="button"
                            onClick={() => setDeleteTargetId(recordId)}
                            className="text-stone-400 hover:text-red-600 dark:hover:text-red-400 cursor-pointer"
                            aria-label={`Delete diagnosis record ${recordId}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
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
