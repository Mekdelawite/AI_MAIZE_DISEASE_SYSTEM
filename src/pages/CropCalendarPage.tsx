import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, MapPin, RefreshCw } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { weatherService } from '../services/weatherService';
import { CropCalendarData } from '../types/api';

export const CropCalendarPage: React.FC = () => {
  const { t } = useApp();

  const [calendar, setCalendar] = useState<CropCalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCalendar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await weatherService.getCropCalendar();
      setCalendar(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load crop calendar from /api/crop-calendar.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCalendar();
  }, [loadCalendar]);

  const stages = calendar?.stages || calendar?.calendar || [];

  return (
    <AppShell
      title={t('navCalendar')}
      subtitle="Seasonal maize phenology and crop-management stages returned by GET /api/crop-calendar for your saved region and language."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadCalendar}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <Link
            to="/farmer/profile"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800"
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>Update Location</span>
          </Link>
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error ? (
        <div className="space-y-4">
          <ErrorState
            title="Could not load maize crop calendar"
            message={error}
            onRetry={loadCalendar}
          />
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 flex flex-wrap items-center justify-between gap-4 text-xs">
            <span className="text-stone-600 dark:text-stone-400">
              Ensure your region and woreda are saved in your Farmer Profile so the backend can resolve your agro-ecological zone.
            </span>
            <Link
              to="/farmer/profile"
              className="px-4 py-2 font-semibold text-white bg-emerald-900 rounded-lg whitespace-nowrap"
            >
              Go to Farmer Profile
            </Link>
          </div>
        </div>
      ) : !calendar || (stages.length === 0 && !calendar.notes && !calendar.recommendations) ? (
        <EmptyState
          title="No crop calendar stages returned"
          description="Verify that your Farmer Profile has a valid Ethiopian region and woreda configured."
          actionLabel="Configure Profile"
          onAction={() => {}}
        />
      ) : (
        <div className="space-y-6">
          {/* Metadata Header */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3 text-xs text-stone-600 dark:text-stone-400">
              <Calendar className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
              <span>Region: {calendar.region || 'Configured Region'}</span>
              {calendar.woreda && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>Woreda: {calendar.woreda}</span>
                </>
              )}
              {calendar.agro_ecology && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>Agro-Ecology: {calendar.agro_ecology}</span>
                </>
              )}
              {calendar.season && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>Season: {calendar.season}</span>
                </>
              )}
            </div>
          </div>

          {/* Stages Timeline Grid */}
          {stages.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {stages.map((stage, idx) => (
                <div
                  key={String(stage.id ?? idx)}
                  className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 text-xs text-stone-500 font-mono">
                      <span>Stage {String(idx + 1).padStart(2, '0')}</span>
                      <span>
                        {Array.isArray(stage.months)
                          ? stage.months.join(' – ')
                          : stage.months ||
                            (stage.start_month ? `${stage.start_month} – ${stage.end_month || ''}` : '')}
                      </span>
                    </div>
                    <h3 className="mt-2 text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                      {stage.stage_name || stage.name || stage.phase || `Stage ${idx + 1}`}
                    </h3>
                    {stage.description && (
                      <p className="mt-2 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                        {stage.description}
                      </p>
                    )}

                    {Array.isArray(stage.activities) && stage.activities.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-stone-200/70 dark:border-stone-800">
                        <p className="text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
                          Key Agronomic Activities
                        </p>
                        <ul className="list-disc pl-4 space-y-1 text-xs text-stone-600 dark:text-stone-400">
                          {stage.activities.map((act, i) => (
                            <li key={i}>{act}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {Array.isArray(stage.disease_watch) && stage.disease_watch.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-stone-200/70 dark:border-stone-800">
                        <p className="text-xs font-semibold text-amber-800 dark:text-amber-400 mb-1">
                          Disease Monitoring Focus
                        </p>
                        <p className="text-xs text-stone-600 dark:text-stone-400">
                          {stage.disease_watch.join(' · ')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {calendar.notes && (
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 text-sm text-stone-700 dark:text-stone-300">
              {calendar.notes}
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
};
