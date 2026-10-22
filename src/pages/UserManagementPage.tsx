import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { UserRecord } from '../types/api';
import { formatDateTime } from '../utils/media';

export const UserManagementPage: React.FC = () => {
  const { t, notify } = useApp();

  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [kebeleFilter, setKebeleFilter] = useState('');

  // Status Toggle Confirmation
  const [pendingToggleUser, setPendingToggleUser] = useState<UserRecord | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await adminService.getUsers({
        role: roleFilter || undefined,
        region: regionFilter.trim() || undefined,
        kebele: kebeleFilter || undefined,
        search: search.trim() || undefined,
      });
      setUsers(list);
    } catch (err: any) {
      setError(err?.message || 'Unable to load users from /api/admin/users.');
    } finally {
      setLoading(false);
    }
  }, [roleFilter, regionFilter, kebeleFilter, search]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearch(searchInput.trim());
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [searchInput]);

  const handleConfirmToggleStatus = async () => {
    if (!pendingToggleUser) return;
    const nextStatus = pendingToggleUser.is_active === false ? true : false;
    setUpdatingStatus(true);
    try {
      await adminService.updateUserStatus(pendingToggleUser.id, nextStatus);
      setUsers((prev) =>
        prev.map((u) => (u.id === pendingToggleUser.id ? { ...u, is_active: nextStatus } : u))
      );
      notify(
        `User #${pendingToggleUser.id} status updated to ${nextStatus ? 'Active' : 'Inactive'}.`,
        'success'
      );
      setPendingToggleUser(null);
    } catch (err: any) {
      notify(err?.message || 'Failed to update user status.', 'error');
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <AppShell
      title={t('navAdminUsers')}
      actions={
        <button
          type="button"
          onClick={loadUsers}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('refresh')}</span>
        </button>
      }
    >
      {/* Filter Bar */}
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 flex flex-wrap items-center justify-between gap-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const nextSearch = searchInput.trim();
            if (nextSearch === search) {
              void loadUsers();
            } else {
              setSearch(nextSearch);
            }
          }}
          className="flex items-center gap-2 flex-1 min-w-[240px]"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by name, phone, role, or region..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-1.5 text-xs font-medium text-white bg-emerald-800 rounded-lg cursor-pointer"
          >
            {t('search')}
          </button>
        </form>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          aria-label="Filter by role"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        >
          <option value="">All Roles</option>
          <option value="farmer">Farmer</option>
          <option value="extension_agent">Extension Agent</option>
          <option value="admin">Admin</option>
        </select>
        <input
          type="text"
          value={regionFilter}
          onChange={(e) => setRegionFilter(e.target.value)}
          aria-label="Filter by region"
          placeholder="Filter by region"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
        <input
          type="text"
          value={kebeleFilter}
          onChange={(e) => setKebeleFilter(e.target.value)}
          aria-label="Filter by kebele"
          placeholder="Filter by kebele"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
      </div>

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState title="Could not load system users" message={error} onRetry={loadUsers} />
      ) : users.length === 0 ? (
        <EmptyState
          title="No matching user accounts found"
          description="Try clearing your search or role filter."
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Full Name</th>
                  <th className="py-3 px-4">Phone Number</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Region</th>
                  <th className="py-3 px-4">Kebele</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {users.map((u) => {
                  const isActive = u.is_active !== false;
                  return (
                    <tr key={String(u.id)} className="hover:bg-stone-50/80 dark:hover:bg-stone-800/40">
                      <td className="py-3 px-4 font-mono tabular-nums text-xs text-stone-500">
                        #{u.id}
                      </td>
                      <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                        {u.full_name || u.name || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-stone-600 dark:text-stone-400">
                        {u.phone_number || u.phone || '—'}
                      </td>
                      <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                        <span className="font-medium text-stone-900 dark:text-stone-100">{u.role}</span>
                      </td>
                      <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">{u.region || '—'}</td>
                      <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">{u.kebele || '—'}</td>
                      <td className="py-3 px-4 text-xs font-medium">
                        {isActive ? (
                          <span className="text-emerald-800 dark:text-emerald-400">Active</span>
                        ) : (
                          <span className="text-red-700 dark:text-red-400">Deactivated</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs font-mono tabular-nums text-stone-500">
                        {formatDateTime(u.created_at)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => setPendingToggleUser(u)}
                          className={`text-xs font-medium hover:underline cursor-pointer whitespace-nowrap ${
                            isActive
                              ? 'text-red-700 dark:text-red-400'
                              : 'text-emerald-800 dark:text-emerald-400'
                          }`}
                        >
                          {isActive ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingToggleUser)}
        title={
          pendingToggleUser?.is_active !== false
            ? 'Deactivate User Account'
            : 'Activate User Account'
        }
        description={
          pendingToggleUser?.is_active !== false
            ? `Are you sure you want to deactivate ${
                pendingToggleUser?.full_name || pendingToggleUser?.phone_number || 'this account'
              }? They will not be able to sign in until reactivated.`
            : `Reactivate ${
                pendingToggleUser?.full_name || pendingToggleUser?.phone_number || 'this account'
              }?`
        }
        confirmLabel={pendingToggleUser?.is_active !== false ? 'Deactivate Account' : 'Activate Account'}
        variant={pendingToggleUser?.is_active !== false ? 'danger' : 'primary'}
        loading={updatingStatus}
        onConfirm={handleConfirmToggleStatus}
        onCancel={() => setPendingToggleUser(null)}
      />
    </AppShell>
  );
};
