import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Layers, Trash2 } from 'lucide-react';
import {
  ConfirmDialog,
  ErrorState,
  LoadingSkeleton,
} from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { diagnosisService } from '../services/diagnosisService';
import { DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime, resolveMediaUrl } from '../utils/media';

export const DiagnosisDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { t, notify } = useApp();
  const navigate = useNavigate();

  const [item, setItem] = useState<DiagnosisHistoryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [heatmapError, setHeatmapError] = useState(false);
  const [imageError, setImageError] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await diagnosisService.getHistoryDetail(id);
      setItem(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load diagnosis detail from server.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleDelete = async () => {
    if (!id) return;
    setDeleting(true);
    try {
      await diagnosisService.deleteHistoryItem(id);
      notify(`Diagnosis record #${id} deleted.`, 'success');
      navigate('/farmer/history');
    } catch (err: any) {
      notify(err?.message || 'Failed to delete diagnosis record.', 'error');
      setDeleting(false);
      setConfirmDeleteOpen(false);
    }
  };

  const imageUrl = resolveMediaUrl(item?.image_url);
  const heatmapUrl = resolveMediaUrl(item?.heatmap_url);

  return (
    <AppShell
      title={`Diagnosis Record ${id ? `#${id}` : ''}`}
      subtitle="Detailed view of historical maize leaf classification, Grad-CAM explainability, and saved advisory."
      actions={
        <div className="flex items-center gap-2">
          <Link
            to="/farmer/history"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>{t('back')}</span>
          </Link>
          {item && (
            <button
              type="button"
              onClick={() => setConfirmDeleteOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{t('delete')}</span>
            </button>
          )}
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error || !item ? (
        <ErrorState
          title="Could not load diagnosis detail"
          message={error || 'Diagnosis record not found.'}
          onRetry={loadDetail}
        />
      ) : (
        <div className="space-y-8">
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400 font-mono tabular-nums">
                  <span>Record #{item.diagnosis_id ?? item.id}</span>
                  <span aria-hidden="true">·</span>
                  <span>{formatDateTime(item.created_at)}</span>
                  {item.model_name && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{item.model_name}</span>
                    </>
                  )}
                </div>
                <h2 className="mt-2 text-2xl font-bold text-stone-900 dark:text-stone-100 font-display">
                  {item.disease_class || item.class_name}
                </h2>
              </div>
              <div className="text-right">
                <span className="text-xs text-stone-500 block">Confidence</span>
                <span className="text-2xl font-bold font-mono tabular-nums text-emerald-800 dark:text-emerald-400">
                  {formatConfidence(item.confidence)}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
              <div className="px-5 py-3 border-b border-stone-200 dark:border-stone-800 text-xs font-semibold">
                Leaf Photograph
              </div>
              <div className="bg-stone-950 min-h-[260px] flex items-center justify-center p-4">
                {imageUrl && !imageError ? (
                  <img
                    src={imageUrl}
                    alt="Diagnosed maize leaf"
                    referrerPolicy="no-referrer"
                    onError={() => setImageError(true)}
                    className="max-h-[300px] w-auto object-contain rounded"
                  />
                ) : (
                  <p className="text-xs text-stone-400">Public leaf image URL not available for this record.</p>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
              <div className="px-5 py-3 border-b border-stone-200 dark:border-stone-800 flex items-center gap-2 text-xs font-semibold">
                <Layers className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
                <span>Grad-CAM Heatmap</span>
              </div>
              <div className="bg-stone-950 min-h-[260px] flex items-center justify-center p-4">
                {heatmapUrl && !heatmapError ? (
                  <img
                    src={heatmapUrl}
                    alt="Grad-CAM heatmap"
                    referrerPolicy="no-referrer"
                    onError={() => setHeatmapError(true)}
                    className="max-h-[300px] w-auto object-contain rounded"
                  />
                ) : (
                  <p className="text-xs text-stone-400">Visual explanation is unavailable for this record.</p>
                )}
              </div>
            </div>
          </div>

          {item.advisory && (
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-4">
              <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                {item.advisory.heading || item.advisory.title || 'Associated Agronomic Advisory'}
              </h3>
              {item.advisory.description && (
                <p className="text-sm text-stone-700 dark:text-stone-300 leading-relaxed whitespace-pre-line">
                  {item.advisory.description}
                </p>
              )}
              {item.advisory.treatment && (
                <div className="pt-3 border-t border-stone-200 dark:border-stone-800">
                  <h4 className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 mb-1">
                    Treatment
                  </h4>
                  <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    {Array.isArray(item.advisory.treatment)
                      ? item.advisory.treatment.join('\n')
                      : item.advisory.treatment}
                  </p>
                </div>
              )}
              {item.advisory.prevention && (
                <div className="pt-3 border-t border-stone-200 dark:border-stone-800">
                  <h4 className="text-xs font-semibold text-amber-800 dark:text-amber-400 mb-1">
                    Prevention
                  </h4>
                  <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    {Array.isArray(item.advisory.prevention)
                      ? item.advisory.prevention.join('\n')
                      : item.advisory.prevention}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmDeleteOpen}
        title="Delete Diagnosis Record"
        description={`Are you sure you want to delete diagnosis record #${id}?`}
        confirmLabel={t('delete')}
        cancelLabel={t('cancel')}
        variant="danger"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </AppShell>
  );
};
