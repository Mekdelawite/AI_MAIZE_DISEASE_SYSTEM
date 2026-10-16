import React, { useCallback, useEffect, useState } from 'react';
import { Layers, RefreshCw, X } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { extensionService } from '../services/extensionService';
import { DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime, resolveMediaUrl } from '../utils/media';

export const ExtensionCasesPage: React.FC = () => {
  const { t, notify } = useApp();

  const [cases, setCases] = useState<DiagnosisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [diseaseFilter, setDiseaseFilter] = useState('');
  const [woredaFilter, setWoredaFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Selected Case Detail
  const [selectedCase, setSelectedCase] = useState<DiagnosisHistoryItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await extensionService.getDiagnoses({
        disease_class: diseaseFilter.trim() || undefined,
        woreda: woredaFilter.trim() || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setCases(res.items);
    } catch (err: any) {
      setError(err?.message || 'Unable to load assigned diagnosis cases from /api/extension/diagnoses.');
    } finally {
      setLoading(false);
    }
  }, [diseaseFilter, woredaFilter, startDate, endDate]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleSelectCase = async (id: string | number) => {
    setDetailLoading(true);
    try {
      const detail = await extensionService.getDiagnosisDetail(id);
      setSelectedCase(detail);
    } catch (err: any) {
      notify(err?.message || 'Failed to load case detail.', 'error');
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <AppShell
      title={t('navExtCases')}
      subtitle="Inspect farmer maize leaf diagnoses assigned to your region and woreda via GET /api/extension/diagnoses."
      actions={
        <button
          type="button"
          onClick={loadCases}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('refresh')}</span>
        </button>
      }
    >
      {/* Filter Bar */}
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
        <div>
          <label className="block text-xs text-stone-500 mb-1">Disease Class</label>
          <input
            type="text"
            value={diseaseFilter}
            onChange={(e) => setDiseaseFilter(e.target.value)}
            placeholder="e.g. Common_Rust"
            className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div>
          <label className="block text-xs text-stone-500 mb-1">Woreda</label>
          <input
            type="text"
            value={woredaFilter}
            onChange={(e) => setWoredaFilter(e.target.value)}
            placeholder="Filter by woreda"
            className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div>
          <label className="block text-xs text-stone-500 mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div>
          <label className="block text-xs text-stone-500 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadCases}
            className="flex-1 py-1.5 px-3 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer"
          >
            Apply Filters
          </button>
          <button
            type="button"
            onClick={() => {
              setDiseaseFilter('');
              setWoredaFilter('');
              setStartDate('');
              setEndDate('');
            }}
            className="py-1.5 px-2.5 text-xs text-stone-600 dark:text-stone-400 hover:underline cursor-pointer"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className={selectedCase ? 'lg:col-span-7' : 'lg:col-span-12'}>
          {loading ? (
            <LoadingSkeleton rows={5} />
          ) : error ? (
            <ErrorState title="Could not load assigned cases" message={error} onRetry={loadCases} />
          ) : cases.length === 0 ? (
            <EmptyState
              title="No assigned diagnosis cases found"
              description="Cases submitted by farmers within your assigned region and woreda will appear here."
            />
          ) : (
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                      <th className="py-3 px-4">ID</th>
                      <th className="py-3 px-4">Farmer / Location</th>
                      <th className="py-3 px-4">Disease Class</th>
                      <th className="py-3 px-4 text-right">Confidence</th>
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200 dark:divide-stone-800 text-sm">
                    {cases.map((c) => {
                      const caseId = c.diagnosis_id ?? c.id;
                      return (
                        <tr
                          key={String(caseId)}
                          onClick={() => handleSelectCase(caseId)}
                          className="hover:bg-stone-50/80 dark:hover:bg-stone-800/40 transition-colors cursor-pointer"
                        >
                          <td className="py-3 px-4 font-mono tabular-nums text-xs text-stone-500">
                            #{caseId}
                          </td>
                          <td className="py-3 px-4">
                            <p className="font-medium text-stone-900 dark:text-stone-100">
                              {c.farmer_name || c.farmer_phone || 'Assigned Farmer'}
                            </p>
                            <p className="text-xs text-stone-500">
                              {c.region || '—'} {c.woreda ? `· ${c.woreda}` : ''}
                            </p>
                          </td>
                          <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                            {c.disease_class || c.class_name}
                          </td>
                          <td className="py-3 px-4 text-right font-mono tabular-nums text-emerald-800 dark:text-emerald-400">
                            {formatConfidence(c.confidence)}
                          </td>
                          <td className="py-3 px-4 text-xs font-mono tabular-nums text-stone-500">
                            {formatDateTime(c.created_at)}
                          </td>
                          <td className="py-3 px-4 text-right text-xs font-semibold text-emerald-800 dark:text-emerald-400">
                            {t('viewDetails')}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Case Detail Panel */}
        {selectedCase && (
          <div className="lg:col-span-5">
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sticky top-20 space-y-5">
              <div className="flex items-start justify-between gap-2 border-b border-stone-200 dark:border-stone-800 pb-4">
                <div>
                  <span className="text-xs font-mono text-stone-500">
                    Case #{selectedCase.diagnosis_id ?? selectedCase.id} ·{' '}
                    {formatDateTime(selectedCase.created_at)}
                  </span>
                  <h3 className="mt-1 text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                    {selectedCase.disease_class || selectedCase.class_name}
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-400">
                    Confidence:{' '}
                    <span className="font-mono font-semibold text-emerald-800 dark:text-emerald-400">
                      {formatConfidence(selectedCase.confidence)}
                    </span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedCase(null)}
                  className="text-stone-400 hover:text-stone-700 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {detailLoading ? (
                <LoadingSkeleton rows={3} />
              ) : (
                <div className="space-y-4">
                  <div className="text-xs space-y-1 text-stone-600 dark:text-stone-400">
                    <p>
                      <span className="font-semibold text-stone-800 dark:text-stone-200">Farmer: </span>
                      {selectedCase.farmer_name || '—'} ({selectedCase.farmer_phone || 'No phone'})
                    </p>
                    <p>
                      <span className="font-semibold text-stone-800 dark:text-stone-200">Location: </span>
                      {selectedCase.region || '—'} · {selectedCase.woreda || '—'}{' '}
                      {selectedCase.kebele ? `· ${selectedCase.kebele}` : ''}
                    </p>
                  </div>

                  {resolveMediaUrl(selectedCase.heatmap_url) && (
                    <div className="rounded-lg overflow-hidden border border-stone-200 dark:border-stone-800 bg-stone-950 p-3">
                      <div className="flex items-center gap-1.5 text-xs text-stone-300 mb-2">
                        <Layers className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Grad-CAM Visual Explanation</span>
                      </div>
                      <img
                        src={resolveMediaUrl(selectedCase.heatmap_url)!}
                        alt="Case Grad-CAM heatmap"
                        referrerPolicy="no-referrer"
                        className="max-h-48 w-auto mx-auto object-contain rounded"
                      />
                    </div>
                  )}

                  {selectedCase.advisory?.description && (
                    <div className="pt-3 border-t border-stone-200 dark:border-stone-800">
                      <h4 className="text-xs font-semibold text-stone-500 mb-1">Generated Advisory</h4>
                      <p className="text-xs text-stone-700 dark:text-stone-300 leading-relaxed whitespace-pre-line">
                        {selectedCase.advisory.description}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
};
