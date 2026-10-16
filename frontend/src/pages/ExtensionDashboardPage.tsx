import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, RefreshCw, ScanLine } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  LineChart,
  Line,
} from 'recharts';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { extensionService } from '../services/extensionService';

export const ExtensionDashboardPage: React.FC = () => {
  const { t } = useApp();

  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await extensionService.getDashboard();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Unable to load extension agent dashboard from /api/extension/dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Normalize real API arrays if present
  const diseaseDist: { name: string; count: number }[] = React.useMemo(() => {
    const raw = data?.disease_distribution || data?.diseases || data?.by_disease;
    if (!raw) return [];
    if (Array.isArray(raw)) {
      return raw.map((item: any) => ({
        name: String(item.disease_class || item.class_name || item.name || 'Unknown'),
        count: Number(item.count ?? item.total ?? 0),
      }));
    }
    if (typeof raw === 'object') {
      return Object.entries(raw).map(([name, count]) => ({
        name,
        count: Number(count ?? 0),
      }));
    }
    return [];
  }, [data]);

  const trendsData: { date: string; count: number }[] = React.useMemo(() => {
    const raw = data?.trends || data?.diagnosis_trends || data?.daily_cases;
    if (!Array.isArray(raw)) return [];
    return raw.map((item: any) => ({
      date: String(item.date || item.period || item.day || ''),
      count: Number(item.count ?? item.total ?? 0),
    }));
  }, [data]);

  const woredaBreakdown: { woreda: string; count: number }[] = React.useMemo(() => {
    const raw = data?.cases_by_woreda || data?.by_woreda || data?.woreda_summary;
    if (!raw) return [];
    if (Array.isArray(raw)) {
      return raw.map((item: any) => ({
        woreda: String(item.woreda || item.name || 'Unassigned'),
        count: Number(item.count ?? item.total ?? 0),
      }));
    }
    if (typeof raw === 'object') {
      return Object.entries(raw).map(([woreda, count]) => ({
        woreda,
        count: Number(count ?? 0),
      }));
    }
    return [];
  }, [data]);

  const totalDiagnoses =
    data?.total_diagnoses ?? data?.summary?.total_diagnoses ?? data?.total_cases ?? null;
  const assignedFarmers =
    data?.total_farmers ?? data?.summary?.total_farmers ?? data?.assigned_farmers ?? null;
  const assignedRegion = data?.region || data?.assignment?.region || null;
  const assignedWoreda = data?.woreda || data?.assignment?.woreda || null;

  return (
    <AppShell
      title={t('navExtDashboard')}
      subtitle="Regional and woreda-assigned maize disease analytics from GET /api/extension/dashboard."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadDashboard}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <Link
            to="/extension/cases"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg whitespace-nowrap"
          >
            <ScanLine className="w-3.5 h-3.5" />
            <span>{t('navExtCases')}</span>
          </Link>
          <Link
            to="/extension/map"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 whitespace-nowrap"
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>{t('navExtMap')}</span>
          </Link>
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState
          title="Could not load extension dashboard"
          message={error}
          onRetry={loadDashboard}
        />
      ) : !data ? (
        <EmptyState
          title="No extension dashboard payload returned"
          description="Ensure your account is authorized with the extension_agent role."
        />
      ) : (
        <div className="space-y-8">
          {/* Summary Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <span className="text-xs text-stone-500">Assigned Jurisdiction</span>
              <p className="mt-1.5 text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                {assignedRegion || 'All Assigned Regions'}
                {assignedWoreda ? ` · ${assignedWoreda}` : ''}
              </p>
            </div>

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <span className="text-xs text-stone-500">Assigned Diagnoses</span>
              <p className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-emerald-800 dark:text-emerald-400">
                {totalDiagnoses !== null ? totalDiagnoses : '—'}
              </p>
            </div>

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <span className="text-xs text-stone-500">Farmers in Jurisdiction</span>
              <p className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                {assignedFarmers !== null ? assignedFarmers : '—'}
              </p>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Disease Distribution */}
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                Disease Class Distribution
              </h2>
              {diseaseDist.length === 0 ? (
                <p className="text-xs text-stone-500 py-12 text-center">
                  No disease distribution records returned by the API yet.
                </p>
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={diseaseDist} margin={{ top: 8, right: 12, left: -12, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#78716c33" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#065f46" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Trend Chart */}
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                Diagnosis Case Trends
              </h2>
              {trendsData.length === 0 ? (
                <p className="text-xs text-stone-500 py-12 text-center">
                  No time-series trend records returned by the API yet.
                </p>
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendsData} margin={{ top: 8, right: 12, left: -12, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#78716c33" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="count" stroke="#d97706" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {/* Cases Grouped by Woreda */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
            <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
              Cases Grouped by Woreda
            </h2>
            {woredaBreakdown.length === 0 ? (
              <p className="text-xs text-stone-500">
                No woreda breakdown records returned in the dashboard response.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-stone-200 dark:border-stone-800 text-xs text-stone-500">
                      <th className="py-2.5 px-4">Woreda</th>
                      <th className="py-2.5 px-4 text-right">Diagnosed Cases</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                    {woredaBreakdown.map((row) => (
                      <tr key={row.woreda}>
                        <td className="py-3 px-4 font-medium">{row.woreda}</td>
                        <td className="py-3 px-4 text-right font-mono tabular-nums font-semibold">
                          {row.count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
};
