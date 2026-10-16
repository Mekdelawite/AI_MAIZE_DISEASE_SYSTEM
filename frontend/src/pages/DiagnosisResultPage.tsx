import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, History, Layers, ScanLine, ShieldAlert } from 'lucide-react';
import { EmptyState } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { CompleteDiagnosisResponse } from '../types/api';
import { formatConfidence, formatDateTime, normalizeConfidencePercent, resolveMediaUrl } from '../utils/media';

function renderListOrText(value?: string | string[] | null): React.ReactNode {
  if (!value) return null;
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    return (
      <ul className="space-y-1.5 text-sm text-stone-700 dark:text-stone-300 list-disc pl-5">
        {value.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    );
  }
  return <p className="text-sm text-stone-700 dark:text-stone-300 leading-relaxed whitespace-pre-line">{value}</p>;
}

export const DiagnosisResultPage: React.FC = () => {
  const { t } = useApp();
  const location = useLocation();
  const navigate = useNavigate();

  const state = (location.state as {
    result?: CompleteDiagnosisResponse;
    uploadedPreviewUrl?: string;
  }) || {};

  const result = state.result;
  const [heatmapImgError, setHeatmapImgError] = useState(false);

  if (!result || !result.diagnosis) {
    return (
      <AppShell title="Diagnosis Result" subtitle="Review AI classification, Grad-CAM explainability, and advisory.">
        <EmptyState
          title="No active diagnosis result in session"
          description="Submit a maize leaf image on the Diagnose page or select a saved record from Diagnosis History."
          actionLabel={t('diagnoseLeaf')}
          onAction={() => navigate('/farmer/diagnose')}
        />
      </AppShell>
    );
  }

  const { diagnosis, advisory, database } = result;
  const prediction = diagnosis.prediction || { class_name: 'Unknown', confidence: 0 };
  const confidencePercent = normalizeConfidencePercent(prediction.confidence);
  const savedDiagnosisId = database?.diagnosis_id ?? diagnosis.database_id;

  const overlayPath = diagnosis.explainability?.overlay || diagnosis.overlay;
  const overlayFilename = overlayPath?.split(/[\\/]/).pop();
  const resolvedHeatmapUrl = diagnosis.explainability?.overlay_url || diagnosis.overlay_url
    ? resolveMediaUrl(diagnosis.explainability?.overlay_url || diagnosis.overlay_url)
    : resolveMediaUrl(
        null,
        overlayFilename ||
          diagnosis.explainability?.overlay_filename ||
          diagnosis.explainability?.heatmap_filename
      ) || resolveMediaUrl(diagnosis.explainability?.heatmap_url || diagnosis.heatmap_url);

  const resolvedOriginalImageUrl =
    state.uploadedPreviewUrl || resolveMediaUrl(diagnosis.image_url);

  const treatmentContent = advisory?.management || advisory?.treatment || advisory?.treatments || advisory?.recommendations;
  const preventionContent = advisory?.prevention || advisory?.preventions;
  const outbreakStatus = diagnosis.outbreak_status || diagnosis.outbreak;

  return (
    <AppShell
      title="Maize Leaf Diagnosis Result"
      subtitle="MobileNetV2 classification output, Grad-CAM visual attention heatmap, and server-generated agronomic advisory."
      actions={
        <div className="flex items-center gap-2">
          <Link
            to="/farmer/history"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 whitespace-nowrap"
          >
            <History className="w-3.5 h-3.5" />
            <span>{t('navHistory')}</span>
          </Link>
          <Link
            to="/farmer/diagnose"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg whitespace-nowrap"
          >
            <ScanLine className="w-3.5 h-3.5" />
            <span>New Diagnosis</span>
          </Link>
        </div>
      }
    >
      <div className="space-y-8">
        {/* Top Summary Card */}
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
                <span>Detected Class</span>
                {savedDiagnosisId !== undefined && (
                  <>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono tabular-nums">Record ID: #{savedDiagnosisId}</span>
                  </>
                )}
                {prediction.model_name && (
                  <>
                    <span aria-hidden="true">·</span>
                    <span>Model: {prediction.model_name}</span>
                  </>
                )}
                {prediction.model_version && (
                  <>
                    <span aria-hidden="true">|</span>
                    <span>Version: {prediction.model_version}</span>
                  </>
                )}
                {diagnosis.created_at && (
                  <>
                    <span aria-hidden="true">Â·</span>
                    <span>{formatDateTime(diagnosis.created_at)}</span>
                  </>
                )}
                {(prediction.prediction_time_ms !== undefined || prediction.inference_time !== undefined) && (
                  <>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono tabular-nums">
                      Inference: {prediction.prediction_time_ms ?? prediction.inference_time} ms
                    </span>
                  </>
                )}
              </div>

              <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-stone-900 dark:text-stone-100 font-display">
                {prediction.class_name}
              </h2>
            </div>

            <div className="md:text-right min-w-[220px]">
              <div className="flex items-baseline md:justify-end gap-2">
                <span className="text-xs text-stone-500 dark:text-stone-400">Model Confidence:</span>
                <span className="text-2xl font-bold font-mono tabular-nums text-emerald-800 dark:text-emerald-400">
                  {formatConfidence(prediction.confidence)}
                </span>
              </div>
              <div className="mt-2 h-2 w-full bg-stone-200 dark:bg-stone-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-700 dark:bg-emerald-500 transition-all"
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-stone-200/70 dark:border-stone-800 flex items-start gap-2.5 text-xs text-stone-600 dark:text-stone-400">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p>{t('confidenceDisclaimer')}</p>
          </div>

          {outbreakStatus && (
            <div className="mt-4 rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/60 dark:bg-amber-950/20 p-3.5 flex items-start gap-2.5 text-xs text-amber-900 dark:text-amber-200">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Regional Outbreak Monitor: </span>
                <span>
                  {outbreakStatus.message ||
                    (outbreakStatus.alert_triggered
                      ? `Outbreak threshold triggered (${outbreakStatus.risk_level || 'active'}).`
                      : outbreakStatus.status
                        ? `Outbreak evaluation ${outbreakStatus.status}.`
                        : 'Evaluated against regional threshold.')}
                </span>
              </div>
            </div>
          )}

          {prediction.probabilities && Object.keys(prediction.probabilities).length > 0 && (
            <div className="mt-5 border-t border-stone-200/70 pt-4 dark:border-stone-800">
              <h3 className="mb-3 text-xs font-semibold text-stone-600 dark:text-stone-300">
                Class probability scores
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(prediction.probabilities).map(([className, confidence]) => (
                  <div key={className} className="flex items-center justify-between gap-3 text-xs">
                    <span className="text-stone-700 dark:text-stone-300">{className}</span>
                    <span className="font-mono tabular-nums text-stone-500 dark:text-stone-400">
                      {formatConfidence(confidence)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Visual Comparison: Uploaded Leaf vs Grad-CAM Explainability Heatmap */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden flex flex-col">
            <div className="px-5 py-3.5 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between">
              <h3 className="text-sm font-bold text-stone-900 dark:text-stone-100 font-display">
                Submitted Maize Leaf Image
              </h3>
              <span className="text-xs text-stone-500">Original Input</span>
            </div>
            <div className="flex-1 bg-stone-950 min-h-[280px] flex items-center justify-center p-4">
              {resolvedOriginalImageUrl ? (
                <img
                  src={resolvedOriginalImageUrl}
                  alt="Uploaded maize leaf"
                  referrerPolicy="no-referrer"
                  className="max-h-[320px] w-auto object-contain rounded"
                />
              ) : (
                <p className="text-xs text-stone-400">Original image preview unavailable.</p>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden flex flex-col">
            <div className="px-5 py-3.5 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
                <h3 className="text-sm font-bold text-stone-900 dark:text-stone-100 font-display">
                  Grad-CAM Overlay Heatmap
                </h3>
              </div>
              <span className="text-xs text-stone-500 font-mono">
                  {diagnosis.explainability?.method || 'Overlay'}
              </span>
            </div>
            <div className="flex-1 bg-stone-950 min-h-[280px] flex items-center justify-center p-4">
              {resolvedHeatmapUrl && !heatmapImgError ? (
                <img
                  src={resolvedHeatmapUrl}
                    alt="Grad-CAM overlay highlighting the image regions that influenced the diagnosis"
                  referrerPolicy="no-referrer"
                  onError={() => setHeatmapImgError(true)}
                  className="max-h-[320px] w-auto object-contain rounded"
                />
              ) : (
                <div className="text-center max-w-xs p-6">
                  <p className="text-xs text-stone-300 font-medium">
                    Grad-CAM overlay is unavailable for this result.
                  </p>
                  <p className="mt-1 text-xs text-stone-500">
                    {diagnosis.explainability?.message ||
                      'Grad-CAM may not have been requested, or the backend did not return an overlay image.'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Agronomic Advisory Section */}
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-200 dark:border-stone-800 pb-4">
            <div>
              <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                {advisory?.heading || advisory?.title || `Agronomic Advisory: ${advisory?.disease || prediction.class_name}`}
              </h3>
              {advisory?.disease && (
                <p className="mt-1 text-sm text-stone-700 dark:text-stone-300">
                  Disease: {advisory.disease}
                </p>
              )}
              {advisory?.scientific_name && (
                <p className="mt-1 text-sm italic text-stone-600 dark:text-stone-400">
                  {advisory.scientific_name}
                </p>
              )}
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                {advisory?.severity && (
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                    Severity: {advisory.severity}
                  </span>
                )}
                {advisory?.confidence != null && (
                  <span className="rounded-full bg-emerald-100 px-2.5 py-1 font-medium text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
                    Advisory confidence: {formatConfidence(advisory.confidence)}
                  </span>
                )}
                {advisory?.language && (
                  <span className="rounded-full bg-stone-100 px-2.5 py-1 text-stone-700 dark:bg-stone-800 dark:text-stone-300">
                    Language: {advisory.language === 'am' ? 'Amharic' : 'English'}
                  </span>
                )}
              </div>
              {advisory?.source && (
                <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">
                  Advisory Source: {advisory.source}
                </p>
              )}
              {advisory?.created_at && (
                <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">
                  Generated: {formatDateTime(advisory.created_at)}
                </p>
              )}
            </div>
            {database?.advisory_id !== undefined && (
              <span className="text-xs font-mono text-stone-500">Advisory ID: #{database.advisory_id}</span>
            )}
          </div>

          {!advisory ? (
            <p className="text-sm text-stone-600 dark:text-stone-400">
              No advisory payload was returned by the server for this classification.
            </p>
          ) : (
            <div className="space-y-6">
              {advisory.description && (
                <div>
                  <h4 className="text-xs font-semibold text-stone-500 dark:text-stone-400 mb-2">
                    Condition Overview
                  </h4>
                  <p className="text-sm text-stone-800 dark:text-stone-200 leading-relaxed whitespace-pre-line">
                    {advisory.description}
                  </p>
                </div>
              )}

              {advisory.advisory_text && !advisory.description && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold text-stone-500 dark:text-stone-400">
                    Advisory
                  </h4>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-stone-800 dark:text-stone-200">
                    {advisory.advisory_text}
                  </p>
                </div>
              )}

              {renderListOrText(advisory.symptoms) && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold text-stone-500 dark:text-stone-400">Symptoms</h4>
                  {renderListOrText(advisory.symptoms)}
                </div>
              )}

              {renderListOrText(advisory.causes) && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold text-stone-500 dark:text-stone-400">Causes</h4>
                  {renderListOrText(advisory.causes)}
                </div>
              )}

              {renderListOrText(advisory.favorable_conditions) && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold text-stone-500 dark:text-stone-400">Favorable Conditions</h4>
                  {renderListOrText(advisory.favorable_conditions)}
                </div>
              )}

              {treatmentContent && (
                <div className="pt-4 border-t border-stone-200/70 dark:border-stone-800">
                  <h4 className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 mb-2">
                    Treatment & Management Recommendations
                  </h4>
                  {renderListOrText(treatmentContent)}
                </div>
              )}

              {preventionContent && (
                <div className="pt-4 border-t border-stone-200/70 dark:border-stone-800">
                  <h4 className="text-xs font-semibold text-amber-800 dark:text-amber-400 mb-2">
                    Prevention Guidance
                  </h4>
                  {renderListOrText(preventionContent)}
                </div>
              )}

              {advisory.sources && advisory.sources.length > 0 && (
                <div className="border-t border-stone-200/70 pt-4 dark:border-stone-800">
                  <h4 className="mb-2 text-xs font-semibold text-stone-600 dark:text-stone-300">
                    Sources
                  </h4>
                  <ul className="space-y-2">
                    {advisory.sources.map((source, index) => (
                      <li key={`${source.title || 'source'}-${index}`} className="text-sm text-stone-700 dark:text-stone-300">
                        {source.url ? (
                          <a href={source.url} target="_blank" rel="noreferrer" className="font-medium text-emerald-800 underline dark:text-emerald-300">
                            {source.title || source.organization || source.url}
                          </a>
                        ) : (
                          <span className="font-medium">{source.title || source.organization || `Source ${index + 1}`}</span>
                        )}
                        {(source.organization || source.year || source.source_type) && (
                          <span className="ml-1 text-xs text-stone-500 dark:text-stone-400">
                            {[source.organization, source.year, source.source_type].filter(Boolean).join(' · ')}
                          </span>
                        )}
                        {source.notes && <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">{source.notes}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {advisory.validation && Object.keys(advisory.validation).length > 0 && (
                <details className="border-t border-stone-200/70 pt-4 dark:border-stone-800">
                  <summary className="cursor-pointer text-xs font-semibold text-stone-600 dark:text-stone-300">
                    Advisory validation details
                  </summary>
                  <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                    {Object.entries(advisory.validation).map(([key, value]) => (
                      <div key={key} className="rounded-lg bg-stone-50 p-3 dark:bg-stone-900/50">
                        <dt className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">{key.replaceAll('_', ' ')}</dt>
                        <dd className="mt-1 break-words text-xs text-stone-700 dark:text-stone-300">
                          {typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
                            ? String(value)
                            : JSON.stringify(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}

              {advisory.disclaimer && (
                <p className="border-t border-stone-200/70 pt-4 text-xs leading-relaxed text-stone-500 dark:border-stone-800 dark:text-stone-400">
                  {advisory.disclaimer}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between">
          <Link
            to="/farmer/diagnose"
            className="inline-flex items-center gap-2 text-xs font-medium text-stone-700 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Analyze Another Maize Leaf</span>
          </Link>
        </div>
      </div>
    </AppShell>
  );
};
