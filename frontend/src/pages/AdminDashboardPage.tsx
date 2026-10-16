import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertOctagon, FileSpreadsheet, RefreshCw, ShieldAlert, Users } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { formatConfidence, formatDateTime } from '../utils/media';

export const AdminDashboardPage: React.FC = () => {
  const { t } = useApp();

  const [dashboard, setDashboard] = useState<any | null>(null);
  const [regionalStats, setRegionalStats] = useState<any[]>([]);
  const [recentDiagnoses, setRecentDiagnoses] = useState<any[]>([]);
  const [comments, setComments] = useState<any[]>([]);
  const [geoCount, setGeoCount] = useState<number>(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAdminOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dashData = await adminService.getDashboard();
      setDashboard(dashData);
    } catch (err: any) {
      setError(err?.message || 'Unable to load administrator dashboard from /api/admin/dashboard.');
    } finally {
      setLoading(false);
    }

    adminService
      .getRegionalStatistics()
      .then((res) => {
        const list = Array.isArray(res)
          ? res
          : Array.isArray(res?.regions)
          ? res.regions
          : Array.isArray(res?.regional_statistics)
          ? res.regional_statistics
          : [];
        setRegionalStats(list);
      })
      .catch(() => {});

    adminService
      .getDiagnoses()
      .then((list) => setRecentDiagnoses(list.slice(0, 8)))
      .catch(() => {});

    adminService
      .getComments()
      .then((list) => setComments(list.slice(0, 5)))
      .catch(() => {});

    adminService
      .getGeoDiseases()
      .then((list) => setGeoCount(list.length))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadAdminOverview();
  }, [loadAdminOverview]);

  const diseaseChartData = React.useMemo(() => {
    const raw =
      dashboard?.disease_distribution ||
      dashboard?.diseases ||
      dashboard?.by_disease;
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
  }, [dashboard]);

  const totalUsers = dashboard?.total_users ?? dashboard?.users_count ?? dashboard?.summary?.total_users;
  const totalFarmers = dashboard?.total_farmers ?? dashboard?.farmers_count ?? dashboard?.summary?.total_farmers;
  const totalAgents =
    dashboard?.total_extension_agents ??
    dashboard?.extension_agents_count ??
    dashboard?.summary?.total_extension_agents;
  const totalDiagnoses =
    dashboard?.total_diagnoses ?? dashboard?.diagnoses_count ?? dashboard?.summary?.total_diagnoses;

  return (
    <AppShell
      title={t('navAdminDashboard')}
      subtitle="System-wide telemetry, regional maize disease distribution, user accounts, and outbreak monitoring."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={loadAdminOverview}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <Link
            to="/admin/outbreaks"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg whitespace-nowrap"
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>{t('navAdminOutbreaks')}</span>
          </Link>
          <Link
            to="/admin/reports"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 whitespace-nowrap"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{t('navAdminReports')}</span>
          </Link>
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState
          title="Could not load administrator dashboard"
          message={error}
          onRetry={loadAdminOverview}
        />
      ) : !dashboard ? (
        <EmptyState
          title="No administrator metrics returned"
          description="Verify that your authenticated account has the admin role."
        />
      ) : (
        <div className="space-y-8">
          {/* KPI Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span>Total Users</span>
                <Users className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
              </div>
              <p className="mt-2 text-2xl font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                {totalUsers ?? '—'}
              </p>
              <Link to="/admin/users" className="mt-2 inline-block text-xs text-emerald-800 dark:text-emerald-400 hover:underline">
                Manage Users
              </Link>
            </div>

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span>Registered Farmers</span>
                <Users className="w-4 h-4 text-emerald-800 dark:text-emerald-400" />
              </div>
              <p className="mt-2 text-2xl font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                {totalFarmers ?? '—'}
              </p>
              <Link to="/admin/farmers" className="mt-2 inline-block text-xs text-emerald-800 dark:text-emerald-400 hover:underline">
                View Farmers Directory
              </Link>
            </div>

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span>Extension Agents</span>
                <ShieldAlert className="w-4 h-4 text-amber-600" />
              </div>
              <p className="mt-2 text-2xl font-bold font-mono tabular-nums text-stone-900 dark:text-stone-100">
                {totalAgents ?? '—'}
              </p>
              <Link to="/admin/extension-agents" className="mt-2 inline-block text-xs text-emerald-800 dark:text-emerald-400 hover:underline">
                Manage Agents
              </Link>
            </div>

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span>Total Diagnoses</span>
                <span className="font-mono">{geoCount > 0 ? `${geoCount} geo-tagged` : ''}</span>
              </div>
              <p className="mt-2 text-2xl font-bold font-mono tabular-nums text-emerald-800 dark:text-emerald-400">
                {totalDiagnoses ?? '—'}
              </p>
              <Link to="/admin/reports" className="mt-2 inline-block text-xs text-emerald-800 dark:text-emerald-400 hover:underline">
                Export Reports
              </Link>
            </div>
          </div>

          {/* Disease Distribution & Regional Statistics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                System Disease Distribution
              </h2>
              {diseaseChartData.length === 0 ? (
                <p className="text-xs text-stone-500 py-12 text-center">
                  No disease distribution records returned by /api/admin/dashboard.
                </p>
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={diseaseChartData} margin={{ top: 8, right: 12, left: -12, bottom: 8 }}>
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

            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                Regional Statistics (/api/admin/regional-statistics)
              </h2>
              {regionalStats.length === 0 ? (
                <p className="text-xs text-stone-500 py-12 text-center">
                  No regional statistics records returned yet.
                </p>
              ) : (
                <div className="overflow-x-auto max-h-64">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-stone-200 dark:border-stone-800 text-stone-500">
                        <th className="py-2 px-3">Region</th>
                        <th className="py-2 px-3 text-right">Cases / Diagnoses</th>
                        <th className="py-2 px-3 text-right">Farmers</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                      {regionalStats.map((reg, idx) => (
                        <tr key={String(reg.region ?? idx)}>
                          <td className="py-2.5 px-3 font-medium text-stone-900 dark:text-stone-100">
                            {reg.region || reg.name || 'Unspecified'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                            {reg.diagnoses_count ?? reg.total_diagnoses ?? reg.count ?? '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                            {reg.farmers_count ?? reg.total_farmers ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* System Diagnoses & Recent Community Comments */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                Recent System Diagnoses (/api/admin/diagnoses)
              </h2>
              {recentDiagnoses.length === 0 ? (
                <p className="text-xs text-stone-500">No diagnosis records returned.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-stone-200 dark:border-stone-800 text-stone-500">
                        <th className="py-2 px-3">ID</th>
                        <th className="py-2 px-3">Disease Class</th>
                        <th className="py-2 px-3">Region</th>
                        <th className="py-2 px-3 text-right">Confidence</th>
                        <th className="py-2 px-3">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                      {recentDiagnoses.map((d, i) => (
                        <tr key={String(d.id ?? d.diagnosis_id ?? i)}>
                          <td className="py-2.5 px-3 font-mono text-stone-500">
                            #{d.diagnosis_id ?? d.id}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-stone-900 dark:text-stone-100">
                            {d.disease_class || d.class_name}
                          </td>
                          <td className="py-2.5 px-3 text-stone-600 dark:text-stone-400">
                            {d.region || '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono tabular-nums text-emerald-800 dark:text-emerald-400">
                            {formatConfidence(d.confidence)}
                          </td>
                          <td className="py-2.5 px-3 font-mono tabular-nums text-stone-500">
                            {formatDateTime(d.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="lg:col-span-5 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                Community Comments (/api/admin/comments)
              </h2>
              {comments.length === 0 ? (
                <p className="text-xs text-stone-500">No discussion comments returned.</p>
              ) : (
                <div className="space-y-3">
                  {comments.map((c, idx) => (
                    <div
                      key={String(c.id ?? idx)}
                      className="rounded-lg border border-stone-200 dark:border-stone-800 p-3 text-xs"
                    >
                      <div className="flex items-center justify-between text-stone-500">
                        <span className="font-semibold text-stone-800 dark:text-stone-200">
                          {c.author_name || c.user_name || 'User'}
                        </span>
                        <span className="font-mono">{formatDateTime(c.created_at)}</span>
                      </div>
                      <p className="mt-1 text-stone-600 dark:text-stone-400 line-clamp-2">
                        {c.content || c.comment}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
};
