import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { EthiopiaDiseaseMap, normalizeEthiopianRegionName, resolveEthiopianRegionName } from '../components/maps/EthiopiaDiseaseMap';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { extensionService } from '../services/extensionService';
import { formatConfidence, formatDateTime } from '../utils/media';

export const ExtensionMapPage: React.FC = () => {
  const { t } = useApp();
  const [geoCases, setGeoCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diseaseFilter, setDiseaseFilter] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('');

  const loadGeoData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setGeoCases(await extensionService.getGeoDiseases({ disease_class: diseaseFilter || undefined }));
    } catch (err: any) {
      setError(err?.message || 'Unable to load geographic disease records.');
    } finally {
      setLoading(false);
    }
  }, [diseaseFilter]);
  useEffect(() => { void loadGeoData(); }, [loadGeoData]);

  const diseases = useMemo(() => [...new Set(geoCases.map((item) => item.disease_class || item.class_name).filter(Boolean))].sort(), [geoCases]);
  const regionCases = useMemo(() => geoCases.filter((item) => !selectedRegion || normalizeEthiopianRegionName(resolveEthiopianRegionName(item.region)) === normalizeEthiopianRegionName(resolveEthiopianRegionName(selectedRegion))), [geoCases, selectedRegion]);
  const mappedCases = useMemo(() => regionCases.filter((item) => Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude))), [regionCases]);

  return <AppShell title={t('navExtMap')} subtitle="Disease records in your assigned area, shown on Ethiopia’s administrative map."
    actions={<div className="flex items-center gap-2">
      <select value={diseaseFilter} onChange={(e) => setDiseaseFilter(e.target.value)} aria-label="Filter by disease type" className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs dark:border-stone-700 dark:bg-stone-900">
        <option value="">All diseases</option>{diseases.map((disease) => <option key={disease} value={disease}>{disease}</option>)}
      </select>
      <button type="button" onClick={() => void loadGeoData()} className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 px-3.5 py-2 text-xs font-medium text-stone-700 hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"><RefreshCw className="h-3.5 w-3.5" />{t('refresh')}</button>
    </div>}>
    {loading ? <LoadingSkeleton rows={4} /> : error ? <ErrorState title="Could not load geographic disease records" message={error} onRetry={() => void loadGeoData()} /> : geoCases.length === 0 ? <EmptyState title="No geo-tagged disease cases returned" description="No diagnosis records are available for your assigned area and selected disease." /> : <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121A16]">
        <h2 className="mb-1 text-base font-bold text-stone-900 dark:text-stone-100">Ethiopia disease map</h2>
        <p className="mb-3 text-xs text-stone-500">{mappedCases.length} of {regionCases.length} matching records have valid coordinates. Click a regional boundary to inspect it.</p>
        <div className="mb-3 flex flex-wrap gap-4 text-xs text-stone-600 dark:text-stone-300"><span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-red-600" />Outbreak (5+ at same GPS point)</span><span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-yellow-500" />Moderate (2–4)</span><span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-green-600" />Low (1)</span></div>
        <EthiopiaDiseaseMap cases={mappedCases} selectedRegion={selectedRegion} onSelectRegion={setSelectedRegion} />
        {selectedRegion && <p className="mt-3 text-xs text-stone-600 dark:text-stone-300" aria-live="polite"><strong>{selectedRegion}</strong>: {regionCases.length} records, {mappedCases.length} with valid coordinates. <button className="ml-2 underline" onClick={() => setSelectedRegion('')}>Clear region</button></p>}
        {!selectedRegion && geoCases.length > mappedCases.length && <p className="mt-3 text-xs text-stone-500">{geoCases.length - mappedCases.length} records are missing valid coordinates and are omitted from map markers.</p>}
      </section>
      <section className="overflow-hidden rounded-xl border border-stone-200 bg-white dark:border-stone-800 dark:bg-[#121A16]"><div className="overflow-x-auto"><table className="w-full border-collapse text-left text-sm"><thead><tr className="border-b bg-stone-50/60 text-xs text-stone-500 dark:bg-stone-900/40"><th className="px-4 py-3">Disease</th><th className="px-4 py-3">Farmer</th><th className="px-4 py-3">Region / Woreda</th><th className="px-4 py-3">Coordinates</th><th className="px-4 py-3">Confidence</th><th className="px-4 py-3">Timestamp</th></tr></thead><tbody className="divide-y divide-stone-200 dark:divide-stone-800">{regionCases.map((item, index) => <tr key={String(item.id ?? item.diagnosis_id ?? index)}><td className="px-4 py-3">{item.disease_class || item.class_name || '—'}</td><td className="px-4 py-3">{item.farmer_name || '—'}</td><td className="px-4 py-3">{[item.region, item.woreda].filter(Boolean).join(' · ') || '—'}</td><td className="px-4 py-3 font-mono text-xs">{item.latitude != null && item.longitude != null ? `${item.latitude}, ${item.longitude}` : '—'}</td><td className="px-4 py-3">{formatConfidence(item.confidence)}</td><td className="px-4 py-3">{formatDateTime(item.created_at)}</td></tr>)}</tbody></table></div></section>
    </div>}
  </AppShell>;
};
