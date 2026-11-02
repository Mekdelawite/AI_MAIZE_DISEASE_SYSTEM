import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, AlertOctagon, ArrowRight, Bell, CalendarDays, FileSpreadsheet, Leaf, MapPin, RefreshCw, ShieldAlert, Sprout, Users } from 'lucide-react';
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { formatDateTime } from '../utils/media';
import adminMaizeBanner from '../assets/images/farmer_dashboard_maize_banner.jpg';
import { EthiopiaDiseaseMap } from '../components/maps/EthiopiaDiseaseMap';

export const AdminDashboardPage: React.FC = () => {
  const { t } = useApp();

  const [dashboard, setDashboard] = useState<any | null>(null);
  const [regionalStats, setRegionalStats] = useState<any | null>(null);
  const [regionalFilters, setRegionalFilters] = useState({ disease_class: '', start_date: '', end_date: '' });
  const [regionalLoading, setRegionalLoading] = useState(true);
  const [regionalError, setRegionalError] = useState<string | null>(null);
  const [recentDiagnoses, setRecentDiagnoses] = useState<any[]>([]);
  const [comments, setComments] = useState<any[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [geoCount, setGeoCount] = useState<number>(0);
  const [geoCases, setGeoCases] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadComments = useCallback(async () => {
    setCommentsLoading(true);
    setCommentsError(null);
    try {
      setComments(await adminService.getComments());
    } catch (err: any) {
      setCommentsError(err?.message || 'Unable to load extension comments.');
    } finally {
      setCommentsLoading(false);
    }
  }, []);

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
      .getDiagnoses()
      .then((list) => setRecentDiagnoses(list.slice(0, 8)))
      .catch(() => {});

    loadComments();

    adminService
      .getGeoDiseases()
      .then((list) => {
        setGeoCases(list);
        setGeoCount(list.length);
      })
      .catch(() => {});
  }, [loadComments]);

  const loadRegionalStatistics = useCallback(async () => {
    setRegionalLoading(true);
    setRegionalError(null);
    try {
      setRegionalStats(await adminService.getRegionalStatistics(regionalFilters));
    } catch (err: any) {
      setRegionalError(err?.message || 'Unable to load regional statistics.');
    } finally {
      setRegionalLoading(false);
    }
  }, [regionalFilters]);

  useEffect(() => {
    loadAdminOverview();
  }, [loadAdminOverview]);

  useEffect(() => {
    loadRegionalStatistics();
  }, [loadRegionalStatistics]);

  const diseaseChartData = React.useMemo(() => {
    const raw =
      dashboard?.diagnoses?.by_disease ||
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

  const totalFarmers =
    dashboard?.users?.farmers ??
    dashboard?.total_farmers ??
    dashboard?.farmers_count ??
    dashboard?.summary?.total_farmers;
  const totalAgents =
    dashboard?.users?.extension_agents ??
    dashboard?.total_extension_agents ??
    dashboard?.extension_agents_count ??
    dashboard?.summary?.total_extension_agents;
  const totalDiagnoses =
    dashboard?.diagnoses?.total ??
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
          <section className="relative isolate overflow-hidden rounded-2xl border border-emerald-100 bg-emerald-950 shadow-sm dark:border-emerald-900">
            <img src={adminMaizeBanner} alt="Green maize field" className="absolute inset-0 -z-20 h-full w-full object-cover object-center" />
            <div className="absolute inset-0 -z-10 bg-gradient-to-r from-white via-white/90 to-white/15 dark:from-[#0d1c17]/95 dark:via-[#0d1c17]/75 dark:to-[#0d1c17]/20" />
            <div className="flex min-h-44 flex-wrap items-end justify-between gap-5 p-6 sm:min-h-52 sm:p-8">
              <div className="max-w-2xl">
                <p className="mb-2 inline-flex items-center gap-2 rounded-full bg-emerald-100/90 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-emerald-900 dark:bg-emerald-950/80 dark:text-emerald-200"><Sprout className="h-3.5 w-3.5" /> MaizeCare AI · Admin workspace</p>
                <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 dark:text-white sm:text-4xl">Welcome, Admin!</h2>
                <p className="mt-2 text-sm text-stone-700 dark:text-stone-100 sm:text-base">Manage the MaizeCare AI system and support farmers across Ethiopia.</p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-xl border border-white/70 bg-white/90 px-4 py-2.5 text-sm font-semibold text-stone-800 shadow-sm dark:border-white/15 dark:bg-stone-950/75 dark:text-stone-100"><CalendarDays className="h-4 w-4 text-emerald-800 dark:text-emerald-300" />{new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</div>
            </div>
          </section>

          {/* KPI Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="group rounded-2xl border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-stone-800 dark:bg-[#121A16]">
              <div className="flex items-center justify-between"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"><Users className="h-5 w-5" /></span><span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">Farmers</span></div>
              <p className="mt-3 text-3xl font-extrabold tabular-nums text-stone-900 dark:text-stone-100">{totalFarmers ?? '—'}</p>
              <span className="mt-1 block text-xs font-medium text-stone-500">Registered farmers</span>
            </div>

            <div className="group rounded-2xl border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-stone-800 dark:bg-[#121A16]">
              <div className="flex items-center justify-between"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime-100 text-emerald-800 dark:bg-lime-950/40 dark:text-lime-300"><Leaf className="h-5 w-5" /></span><span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">All time</span></div>
              <p className="mt-3 text-3xl font-extrabold tabular-nums text-stone-900 dark:text-stone-100">{totalDiagnoses ?? '—'}</p>
              <span className="mt-1 block text-xs font-medium text-stone-500">Disease diagnoses</span>
            </div>

            <div className="group rounded-2xl border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-stone-800 dark:bg-[#121A16]">
              <div className="flex items-center justify-between"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-100 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300"><ShieldAlert className="h-5 w-5" /></span><span className="text-xs font-semibold text-sky-700 dark:text-sky-300">Field network</span></div>
              <p className="mt-3 text-3xl font-extrabold tabular-nums text-stone-900 dark:text-stone-100">{totalAgents ?? '—'}</p>
              <span className="mt-1 block text-xs font-medium text-stone-500">Extension agents</span>
            </div>

            <div className="group rounded-2xl border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-stone-800 dark:bg-[#121A16]">
              <div className="flex items-center justify-between"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"><MapPin className="h-5 w-5" /></span><span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Geo-tagged: {geoCount}</span></div>
              <p className="mt-3 text-3xl font-extrabold tabular-nums text-stone-900 dark:text-stone-100">{regionalStats?.by_region?.length ?? '—'}</p>
              <span className="mt-1 block text-xs font-medium text-stone-500">Regions reporting</span>
            </div>
          </div>

          {/* Disease Distribution & Regional Statistics */}
          <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-3">
            <div className="min-w-0 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
              <div className="mb-3 flex items-center justify-between gap-3"><div><h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">Disease Statistics</h2><p className="mt-1 text-xs text-stone-500">Recorded cases by disease class</p></div><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"><Activity className="h-4 w-4" /></span></div>
              {diseaseChartData.length === 0 ? (
                <p className="text-xs text-stone-500 py-12 text-center">
                  No disease distribution records returned by /api/admin/dashboard.
                </p>
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={diseaseChartData} dataKey="count" nameKey="name" cx="50%" cy="46%" innerRadius={58} outerRadius={88} paddingAngle={3} strokeWidth={1} stroke="var(--color-stone-50, #fff)">
                        {diseaseChartData.map((_: any, index: number) => <Cell key={`disease-${index}`} fill={['#07845c', '#f4b400', '#f97316', '#8b5cf6', '#2f80ed', '#ef4444'][index % 6]} />)}
                      </Pie>
                      <Tooltip formatter={(value: any) => [value, 'Cases']} />
                      <Legend verticalAlign="bottom" height={48} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <section className="min-w-0 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
              <div className="mb-3 flex items-center gap-2"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"><MapPin className="h-4 w-4" /></span><div><h2 className="text-sm font-bold text-stone-900 dark:text-stone-100">Disease Distribution in Ethiopia</h2><p className="text-[11px] text-stone-500">Geo-tagged diagnosis hotspots</p></div></div>
              {geoCases.length > 0 ? <EthiopiaDiseaseMap cases={geoCases} selectedRegion="" onSelectRegion={() => {}} mapHeight={270} compact focusEthiopia /> : <div className="flex min-h-[270px] flex-col items-center justify-center rounded-xl bg-emerald-50/60 px-5 text-center dark:bg-emerald-950/20"><MapPin className="h-8 w-8 text-emerald-700 dark:text-emerald-400" /><p className="mt-3 text-sm font-semibold text-stone-800 dark:text-stone-200">No geo-tagged diagnoses to map yet</p><p className="mt-1 text-xs text-stone-500">Cases with valid GPS coordinates will appear here.</p><Link to="/admin/geo-diseases" className="mt-3 text-xs font-semibold text-emerald-800 hover:underline dark:text-emerald-300">Open disease map</Link></div>}
            </section>

            <section className="min-w-0 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
              <div className="mb-4 flex items-center justify-between gap-2"><div className="flex items-center gap-2"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"><Bell className="h-4 w-4" /></span><div><h2 className="text-base font-bold text-stone-900 dark:text-stone-100">Recent Activities</h2><p className="text-[11px] text-stone-500">Latest reported diagnoses</p></div></div><Link to="/admin/diagnoses" className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">View all <ArrowRight className="h-3 w-3" /></Link></div>
              {recentDiagnoses.length === 0 ? <p className="py-8 text-center text-xs text-stone-500">No recent activity is available.</p> : <div className="relative space-y-4 before:absolute before:bottom-3 before:left-4 before:top-3 before:w-px before:bg-stone-200 dark:before:bg-stone-700">{recentDiagnoses.slice(0, 4).map((item, index) => <div key={String(item.id ?? item.diagnosis_id ?? index)} className="relative flex gap-3"><span className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800 ring-4 ring-white dark:bg-emerald-950 dark:text-emerald-300 dark:ring-[#121A16]"><Leaf className="h-4 w-4" /></span><div className="min-w-0 pt-0.5"><p className="text-xs font-bold text-stone-800 dark:text-stone-100">New diagnosis reported</p><p className="mt-0.5 truncate text-xs text-stone-600 dark:text-stone-300">{item.region || 'Ethiopia'} · {item.disease_class || item.class_name || 'Disease diagnosis'}</p><p className="mt-0.5 text-[11px] text-stone-500">{formatDateTime(item.created_at)}</p></div></div>)}</div>}
            </section>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm dark:border-stone-800 dark:bg-[#121A16] lg:col-span-5">
              <div className="mb-4 flex items-center gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"><Activity className="h-4 w-4" /></span><div><h2 className="text-base font-bold text-stone-900 dark:text-stone-100">Quick Actions</h2><p className="text-xs text-stone-500">Go directly to common admin tasks</p></div></div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {[
                  { label: 'Manage Users', to: '/admin/users', icon: Users, iconClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300' },
                  { label: 'Disease Reports', to: '/admin/reports', icon: FileSpreadsheet, iconClass: 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300' },
                  { label: 'Regional Alerts', to: '/admin/regional-alerts', icon: Bell, iconClass: 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300' },
                  { label: 'Outbreak Monitor', to: '/admin/outbreaks', icon: AlertOctagon, iconClass: 'bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300' },
                  { label: 'Extension Agents', to: '/admin/extension-agents', icon: ShieldAlert, iconClass: 'bg-violet-100 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300' },
                  { label: 'Disease Map', to: '/admin/geo-diseases', icon: MapPin, iconClass: 'bg-sky-100 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300' },
                ].map(({ label, to, icon: Icon, iconClass }) => (
                  <Link key={to} to={to} className="group flex items-center gap-2.5 rounded-xl border border-stone-200 px-3 py-2.5 text-xs font-semibold text-stone-700 transition hover:border-emerald-300 hover:bg-emerald-50/60 dark:border-stone-800 dark:text-stone-200 dark:hover:border-emerald-900 dark:hover:bg-emerald-950/30">
                    <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${iconClass}`}><Icon className="h-4 w-4" /></span>{label}<ArrowRight className="ml-auto h-3.5 w-3.5 text-stone-400 transition group-hover:translate-x-0.5 group-hover:text-emerald-700" />
                  </Link>
                ))}
              </div>
            </section>
            <section className="relative isolate overflow-hidden rounded-2xl border border-emerald-100 bg-emerald-50 p-5 shadow-sm dark:border-emerald-950 dark:bg-emerald-950/20 lg:col-span-7">
              <img src={adminMaizeBanner} alt="" aria-hidden="true" className="absolute inset-y-0 right-0 -z-10 h-full w-2/5 object-cover object-right opacity-30" />
              <div className="absolute inset-0 -z-10 bg-gradient-to-r from-emerald-50 via-emerald-50/95 to-emerald-50/25 dark:from-[#10241a] dark:via-[#10241a]/90 dark:to-[#10241a]/30" />
              <div className="flex items-center gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/80 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300"><Sprout className="h-5 w-5" /></span><div><h2 className="text-base font-bold text-emerald-950 dark:text-emerald-100">Top Affected Regions</h2><p className="text-xs text-stone-600 dark:text-stone-300">Based on diagnoses in the selected period</p></div><Link to="/admin/geo-diseases" className="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 hover:underline dark:text-emerald-300">View map <ArrowRight className="h-3 w-3" /></Link></div>
              <form className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); loadRegionalStatistics(); }}>
                <select aria-label="Filter by disease" value={regionalFilters.disease_class} onChange={(event) => setRegionalFilters((filters) => ({ ...filters, disease_class: event.target.value }))} className="min-w-0 rounded-lg border border-stone-300 bg-white/90 px-2.5 py-2 text-xs text-stone-800 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200"><option value="">All disease classes</option>{diseaseChartData.map((disease: any) => <option key={disease.name} value={disease.name}>{disease.name}</option>)}</select>
                <input aria-label="From date" type="date" value={regionalFilters.start_date} onChange={(event) => setRegionalFilters((filters) => ({ ...filters, start_date: event.target.value, end_date: '' }))} className="min-w-0 rounded-lg border border-stone-300 bg-white/90 px-2 py-2 text-xs text-stone-800 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200" />
                <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" onClick={() => setRegionalFilters({ disease_class: '', start_date: '', end_date: '' })} className="rounded-lg px-3 py-1.5 text-xs text-stone-600 hover:bg-white/60 dark:text-stone-300">Clear</button><button type="submit" className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800" disabled={regionalLoading}><RefreshCw className={`h-3 w-3 ${regionalLoading ? 'animate-spin' : ''}`} />Apply</button></div>
              </form>
              {regionalLoading ? <p className="mt-5 text-xs text-stone-500">Loading region totals…</p> : regionalError ? <p className="mt-5 text-xs text-red-700 dark:text-red-300">Regional totals are unavailable.</p> : (regionalStats?.by_region || []).length === 0 ? <p className="mt-5 text-xs text-stone-600 dark:text-stone-300">No regions have diagnoses for these filters.</p> : <div className="mt-5 space-y-3">{[...(regionalStats?.by_region || [])].sort((a: any, b: any) => Number(b.count || 0) - Number(a.count || 0)).slice(0, 5).map((item: any, index: number, rows: any[]) => { const maximum = Math.max(1, Number(rows[0]?.count || 0)); const percent = Math.max(4, Math.round((Number(item.count || 0) / maximum) * 100)); return <div key={item.region || index} className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-2 text-xs"><span className="truncate font-medium text-stone-700 dark:text-stone-200">{item.region || 'Unspecified'}</span><span className="h-2 overflow-hidden rounded-full bg-white/80 dark:bg-stone-800"><span className="block h-full rounded-full bg-emerald-700 dark:bg-emerald-500" style={{ width: `${percent}%` }} /></span><span className="text-right font-mono text-stone-600 dark:text-stone-300">{item.count}</span></div>; })}</div>}
            </section>
          </div>

          {/* Extension Agent Comments */}
          <div className="grid grid-cols-1 gap-6">
            <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display mb-4">
                Extension Agent Comments
              </h2>
              <div className="flex items-center justify-between gap-3 -mt-2 mb-4">
                <p className="text-xs text-stone-500">{comments.length} diagnosis comments and discussion replies</p>
                <button type="button" onClick={loadComments} disabled={commentsLoading} aria-label="Refresh extension comments" className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 disabled:opacity-50">
                  <RefreshCw className={`w-3 h-3 ${commentsLoading ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>
              {commentsError ? (
                <p role="alert" className="text-xs text-red-700 dark:text-red-300">{commentsError}</p>
              ) : commentsLoading ? (
                <p className="text-xs text-stone-500 py-6 text-center">Loading extension comments...</p>
              ) : comments.length === 0 ? (
                <p className="text-xs text-stone-500 py-6 text-center">No extension agent comments returned.</p>
              ) : (
                <div className="space-y-3">
                  {comments.slice(0, 5).map((c, idx) => (
                    <div
                      key={String(c.id ?? idx)}
                      className="rounded-lg border border-stone-200 dark:border-stone-800 p-3 text-xs"
                    >
                      <div className="flex items-center justify-between text-stone-500">
                        <span className="font-semibold text-stone-800 dark:text-stone-200">
                          {c.extension_agent_name || 'Extension agent'}
                        </span>
                        <span className="font-mono">{formatDateTime(c.created_at)}</span>
                      </div>
                      <span className="mt-1 inline-block rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                        {c.source_label || (c.post_id != null ? 'Discussion reply' : 'Extension comment')}
                      </span>
                      <p className="mt-1 whitespace-pre-wrap break-words text-stone-600 dark:text-stone-400">
                        {c.comment || 'No comment text returned.'}
                      </p>
                      <p className="mt-2 text-[11px] text-stone-500">
                        {c.kind === 'discussion_reply' || c.post_id != null
                          ? `Discussion: ${c.post_title || `Post #${c.post_id ?? '—'}`}`
                          : `Diagnosis #${c.diagnosis_id ?? '—'}`}
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
