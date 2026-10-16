import React, { useCallback, useEffect, useState } from 'react';
import { Plus, RefreshCw, X } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { formatDateTime } from '../utils/media';

export const ExtensionAgentManagementPage: React.FC = () => {
  const { t, notify } = useApp();

  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Agent Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [region, setRegion] = useState('Oromia');
  const [woreda, setWoreda] = useState('');
  const [kebele, setKebele] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<'en' | 'am'>('en');
  const [creating, setCreating] = useState(false);

  const loadAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await adminService.getExtensionAgents();
      setAgents(list);
    } catch (err: any) {
      setError(err?.message || 'Unable to load extension agents from /api/admin/extension-agents.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !phoneNumber.trim() || !password || !region.trim() || !woreda.trim()) {
      notify('Full name, phone number, password, region, and woreda are required.', 'warning');
      return;
    }

    setCreating(true);
    try {
      await adminService.createExtensionAgent({
        full_name: fullName.trim(),
        phone_number: phoneNumber.trim(),
        password,
        region: region.trim(),
        woreda: woreda.trim(),
        kebele: kebele.trim() || undefined,
        preferred_language: preferredLanguage,
      });
      notify('Extension agent account created on server.', 'success');
      setCreateOpen(false);
      setFullName('');
      setPhoneNumber('');
      setPassword('');
      setWoreda('');
      setKebele('');
      loadAgents();
    } catch (err: any) {
      notify(err?.message || 'Failed to create extension agent account.', 'error');
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppShell
      title={t('navAdminAgents')}
      subtitle="Manage woreda agricultural extension agents via GET and POST /api/admin/extension-agents."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadAgents}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Register Extension Agent</span>
          </button>
        </div>
      }
    >
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error ? (
        <ErrorState
          title="Could not load extension agents"
          message={error}
          onRetry={loadAgents}
        />
      ) : agents.length === 0 ? (
        <EmptyState
          title="No extension agents registered yet"
          description="Provision woreda extension officers so they can monitor regional maize cases and reply to farmer questions."
          actionLabel="Register Extension Agent"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Agent Name</th>
                  <th className="py-3 px-4">Phone Number</th>
                  <th className="py-3 px-4">Assigned Region & Woreda</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {agents.map((ag, idx) => (
                  <tr key={String(ag.id ?? idx)}>
                    <td className="py-3 px-4 font-mono tabular-nums text-xs text-stone-500">
                      #{ag.id}
                    </td>
                    <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                      {ag.full_name || ag.name || '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-stone-600 dark:text-stone-400">
                      {ag.phone_number || ag.phone || '—'}
                    </td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                      {ag.region || '—'} · {ag.woreda || '—'}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {ag.is_active !== false ? (
                        <span className="text-emerald-800 dark:text-emerald-400 font-medium">Active</span>
                      ) : (
                        <span className="text-red-700 dark:text-red-400 font-medium">Inactive</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono tabular-nums text-stone-500">
                      {formatDateTime(ag.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Extension Agent Modal */}
      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-lg rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                Register Extension Agent (/api/admin/extension-agents)
              </h3>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="text-stone-400 hover:text-stone-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateAgent} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Phone Number *
                  </label>
                  <input
                    type="tel"
                    required
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="+2519..."
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Initial Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Preferred Language
                  </label>
                  <select
                    value={preferredLanguage}
                    onChange={(e) => setPreferredLanguage(e.target.value as 'en' | 'am')}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  >
                    <option value="en">English (en)</option>
                    <option value="am">አማርኛ (am)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Region *
                  </label>
                  <input
                    type="text"
                    required
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Woreda *
                  </label>
                  <input
                    type="text"
                    required
                    value={woreda}
                    onChange={(e) => setWoreda(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Kebele (Optional)
                  </label>
                  <input
                    type="text"
                    value={kebele}
                    onChange={(e) => setKebele(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setCreateOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 rounded-lg cursor-pointer"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50 cursor-pointer"
                >
                  {creating ? 'Creating Account...' : 'Create Agent Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
};
