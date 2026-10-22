import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { MapPin, RefreshCw } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { formatConfidence, formatDateTime } from '../utils/media';
import { EthiopiaDiseaseMap, normalizeEthiopianRegionName, resolveEthiopianRegionName } from '../components/maps/EthiopiaDiseaseMap';

export const AdminGeoDiseaseMapPage: React.FC = () => {
  const { t } = useApp();
  const [cases, setCases] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diseaseClass, setDiseaseClass] = useState('');
  const [region, setRegion] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminService.getGeoDiseaseMapData({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setCases(result.cases);
      setCoverage(result.summary);
    } catch (err: any) {
      setError(err?.message || 'Unable to load geo-disease cases.');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  const regions = useMemo(
    () => (coverage.by_region || []).map((item: any) => item.region).filter(Boolean),
    [coverage]
  );
  const visibleCases = useMemo(
    () => cases.filter((item) => (!region || normalizeEthiopianRegionName(resolveEthiopianRegionName(item.region)) === normalizeEthiopianRegionName(resolveEthiopianRegionName(region))) && (!diseaseClass || item.disease_class === diseaseClass)),
    [cases, region, diseaseClass]
  );
  const selectedCoverage = region
    ? coverage.by_region?.find((item: any) => normalizeEthiopianRegionName(resolveEthiopianRegionName(item.region)) === normalizeEthiopianRegionName(resolveEthiopianRegionName(region))) || {}
    : { ...coverage, total_diagnoses: coverage.total_farmer_diagnoses };
  const mappedCases = useMemo(() => visibleCases.filter((item) => item.latitude != null && item.longitude != null && Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude))), [visibleCases]);
  const diseases = useMemo(() => [...new Set(cases.map((item) => item.disease_class).filter(Boolean))].sort(), [cases]);

  return (
    <AppShell
      title="Geo-Disease Map"
      subtitle="Geographic distribution of farmer disease diagnoses across all regions."
      actions={
        <button
          type="button"
          onClick={() => void loadCases()}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('refresh')}</span>
        </button>
      }
    >
      <div className="mb-6 grid grid-cols-1 gap-3 rounded-xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-[#121A16] sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs text-stone-600 dark:text-stone-300">
          Disease class
          <select
            value={diseaseClass}
            onChange={(event) => setDiseaseClass(event.target.value)}
            className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs dark:border-stone-700 dark:bg-stone-900"
          >
            <option value="">All diseases</option>
            {diseases.map((item: string) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs text-stone-600 dark:text-stone-300">
          Region
          <select
            value={region}
            onChange={(event) => setRegion(event.target.value)}
            className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs dark:border-stone-700 dark:bg-stone-900"
          >
            <option value="">All regions</option>
            {regions.map((item: string) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs text-stone-600 dark:text-stone-300">
          From
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs dark:border-stone-700 dark:bg-stone-900"
          />
        </label>
        <label className="text-xs text-stone-600 dark:text-stone-300">
          To
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs dark:border-stone-700 dark:bg-stone-900"
          />
        </label>
      </div>

      {!loading && !error && Number(selectedCoverage.total_diagnoses || 0) > 0 && (
        <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            ['Farmer diagnoses', selectedCoverage.total_diagnoses],
            ['Mapped cases', selectedCoverage.mapped_cases],
            ['Missing GPS coordinates', selectedCoverage.missing_coordinates],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-[#121A16]">
              <p className="text-xs text-stone-500">{label}</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-stone-900 dark:text-stone-100">{value}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState title="Could not load geo-disease cases" message={error} onRetry={loadCases} />
      ) : (
        <div className="space-y-6">
          <section className="rounded-xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121A16]">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-bold text-stone-900 dark:text-stone-100">Mapped disease cases</h2>
                <p className="text-xs text-stone-500">{mappedCases.length} mapped diagnosis(es); overlapping locations are grouped</p>
              </div>
              <MapPin className="h-5 w-5 text-emerald-800 dark:text-emerald-400" />
            </div>
            <div className="mb-3 flex flex-wrap gap-4 text-xs text-stone-600 dark:text-stone-300" aria-label="Hotspot severity legend">
              <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-red-600" />Outbreak (5+ diagnoses at same GPS point)</span>
              <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-yellow-500" />Moderate (2-4)</span>
              <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-green-600" />Low (1)</span>
            </div>
            <EthiopiaDiseaseMap cases={mappedCases} selectedRegion={region} onSelectRegion={setRegion} />
            <p className="mt-2 text-[11px] text-stone-500">Click a regional boundary to filter cases and view its statistics. Hotspot severity uses the diagnosis count at each exact GPS location.</p>
            {mappedCases.length === 0 && <p className="mt-3 rounded-lg bg-stone-50 p-3 text-xs text-stone-600 dark:bg-stone-900/70 dark:text-stone-300" role="status">
              {Number(selectedCoverage.total_diagnoses || 0) > 0
                ? `${selectedCoverage.missing_coordinates || 0} diagnosis(es) are missing GPS coordinates, or no cases match the active filters. The regional map remains available.`
                : 'No diagnoses match the current date, disease, and region filters. The regional map remains available.'}
            </p>}
            {region && <p className="mt-2 text-xs text-stone-600 dark:text-stone-300" aria-live="polite"><strong>{region}</strong>: {selectedCoverage.total_diagnoses || 0} diagnosis records, {selectedCoverage.mapped_cases || 0} mapped, {selectedCoverage.missing_coordinates || 0} missing coordinates. {visibleCases.length} match the active disease filter.</p>}
          </section>

          {visibleCases.length > 0 ? (
          <section className="overflow-hidden rounded-xl border border-stone-200 bg-white dark:border-stone-800 dark:bg-[#121A16]">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50/60 text-xs font-semibold text-stone-500 dark:border-stone-800 dark:bg-stone-900/40">
                    <th className="px-4 py-3">Farmer</th>
                    <th className="px-4 py-3">Disease</th>
                    <th className="px-4 py-3">Region / Woreda / Kebele</th>
                    <th className="px-4 py-3 text-right">Coordinates</th>
                    <th className="px-4 py-3 text-right">Confidence</th>
                    <th className="px-4 py-3">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                  {visibleCases.map((item, index) => (
                    <tr key={String(item.diagnosis_id ?? item.id ?? index)}>
                      <td className="px-4 py-3 font-medium">{item.farmer_name || '—'}</td>
                      <td className="px-4 py-3">{item.disease_class || '—'}</td>
                      <td className="px-4 py-3 text-xs text-stone-600 dark:text-stone-400">
                        {[item.region, item.woreda, item.kebele].filter(Boolean).join(' · ') || '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs">
                        {item.latitude != null && item.longitude != null && Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude)) ? `${Number(item.latitude).toFixed(5)}, ${Number(item.longitude).toFixed(5)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs">{formatConfidence(item.confidence)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-stone-500">{formatDateTime(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          ) : <EmptyState title="No diagnosis records to list" description="The regional map is still shown above. Adjust the filters or add diagnoses with valid GPS coordinates to see disease hotspots." />}
        </div>
      )}
    </AppShell>
  );
};
