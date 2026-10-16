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
import { apiDownloadBlob } from '../services/api';
import { DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime, resolveMediaUrl } from '../utils/media';

function renderListOrText(value?: string | string[] | null): React.ReactNode {
  if (!value) return null;
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    return (
      <ul className="list-disc space-y-1 pl-5 text-sm text-stone-700 dark:text-stone-300">
        {value.map((entry, index) => <li key={`${index}-${entry}`}>{entry}</li>)}
      </ul>
    );
  }
  return <p className="whitespace-pre-line text-sm leading-relaxed text-stone-700 dark:text-stone-300">{value}</p>;
}

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
  const [leafImageUrl, setLeafImageUrl] = useState<string | null>(null);

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

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setLeafImageUrl(null);
    setImageError(false);

    if (!item?.image_url) return;

    apiDownloadBlob(item.image_url)
      .then(({ blob }) => {
        objectUrl = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
        } else {
          setLeafImageUrl(objectUrl);
        }
      })
      .catch(() => {
        if (!cancelled) setImageError(true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item?.image_url]);

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
                {leafImageUrl && !imageError ? (
                  <img
                    src={leafImageUrl}
                    alt="Diagnosed maize leaf"
                    referrerPolicy="no-referrer"
                    onError={() => setImageError(true)}
                    className="max-h-[300px] w-auto object-contain rounded"
                  />
                ) : (
                  <p className="text-xs text-stone-400">Original uploaded leaf image is unavailable for this record.</p>
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
                {item.advisory.heading || item.advisory.title || `Agronomic Advisory: ${item.advisory.disease || item.disease_class || item.class_name || 'Diagnosis'}`}
              </h3>
              {item.advisory.scientific_name && (
                <p className="text-sm italic text-stone-600 dark:text-stone-400">{item.advisory.scientific_name}</p>
              )}
              <div className="flex flex-wrap gap-2 text-xs">
                {item.advisory.severity && <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">Severity: {item.advisory.severity}</span>}
                {item.advisory.confidence != null && <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">Advisory confidence: {formatConfidence(item.advisory.confidence)}</span>}
                {item.advisory.language && <span className="rounded-full bg-stone-100 px-2.5 py-1 text-stone-700 dark:bg-stone-800 dark:text-stone-300">Language: {item.advisory.language === 'am' ? 'Amharic' : 'English'}</span>}
              </div>
              {(item.advisory.description || item.advisory.advisory_text) && (
                <p className="text-sm text-stone-700 dark:text-stone-300 leading-relaxed whitespace-pre-line">
                  {item.advisory.description || item.advisory.advisory_text}
                </p>
              )}
              {renderListOrText(item.advisory.symptoms) && (
                <div className="border-t border-stone-200 pt-3 dark:border-stone-800">
                  <h4 className="mb-1 text-xs font-semibold text-stone-600 dark:text-stone-300">Symptoms</h4>
                  {renderListOrText(item.advisory.symptoms)}
                </div>
              )}
              {renderListOrText(item.advisory.causes) && (
                <div className="border-t border-stone-200 pt-3 dark:border-stone-800">
                  <h4 className="mb-1 text-xs font-semibold text-stone-600 dark:text-stone-300">Causes</h4>
                  {renderListOrText(item.advisory.causes)}
                </div>
              )}
              {renderListOrText(item.advisory.favorable_conditions) && (
                <div className="border-t border-stone-200 pt-3 dark:border-stone-800">
                  <h4 className="mb-1 text-xs font-semibold text-stone-600 dark:text-stone-300">Favorable Conditions</h4>
                  {renderListOrText(item.advisory.favorable_conditions)}
                </div>
              )}
              {renderListOrText(item.advisory.management || item.advisory.treatment || item.advisory.treatments || item.advisory.recommendations) && (
                <div className="pt-3 border-t border-stone-200 dark:border-stone-800">
                  <h4 className="mb-1 text-xs font-semibold text-emerald-800 dark:text-emerald-400">Management</h4>
                  {renderListOrText(item.advisory.management || item.advisory.treatment || item.advisory.treatments || item.advisory.recommendations)}
                </div>
              )}
              {renderListOrText(item.advisory.prevention || item.advisory.preventions) && (
                <div className="pt-3 border-t border-stone-200 dark:border-stone-800">
                  <h4 className="mb-1 text-xs font-semibold text-amber-800 dark:text-amber-400">Prevention</h4>
                  {renderListOrText(item.advisory.prevention || item.advisory.preventions)}
                </div>
              )}
              {item.advisory.sources && item.advisory.sources.length > 0 && (
                <div className="border-t border-stone-200 pt-3 dark:border-stone-800">
                  <h4 className="mb-2 text-xs font-semibold text-stone-600 dark:text-stone-300">Sources</h4>
                  <ul className="space-y-2">
                    {item.advisory.sources.map((source, index) => (
                      <li key={`${source.title || 'source'}-${index}`} className="text-sm text-stone-700 dark:text-stone-300">
                        {source.url ? <a href={source.url} target="_blank" rel="noreferrer" className="font-medium text-emerald-800 underline dark:text-emerald-300">{source.title || source.organization || source.url}</a> : <span className="font-medium">{source.title || source.organization || `Source ${index + 1}`}</span>}
                        {(source.organization || source.year || source.source_type) && <span className="ml-1 text-xs text-stone-500">{[source.organization, source.year, source.source_type].filter(Boolean).join(' · ')}</span>}
                        {source.notes && <p className="mt-0.5 text-xs text-stone-500">{source.notes}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {item.advisory.validation && Object.keys(item.advisory.validation).length > 0 && (
                <details className="border-t border-stone-200 pt-3 dark:border-stone-800">
                  <summary className="cursor-pointer text-xs font-semibold text-stone-600 dark:text-stone-300">Advisory validation details</summary>
                  <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                    {Object.entries(item.advisory.validation).map(([key, value]) => (
                      <div key={key} className="rounded-lg bg-stone-50 p-3 dark:bg-stone-900/50">
                        <dt className="text-[11px] font-semibold uppercase text-stone-500">{key.replaceAll('_', ' ')}</dt>
                        <dd className="mt-1 break-words text-xs text-stone-700 dark:text-stone-300">{typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' ? String(value) : JSON.stringify(value)}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
              {item.advisory.disclaimer && <p className="border-t border-stone-200 pt-3 text-xs text-stone-500 dark:border-stone-800 dark:text-stone-400">{item.advisory.disclaimer}</p>}
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
