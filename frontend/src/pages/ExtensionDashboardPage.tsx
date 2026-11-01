import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BellRing, Leaf, MapPin, MessageSquare, RefreshCw, ScanLine, ShieldCheck, Users } from 'lucide-react';
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
import { useAuth } from '../context/AuthContext';
import extensionHero from '../assets/images/extension_advisory_field_1791572402850.jpg';

export const ExtensionDashboardPage: React.FC = () => {
  const { t, language } = useApp();
  const { user } = useAuth();

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
      subtitle={language === 'am' ? 'የተመደበውን አካባቢ የበቆሎ በሽታ ሁኔታ ይከታተሉ እና አርሶ አደሮችን ይደግፉ።' : 'Monitor maize disease in your assigned area and support local farmers.'}
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
      <section
        className="relative mb-6 overflow-hidden rounded-2xl bg-emerald-950 bg-cover bg-center shadow-lg"
        style={{
          backgroundImage: `linear-gradient(90deg, rgba(4, 37, 29, 0.88) 0%, rgba(4, 48, 35, 0.66) 52%, rgba(4, 48, 35, 0.12) 100%), url(${extensionHero})`,
          backgroundPosition: 'center 43%',
        }}
      >
        <div className="relative flex min-h-[245px] flex-col justify-center p-6 sm:min-h-[285px] sm:p-9 lg:p-11">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-50 backdrop-blur-sm">
              <Leaf className="h-3.5 w-3.5" />
              {language === 'am' ? 'የአካባቢዎ የግብርና ድጋፍ' : 'Local agricultural support'}
            </span>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-white font-display sm:text-4xl">
              {language === 'am' ? 'እንኳን ደህና መጡ' : 'Welcome, Extension Agent'}{user?.full_name ? `, ${user.full_name}` : '!'}
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-emerald-50/95 sm:text-base">
              {language === 'am' ? 'አርሶ አደሮችን በምክር ይደግፉ፣ የበሽታ ስርጭትን ይከታተሉ እና ጤናማ የበቆሎ ምርትን ያበረታቱ።' : 'Support farmers with timely advice, monitor disease reports, and help strengthen maize production in your community.'}
            </p>
            <div className="mt-5 flex flex-wrap gap-2 text-xs text-white/95">
              <span className="rounded-full border border-white/25 bg-black/15 px-3 py-1.5">{assignedRegion || (language === 'am' ? 'የተመደበ ክልል' : 'Assigned region')}{assignedWoreda ? ` · ${assignedWoreda}` : ''}</span>
              <span className="rounded-full border border-white/25 bg-black/15 px-3 py-1.5">{totalDiagnoses ?? '—'} {language === 'am' ? 'ምርመራዎች' : 'diagnoses'}</span>
            </div>
          </div>
        </div>
      </section>

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
          {/* Impact summary and quick actions */}
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
            <section className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-5 dark:border-emerald-950 dark:bg-emerald-950/15 xl:col-span-7 sm:p-6">
              <div className="mb-4 flex items-center gap-2.5">
                <Leaf className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
                <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">{language === 'am' ? 'የዚህ ወቅት አስተዋጽኦዎ' : 'Your Impact This Season'}</h2>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white bg-white/90 p-4 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
                  <Users className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
                  <p className="mt-3 text-2xl font-bold tabular-nums text-stone-900 dark:text-stone-100">{assignedFarmers !== null ? assignedFarmers : '—'}</p>
                  <p className="mt-0.5 text-xs text-stone-600 dark:text-stone-400">{language === 'am' ? 'በአካባቢው ያሉ አርሶ አደሮች' : 'Farmers in your area'}</p>
                </div>
                <div className="rounded-xl border border-white bg-white/90 p-4 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
                  <ScanLine className="h-5 w-5 text-sky-700 dark:text-sky-400" />
                  <p className="mt-3 text-2xl font-bold tabular-nums text-stone-900 dark:text-stone-100">{totalDiagnoses !== null ? totalDiagnoses : '—'}</p>
                  <p className="mt-0.5 text-xs text-stone-600 dark:text-stone-400">{language === 'am' ? 'የተመዘገቡ ምርመራዎች' : 'Assigned diagnoses'}</p>
                </div>
                <div className="rounded-xl border border-white bg-white/90 p-4 shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
                  <MapPin className="h-5 w-5 text-amber-700 dark:text-amber-400" />
                  <p className="mt-3 truncate text-base font-bold text-stone-900 dark:text-stone-100">{assignedWoreda || assignedRegion || '—'}</p>
                  <p className="mt-0.5 text-xs text-stone-600 dark:text-stone-400">{language === 'am' ? 'የተመደበ አካባቢ' : 'Assigned jurisdiction'}</p>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121A16] xl:col-span-5 sm:p-6">
              <div className="mb-3 flex items-center gap-2.5">
                <ShieldCheck className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
                <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">{language === 'am' ? 'ፈጣን እርምጃዎች' : 'Quick Actions'}</h2>
              </div>
              <div className="space-y-2">
                <Link to="/extension/cases" className="flex min-h-11 items-center gap-3 rounded-xl bg-sky-50 px-3 py-2.5 text-sm font-medium text-sky-950 transition hover:bg-sky-100 dark:bg-sky-950/30 dark:text-sky-100 dark:hover:bg-sky-950/50">
                  <Users className="h-4 w-4" /> <span className="flex-1">{language === 'am' ? 'የተመደቡ ጉዳዮችን ይመልከቱ' : 'View Assigned Farmers'}</span><ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/extension/map" className="flex min-h-11 items-center gap-3 rounded-xl bg-emerald-50 px-3 py-2.5 text-sm font-medium text-emerald-950 transition hover:bg-emerald-100 dark:bg-emerald-950/30 dark:text-emerald-100 dark:hover:bg-emerald-950/50">
                  <MapPin className="h-4 w-4" /> <span className="flex-1">{language === 'am' ? 'የበሽታ ካርታን ይመልከቱ' : 'View Disease Map'}</span><ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/admin/outbreaks" className="flex min-h-11 items-center gap-3 rounded-xl bg-amber-50 px-3 py-2.5 text-sm font-medium text-amber-950 transition hover:bg-amber-100 dark:bg-amber-950/30 dark:text-amber-100 dark:hover:bg-amber-950/50">
                  <BellRing className="h-4 w-4" /> <span className="flex-1">{language === 'am' ? 'የበሽታ ስርጭትን ይመዝግቡ' : 'Report Disease Outbreak'}</span><ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/farmer/discussion" className="flex min-h-11 items-center gap-3 rounded-xl bg-violet-50 px-3 py-2.5 text-sm font-medium text-violet-950 transition hover:bg-violet-100 dark:bg-violet-950/30 dark:text-violet-100 dark:hover:bg-violet-950/50">
                  <MessageSquare className="h-4 w-4" /> <span className="flex-1">{language === 'am' ? 'ከአርሶ አደሮች ጋር ይወያዩ' : 'Discuss with Farmers'}</span><ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </section>
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
