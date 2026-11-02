import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, FileSpreadsheet, RefreshCw, Search } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { adminService } from '../services/adminService';
import { formatConfidence, formatDateTime } from '../utils/media';

export const AdminDiagnosisActivityPage: React.FC = () => {
  const [diagnoses, setDiagnoses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const loadDiagnoses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDiagnoses(await adminService.getDiagnoses());
    } catch (err: any) {
      setError(err?.message || 'Unable to load diagnosis activity.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadDiagnoses(); }, [loadDiagnoses]);

  const visibleDiagnoses = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return diagnoses;
    return diagnoses.filter((item) => [
      item.diagnosis_id, item.id, item.disease_class, item.class_name,
      item.farmer_name, item.region, item.woreda,
    ].some((value) => String(value ?? '').toLowerCase().includes(normalizedQuery)));
  }, [diagnoses, query]);

  return (
    <AppShell
      title="Diagnosis Activity"
      subtitle="Review the full list of recently reported farmer diagnoses."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link to="/admin/dashboard" className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 px-3 py-2 text-xs font-medium text-stone-700 hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"><ArrowLeft className="h-3.5 w-3.5" />Dashboard</Link>
          <Link to="/admin/reports" className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-900 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-800"><FileSpreadsheet className="h-3.5 w-3.5" />Reports</Link>
        </div>
      }
    >
      {loading ? <LoadingSkeleton rows={6} /> : error ? (
        <ErrorState title="Could not load diagnosis activity" message={error} onRetry={() => void loadDiagnoses()} />
      ) : diagnoses.length === 0 ? (
        <EmptyState title="No diagnoses found" description="There are no diagnosis records available yet." />
      ) : (
        <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 p-5 dark:border-stone-800">
            <div><h2 className="text-base font-bold text-stone-900 dark:text-stone-100">All Diagnosis Activity</h2><p className="mt-1 text-xs text-stone-500">{visibleDiagnoses.length} of {diagnoses.length} diagnoses</p></div>
            <div className="flex w-full gap-2 sm:w-auto">
              <label className="relative min-w-0 flex-1 sm:w-72"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search disease, farmer, region…" className="w-full rounded-lg border border-stone-300 bg-white py-2 pl-9 pr-3 text-xs text-stone-800 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100" /></label>
              <button type="button" onClick={() => void loadDiagnoses()} disabled={loading} aria-label="Refresh diagnosis activity" className="inline-flex shrink-0 items-center justify-center rounded-lg border border-stone-300 px-3 text-stone-700 hover:bg-stone-100 disabled:opacity-50 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
            </div>
          </div>
          {visibleDiagnoses.length === 0 ? <p className="p-8 text-center text-sm text-stone-500">No diagnoses match “{query}”.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] table-fixed border-collapse text-left text-xs">
                <thead><tr className="border-b border-stone-200 text-stone-500 dark:border-stone-800"><th className="w-[38%] px-3 py-2.5">Diagnosis</th><th className="w-[32%] px-3 py-2.5">Farmer &amp; location</th><th className="w-[13%] px-3 py-2.5 text-right">Confidence</th><th className="w-[17%] px-3 py-2.5">Date</th></tr></thead>
                <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
                  {visibleDiagnoses.map((item, index) => {
                    const id = item.diagnosis_id ?? item.id;
                    const location = [item.region, item.woreda].filter(Boolean).join(' · ');
                    return <tr key={String(id ?? index)} className="hover:bg-emerald-50/40 dark:hover:bg-emerald-950/15"><td className="px-3 py-2"><div className="flex min-w-0 items-center gap-2"><span className="shrink-0 font-mono text-[10px] text-stone-400">#{id ?? '—'}</span><span className="truncate font-semibold text-stone-900 dark:text-stone-100" title={item.disease_class || item.class_name}>{item.disease_class || item.class_name || 'Unknown disease'}</span></div></td><td className="px-3 py-2"><span className="block truncate font-medium text-stone-700 dark:text-stone-200">{item.farmer_name || 'Unknown farmer'}</span><span className="mt-0.5 block truncate text-[10px] text-stone-500" title={location}>{location || 'Location not recorded'}</span></td><td className="px-3 py-2 text-right font-mono font-semibold text-emerald-800 dark:text-emerald-400">{formatConfidence(item.confidence)}</td><td className="whitespace-nowrap px-3 py-2 text-[11px] text-stone-500">{formatDateTime(item.created_at)}</td></tr>;
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </AppShell>
  );
};
