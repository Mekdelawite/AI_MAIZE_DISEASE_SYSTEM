import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { formatDateTime } from '../utils/media';

export const FarmerManagementPage: React.FC = () => {
  const { t } = useApp();

  const [farmers, setFarmers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [region, setRegion] = useState('');
  const [woreda, setWoreda] = useState('');
  const [kebele, setKebele] = useState('');

  const loadFarmers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await adminService.getFarmers({
        search: search.trim() || undefined,
        region: region.trim() || undefined,
        woreda: woreda.trim() || undefined,
        kebele: kebele.trim() || undefined,
      });
      setFarmers(list);
    } catch (err: any) {
      setError(err?.message || 'Unable to load farmers directory from /api/admin/farmers.');
    } finally {
      setLoading(false);
    }
  }, [search, region, woreda, kebele]);

  useEffect(() => {
    loadFarmers();
  }, [loadFarmers]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearch(searchInput.trim());
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [searchInput]);

  return (
    <AppShell
      title={t('navAdminFarmers')}
      actions={
        <button
          type="button"
          onClick={loadFarmers}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('refresh')}</span>
        </button>
      }
    >
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 grid grid-cols-1 sm:grid-cols-5 gap-3">
        <div className="relative sm:col-span-2">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search farmer name, phone, or kebele..."
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <input
          type="text"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          placeholder="Filter by Region"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
        <input
          type="text"
          value={kebele}
          onChange={(e) => setKebele(e.target.value)}
          placeholder="Filter by Kebele"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
        <input
          type="text"
          value={woreda}
          onChange={(e) => setWoreda(e.target.value)}
          placeholder="Filter by Woreda"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
      </div>

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState title="Could not load farmers list" message={error} onRetry={loadFarmers} />
      ) : farmers.length === 0 ? (
        <EmptyState
          title="No farmer records returned"
          description="Registered smallholder farmer accounts from /api/admin/farmers will appear here."
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Full Name</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Region</th>
                  <th className="py-3 px-4">Woreda</th>
                  <th className="py-3 px-4">Kebele</th>
                  <th className="py-3 px-4">Language</th>
                  <th className="py-3 px-4">SMS</th>
                  <th className="py-3 px-4">Registered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {farmers.map((f, idx) => (
                  <tr key={String(f.id ?? f.user_id ?? idx)}>
                    <td className="py-3 px-4 font-mono tabular-nums text-xs text-stone-500">
                      #{f.id ?? f.user_id}
                    </td>
                    <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                      {f.full_name || f.name || '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-stone-600 dark:text-stone-400">
                      {f.phone_number || f.phone || '—'}
                    </td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">{f.region || '—'}</td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">{f.woreda || '—'}</td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">{f.kebele || '—'}</td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                      {(f.preferred_language || 'en').toUpperCase()}
                    </td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                      {f.sms_opt_in ? 'On' : 'Off'}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono tabular-nums text-stone-500">
                      {formatDateTime(f.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
};
