import React, { useCallback, useEffect, useState } from 'react';
import { MapPin, RefreshCw } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
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

  const loadGeoData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await extensionService.getGeoDiseases({
        disease_class: diseaseFilter.trim() || undefined,
      });
      setGeoCases(items);
    } catch (err: any) {
      setError(err?.message || 'Unable to load geographic disease records from /api/extension/geo-diseases.');
    } finally {
      setLoading(false);
    }
  }, [diseaseFilter]);

  useEffect(() => {
    loadGeoData();
  }, [loadGeoData]);

  // Filter items that have valid numeric latitude & longitude
  const plottedPoints = geoCases.filter(
    (item) =>
      item.latitude !== undefined &&
      item.latitude !== null &&
      item.longitude !== undefined &&
      item.longitude !== null &&
      !Number.isNaN(Number(item.latitude)) &&
      !Number.isNaN(Number(item.longitude))
  );

  // Ethiopian bounding box approximate normalization (Lat 3°N to 15°N, Lng 33°E to 48°E)
  const projectPoint = (lat: number, lng: number) => {
    const x = Math.max(4, Math.min(96, ((lng - 33) / (48 - 33)) * 100));
    const y = Math.max(4, Math.min(96, 100 - ((lat - 3) / (15 - 3)) * 100));
    return { x, y };
  };

  return (
    <AppShell
      title={t('navExtMap')}
      subtitle="Geographic distribution of geo-tagged maize disease diagnoses from GET /api/extension/geo-diseases."
      actions={
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={diseaseFilter}
            onChange={(e) => setDiseaseFilter(e.target.value)}
            placeholder="Filter disease class..."
            className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
          <button
            type="button"
            onClick={loadGeoData}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error ? (
        <ErrorState
          title="Could not load geographic disease records"
          message={error}
          onRetry={loadGeoData}
        />
      ) : geoCases.length === 0 ? (
        <EmptyState
          title="No geo-tagged disease cases returned"
          description="Diagnoses associated with farmer profiles that have saved latitude and longitude coordinates will appear here."
        />
      ) : (
        <div className="space-y-6">
          {/* Coordinate Spatial Plot (Ethiopia Bounding Box 3°N–15°N, 33°E–48°E) */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div>
                <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                  Spatial Coordinate Projection (3°N–15°N, 33°E–48°E)
                </h2>
                <p className="text-xs text-stone-500 font-mono tabular-nums">
                  {plottedPoints.length} of {geoCases.length} record(s) include valid GPS coordinates
                </p>
              </div>
            </div>

            <div className="relative h-80 w-full rounded-xl border border-stone-200 dark:border-stone-800 bg-[#F3F1EC] dark:bg-[#0D1511] overflow-hidden">
              {/* Coordinate Grid Lines */}
              <div className="absolute inset-0 grid grid-cols-6 grid-rows-4 pointer-events-none">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div key={i} className="border-r border-b border-stone-300/40 dark:border-stone-800/60" />
                ))}
              </div>

              {plottedPoints.map((pt, idx) => {
                const { x, y } = projectPoint(Number(pt.latitude), Number(pt.longitude));
                return (
                  <div
                    key={String(pt.id ?? idx)}
                    style={{ left: `${x}%`, top: `${y}%` }}
                    className="absolute -translate-x-1/2 -translate-y-1/2 group"
                  >
                    <MapPin className="w-5 h-5 text-emerald-800 dark:text-amber-400 drop-shadow-xs" />
                    <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-20 w-48 rounded-lg bg-stone-900 text-white p-2.5 text-[11px] shadow-lg">
                      <p className="font-semibold">{pt.disease_class || pt.class_name}</p>
                      <p className="text-stone-300">
                        {pt.region || ''} {pt.woreda ? `· ${pt.woreda}` : ''}
                      </p>
                      <p className="font-mono text-stone-400 mt-0.5">
                        {Number(pt.latitude).toFixed(4)}, {Number(pt.longitude).toFixed(4)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Coordinate Table */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                    <th className="py-3 px-4">Disease Class</th>
                    <th className="py-3 px-4">Region / Woreda</th>
                    <th className="py-3 px-4 text-right">Latitude</th>
                    <th className="py-3 px-4 text-right">Longitude</th>
                    <th className="py-3 px-4 text-right">Confidence</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                  {geoCases.map((item, idx) => (
                    <tr key={String(item.id ?? idx)}>
                      <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                        {item.disease_class || item.class_name || '—'}
                      </td>
                      <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                        {item.region || '—'} {item.woreda ? `· ${item.woreda}` : ''}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-xs">
                        {item.latitude ?? '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-xs">
                        {item.longitude ?? '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-xs text-emerald-800 dark:text-emerald-400">
                        {formatConfidence(item.confidence)}
                      </td>
                      <td className="py-3 px-4 font-mono tabular-nums text-xs text-stone-500">
                        {formatDateTime(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
};
