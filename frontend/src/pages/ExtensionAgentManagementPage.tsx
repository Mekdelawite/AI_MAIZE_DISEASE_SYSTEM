import React, { useCallback, useEffect, useState } from 'react';
import { Plus, RefreshCw, Search, X } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import {
  AdminGeographyOption,
  CreateExtensionAgentPayload,
  ExtensionAgentRecord,
  adminService,
} from '../services/adminService';
import { formatDateTime } from '../utils/media';

type GeographySelection = {
  region_id: string;
  zone_id: string;
  woreda_id: string;
};

type AssignmentHistoryItem = {
  id: number;
  previous_woreda?: string | null;
  new_woreda: string;
  changed_by_admin?: string | null;
  changed_at: string;
};

const EMPTY_ASSIGNMENT: GeographySelection = {
  region_id: '',
  zone_id: '',
  woreda_id: '',
};

const inputClass =
  'w-full px-3 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900';

function GeographySelectors({
  value,
  onChange,
  required = true,
}: {
  value: GeographySelection;
  onChange: (selection: GeographySelection) => void;
  required?: boolean;
}) {
  const [regions, setRegions] = useState<AdminGeographyOption[]>([]);
  const [zones, setZones] = useState<AdminGeographyOption[]>([]);
  const [woredas, setWoredas] = useState<AdminGeographyOption[]>([]);
  const [loadingRegions, setLoadingRegions] = useState(true);
  const [loadingZones, setLoadingZones] = useState(false);
  const [loadingWoredas, setLoadingWoredas] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    adminService.getExtensionAgentGeography('regions')
      .then((items) => {
        if (active) setRegions(items);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Unable to load regions.');
      })
      .finally(() => {
        if (active) setLoadingRegions(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    if (!value.region_id) {
      setZones([]);
      setWoredas([]);
      return () => {
        active = false;
      };
    }

    setLoadingZones(true);
    setError(null);
    adminService.getExtensionAgentGeography('zones', value.region_id)
      .then((items) => {
        if (active) setZones(items);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Unable to load zones.');
      })
      .finally(() => {
        if (active) setLoadingZones(false);
      });
    return () => {
      active = false;
    };
  }, [value.region_id]);

  useEffect(() => {
    let active = true;
    if (!value.zone_id) {
      setWoredas([]);
      return () => {
        active = false;
      };
    }

    setLoadingWoredas(true);
    setError(null);
    adminService.getExtensionAgentGeography('woredas', value.zone_id)
      .then((items) => {
        if (active) setWoredas(items);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Unable to load woredas.');
      })
      .finally(() => {
        if (active) setLoadingWoredas(false);
      });
    return () => {
      active = false;
    };
  }, [value.zone_id]);

  return (
    <div className="space-y-3">
      {error && <p className="text-xs text-red-700 dark:text-red-300" role="alert">{error}</p>}
      <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
        Region *
        <select
          required={required}
          value={value.region_id}
          onChange={(event) => onChange({
            region_id: event.target.value,
            zone_id: '',
            woreda_id: '',
          })}
          disabled={loadingRegions}
          className={`${inputClass} mt-1`}
        >
          <option value="">{loadingRegions ? 'Loading regions...' : 'Select region'}</option>
          {regions.map((region) => (
            <option key={region.id} value={region.id}>{region.name_en}</option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
        Zone *
        <select
          required={required}
          value={value.zone_id}
          onChange={(event) => onChange({
            ...value,
            zone_id: event.target.value,
            woreda_id: '',
          })}
          disabled={!value.region_id || loadingZones}
          className={`${inputClass} mt-1`}
        >
          <option value="">{loadingZones ? 'Loading zones...' : 'Select zone'}</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>{zone.name_en}</option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
        Woreda *
        <select
          required={required}
          value={value.woreda_id}
          onChange={(event) => onChange({ ...value, woreda_id: event.target.value })}
          disabled={!value.zone_id || loadingWoredas}
          className={`${inputClass} mt-1`}
        >
          <option value="">{loadingWoredas ? 'Loading woredas...' : 'Select one woreda'}</option>
          {woredas.map((woreda) => (
            <option key={woreda.id} value={woreda.id}>{woreda.name_en}</option>
          ))}
        </select>
      </label>
    </div>
  );
}

function StatusBadge({ children, tone }: { children: React.ReactNode; tone: 'green' | 'amber' | 'red' | 'stone' }) {
  const colors = {
    green: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
    red: 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300',
    stone: 'bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300',
  };
  return <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-medium ${colors[tone]}`}>{children}</span>;
}

export const ExtensionAgentManagementPage: React.FC = () => {
  const { t, notify } = useApp();
  const [agents, setAgents] = useState<ExtensionAgentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [woredaFilter, setWoredaFilter] = useState('');
  const [accountStatusFilter, setAccountStatusFilter] = useState('');
  const [verificationFilter, setVerificationFilter] = useState('');
  const [busyAgentId, setBusyAgentId] = useState<number | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [email, setEmail] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [organization, setOrganization] = useState('');
  const [verificationMethod, setVerificationMethod] = useState<'email' | 'sms'>('email');
  const [professionalInfoVerified, setProfessionalInfoVerified] = useState(false);
  const [preferredLanguage, setPreferredLanguage] = useState<'en' | 'am'>('en');
  const [createAssignment, setCreateAssignment] = useState<GeographySelection>(EMPTY_ASSIGNMENT);
  const [creating, setCreating] = useState(false);

  const [detailsAgent, setDetailsAgent] = useState<ExtensionAgentRecord | null>(null);
  const [assignmentHistory, setAssignmentHistory] = useState<AssignmentHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [transferAgent, setTransferAgent] = useState<ExtensionAgentRecord | null>(null);
  const [transferAssignment, setTransferAssignment] = useState<GeographySelection>(EMPTY_ASSIGNMENT);
  const [transferring, setTransferring] = useState(false);

  const loadAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await adminService.getExtensionAgents({
        search: search.trim() || undefined,
        region: regionFilter || undefined,
        woreda: woredaFilter || undefined,
        account_status: accountStatusFilter || undefined,
        professional_info_verified: verificationFilter
          ? verificationFilter === 'true'
          : undefined,
      });
      setAgents(list);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Unable to load extension agents.');
    } finally {
      setLoading(false);
    }
  }, [accountStatusFilter, regionFilter, search, verificationFilter, woredaFilter]);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => window.clearTimeout(timeoutId);
  }, [searchInput]);

  const clearCreateForm = () => {
    setFullName('');
    setPhoneNumber('');
    setEmail('');
    setEmployeeId('');
    setOrganization('');
    setVerificationMethod('email');
    setProfessionalInfoVerified(false);
    setPreferredLanguage('en');
    setCreateAssignment(EMPTY_ASSIGNMENT);
  };

  const handleCreateAgent = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!professionalInfoVerified) {
      notify('Confirm that the official professional information has been verified.', 'warning');
      return;
    }
    if (!createAssignment.region_id || !createAssignment.zone_id || !createAssignment.woreda_id) {
      notify('Select exactly one region, zone, and woreda.', 'warning');
      return;
    }

    const payload: CreateExtensionAgentPayload = {
      full_name: fullName.trim(),
      phone_number: phoneNumber.trim(),
      email: email.trim(),
      employee_id: employeeId.trim(),
      organization: organization.trim(),
      region_id: createAssignment.region_id,
      zone_id: createAssignment.zone_id,
      woreda_id: createAssignment.woreda_id,
      verification_method: verificationMethod,
      professional_info_verified: true,
      preferred_language: preferredLanguage,
    };

    setCreating(true);
    try {
      await adminService.createExtensionAgent(payload);
      notify('Verified extension agent created as pending activation; the code was sent.', 'success');
      setCreateOpen(false);
      clearCreateForm();
      await loadAgents();
    } catch (cause: unknown) {
      notify(cause instanceof Error ? cause.message : 'Failed to create extension agent.', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleResend = async (agent: ExtensionAgentRecord) => {
    setBusyAgentId(agent.agent_id);
    try {
      await adminService.resendExtensionAgentActivation(agent.agent_id);
      notify('Activation code submitted for delivery.', 'success');
    } catch (cause: unknown) {
      notify(cause instanceof Error ? cause.message : 'Could not resend activation code.', 'error');
    } finally {
      setBusyAgentId(null);
    }
  };

  const handleStatusChange = async (
    agent: ExtensionAgentRecord,
    accountStatus: 'active' | 'suspended',
  ) => {
    setBusyAgentId(agent.agent_id);
    try {
      await adminService.updateExtensionAgentStatus(agent.agent_id, accountStatus);
      notify(accountStatus === 'suspended' ? 'Extension agent suspended.' : 'Extension agent reactivated.', 'success');
      await loadAgents();
    } catch (cause: unknown) {
      notify(cause instanceof Error ? cause.message : 'Could not update extension-agent status.', 'error');
    } finally {
      setBusyAgentId(null);
    }
  };

  const openDetails = async (agent: ExtensionAgentRecord) => {
    setDetailsAgent(agent);
    setAssignmentHistory([]);
    setHistoryLoading(true);
    try {
      setAssignmentHistory(await adminService.getExtensionAgentAssignmentHistory(agent.agent_id));
    } catch (cause: unknown) {
      notify(cause instanceof Error ? cause.message : 'Could not load assignment history.', 'error');
    } finally {
      setHistoryLoading(false);
    }
  };

  const openTransfer = (agent: ExtensionAgentRecord) => {
    setTransferAgent(agent);
    setTransferAssignment({
      region_id: agent.region_id || '',
      zone_id: agent.zone_id || '',
      woreda_id: agent.woreda_id || '',
    });
  };

  const handleTransfer = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!transferAgent || !transferAssignment.region_id || !transferAssignment.zone_id || !transferAssignment.woreda_id) {
      notify('Select a complete region, zone, and woreda assignment.', 'warning');
      return;
    }

    setTransferring(true);
    try {
      await adminService.transferExtensionAgent(transferAgent.agent_id, transferAssignment);
      notify('Woreda assignment transferred and history recorded.', 'success');
      setTransferAgent(null);
      await loadAgents();
    } catch (cause: unknown) {
      notify(cause instanceof Error ? cause.message : 'Could not transfer extension agent.', 'error');
    } finally {
      setTransferring(false);
    }
  };

  return (
    <AppShell
      title={t('navAdminAgents')}
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadAgents()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 disabled:opacity-50"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Extension Agent</span>
          </button>
        </div>
      }
    >
      <div className="mb-6 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
        <div className="relative min-w-0">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search name, phone, email, employee ID..."
            aria-label="Search extension agents"
            className={`${inputClass} pl-9`}
          />
        </div>
        <input
          value={regionFilter}
          onChange={(event) => setRegionFilter(event.target.value.trimStart())}
          placeholder="Filter by region"
          aria-label="Filter by region"
          className={inputClass}
        />
        <input
          value={woredaFilter}
          onChange={(event) => setWoredaFilter(event.target.value.trimStart())}
          placeholder="Filter by woreda"
          aria-label="Filter by woreda"
          className={inputClass}
        />
        <select
          value={accountStatusFilter}
          onChange={(event) => setAccountStatusFilter(event.target.value)}
          aria-label="Filter by account activation status"
          className={inputClass}
        >
          <option value="">All account statuses</option>
          <option value="pending_activation">Pending activation</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
        <select
          value={verificationFilter}
          onChange={(event) => setVerificationFilter(event.target.value)}
          aria-label="Filter by professional verification"
          className={inputClass}
        >
          <option value="">All verification statuses</option>
          <option value="true">Professionally verified</option>
          <option value="false">Not professionally verified</option>
        </select>
      </div>

      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error ? (
        <ErrorState title="Could not load extension agents" message={error} onRetry={() => void loadAgents()} />
      ) : agents.length === 0 ? (
        <EmptyState
          title={search || regionFilter || woredaFilter ? 'No matching extension agents found' : 'No extension agents registered yet'}
          description="Provision verified woreda extension officers to monitor cases and support farmers in their assigned woreda."
          actionLabel="Create Extension Agent"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">Agent</th>
                  <th className="py-3 px-4">Official contact</th>
                  <th className="py-3 px-4">Employee / office</th>
                  <th className="py-3 px-4">Region / Zone / Woreda</th>
                  <th className="py-3 px-4">Professional verification</th>
                  <th className="py-3 px-4">Account</th>
                  <th className="py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-stone-900 dark:text-stone-100">{agent.full_name || '—'}</div>
                      <div className="text-xs text-stone-500">#{agent.agent_id}</div>
                    </td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                      <div>{agent.email || '—'}</div>
                      <div className="font-mono">{agent.phone_number || '—'}</div>
                    </td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                      <div>{agent.employee_id || '—'}</div>
                      <div>{agent.organization || '—'}</div>
                    </td>
                    <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                      {[agent.region, agent.zone, agent.woreda].filter(Boolean).join(' / ') || 'Unassigned'}
                    </td>
                    <td className="py-3 px-4">
                      {agent.professional_info_verified ? (
                        <div className="space-y-1">
                          <StatusBadge tone="green">Verified</StatusBadge>
                          <div className="text-[11px] text-stone-500">
                            By {agent.professional_info_verified_by || `admin #${agent.professional_info_verified_by_id ?? '—'}`}
                          </div>
                          <div className="text-[11px] text-stone-500">{formatDateTime(agent.professional_info_verified_at)}</div>
                        </div>
                      ) : <StatusBadge tone="amber">Not verified</StatusBadge>}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge tone={
                        agent.account_status === 'active' ? 'green'
                          : agent.account_status === 'pending_activation' ? 'amber' : 'red'
                      }>
                        {agent.account_status.replaceAll('_', ' ')}
                      </StatusBadge>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void openDetails(agent)}
                          className="text-xs text-emerald-800 dark:text-emerald-400 hover:underline"
                        >
                          Details
                        </button>
                        <button
                          type="button"
                          onClick={() => openTransfer(agent)}
                          className="text-xs text-emerald-800 dark:text-emerald-400 hover:underline"
                        >
                          Transfer
                        </button>
                        {agent.account_status === 'pending_activation' && (
                          <button
                            type="button"
                            onClick={() => void handleResend(agent)}
                            disabled={busyAgentId === agent.agent_id}
                            className="text-xs text-emerald-800 dark:text-emerald-400 hover:underline disabled:opacity-50"
                          >
                            {busyAgentId === agent.agent_id ? 'Sending...' : 'Resend code'}
                          </button>
                        )}
                        {agent.account_status === 'active' && (
                          <button
                            type="button"
                            onClick={() => void handleStatusChange(agent, 'suspended')}
                            disabled={busyAgentId === agent.agent_id}
                            className="text-xs text-red-700 dark:text-red-400 hover:underline disabled:opacity-50"
                          >
                            Suspend
                          </button>
                        )}
                        {agent.account_status === 'suspended' && (
                          <button
                            type="button"
                            onClick={() => void handleStatusChange(agent, 'active')}
                            disabled={busyAgentId === agent.agent_id}
                            className="text-xs text-emerald-800 dark:text-emerald-400 hover:underline disabled:opacity-50"
                          >
                            Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs" role="dialog" aria-modal="true">
          <div className="w-full max-w-3xl max-h-[92vh] overflow-y-auto rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-5 sm:p-6 shadow-xl">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">Create Extension Agent</h3>
                <p className="mt-1 text-xs text-stone-500">The agent receives a one-time code and sets their own password.</p>
              </div>
              <button type="button" onClick={() => setCreateOpen(false)} aria-label="Close form" className="text-stone-400 hover:text-stone-700">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateAgent} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                  Full name *
                  <input required maxLength={150} value={fullName} onChange={(event) => setFullName(event.target.value)} className={`${inputClass} mt-1`} />
                </label>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                  Official email address *
                  <input required type="email" maxLength={254} autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className={`${inputClass} mt-1`} />
                </label>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                  Phone number *
                  <input required type="tel" autoComplete="tel" value={phoneNumber} onChange={(event) => setPhoneNumber(event.target.value)} placeholder="+2519..." className={`${inputClass} mt-1 font-mono`} />
                </label>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                  Employee ID *
                  <input required maxLength={80} value={employeeId} onChange={(event) => setEmployeeId(event.target.value)} className={`${inputClass} mt-1`} />
                </label>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 sm:col-span-2">
                  Organization or agricultural office *
                  <input required maxLength={150} value={organization} onChange={(event) => setOrganization(event.target.value)} className={`${inputClass} mt-1`} />
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <GeographySelectors value={createAssignment} onChange={setCreateAssignment} />
                <div className="space-y-4">
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                    Verification method *
                    <select value={verificationMethod} onChange={(event) => setVerificationMethod(event.target.value as 'email' | 'sms')} className={`${inputClass} mt-1`}>
                      <option value="email">Email</option>
                      <option value="sms">SMS</option>
                    </select>
                  </label>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
                    Preferred language
                    <select value={preferredLanguage} onChange={(event) => setPreferredLanguage(event.target.value as 'en' | 'am')} className={`${inputClass} mt-1`}>
                      <option value="en">English</option>
                      <option value="am">አማርኛ</option>
                    </select>
                  </label>
                  <label className="flex items-start gap-2 rounded-lg border border-stone-200 dark:border-stone-700 p-3 text-xs text-stone-700 dark:text-stone-300">
                    <input
                      type="checkbox"
                      required
                      checked={professionalInfoVerified}
                      onChange={(event) => setProfessionalInfoVerified(event.target.checked)}
                      className="mt-0.5 accent-emerald-800"
                    />
                    <span>I have verified the agent’s official identity, employee ID, and agricultural office information.</span>
                  </label>
                </div>
              </div>

              <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-2">
                <button type="button" onClick={() => setCreateOpen(false)} className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 rounded-lg">
                  {t('cancel')}
                </button>
                <button type="submit" disabled={creating} className="px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50">
                  {creating ? 'Creating account...' : 'Verify and create account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {detailsAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" role="dialog" aria-modal="true">
          <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-xl bg-white dark:bg-[#121A16] p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100">Agent details and assignment history</h3>
              <button type="button" onClick={() => setDetailsAgent(null)} aria-label="Close details"><X className="w-4 h-4" /></button>
            </div>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5 text-xs">
              <div><dt className="text-stone-500">Name</dt><dd className="font-medium">{detailsAgent.full_name}</dd></div>
              <div><dt className="text-stone-500">Employee ID</dt><dd className="font-medium">{detailsAgent.employee_id || '—'}</dd></div>
              <div><dt className="text-stone-500">Email</dt><dd className="font-medium break-all">{detailsAgent.email || '—'}</dd></div>
              <div><dt className="text-stone-500">Phone</dt><dd className="font-medium">{detailsAgent.phone_number}</dd></div>
              <div><dt className="text-stone-500">Organization</dt><dd className="font-medium">{detailsAgent.organization || '—'}</dd></div>
              <div><dt className="text-stone-500">Assignment</dt><dd className="font-medium">{[detailsAgent.region, detailsAgent.zone, detailsAgent.woreda].filter(Boolean).join(' / ') || '—'}</dd></div>
              <div>
                <dt className="text-stone-500">Professional verification</dt>
                <dd className="font-medium">
                  {detailsAgent.professional_info_verified
                    ? `Verified by ${detailsAgent.professional_info_verified_by || `admin #${detailsAgent.professional_info_verified_by_id ?? '—'}`} on ${formatDateTime(detailsAgent.professional_info_verified_at)}`
                    : 'Not verified'}
                </dd>
              </div>
              <div><dt className="text-stone-500">Account status</dt><dd className="font-medium">{detailsAgent.account_status.replaceAll('_', ' ')}</dd></div>
            </dl>
            <h4 className="mt-6 mb-2 text-sm font-semibold">Woreda assignment history</h4>
            {historyLoading ? <LoadingSkeleton rows={2} /> : assignmentHistory.length === 0 ? (
              <p className="text-xs text-stone-500">No assignment history is available.</p>
            ) : (
              <ol className="space-y-3">
                {assignmentHistory.map((item) => (
                  <li key={item.id} className="rounded-lg border border-stone-200 dark:border-stone-700 p-3 text-xs">
                    <div className="font-medium">{item.previous_woreda || 'Initial assignment'} → {item.new_woreda}</div>
                    <div className="mt-1 text-stone-500">{item.changed_by_admin || 'System import'} · {formatDateTime(item.changed_at)}</div>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}

      {transferAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" role="dialog" aria-modal="true">
          <form onSubmit={handleTransfer} className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-white dark:bg-[#121A16] p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-stone-900 dark:text-stone-100">Transfer agent assignment</h3>
                <p className="mt-1 text-xs text-stone-500">{transferAgent.full_name}</p>
              </div>
              <button type="button" onClick={() => setTransferAgent(null)} aria-label="Close transfer"><X className="w-4 h-4" /></button>
            </div>
            <GeographySelectors value={transferAssignment} onChange={setTransferAssignment} />
            <p className="text-xs text-stone-500">The new woreda takes effect immediately. The previous assignment will remain in history.</p>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setTransferAgent(null)} className="px-4 py-2 text-xs bg-stone-100 dark:bg-stone-800 rounded-lg">{t('cancel')}</button>
              <button type="submit" disabled={transferring} className="px-4 py-2 text-xs text-white bg-emerald-900 rounded-lg disabled:opacity-50">
                {transferring ? 'Transferring...' : 'Confirm transfer'}
              </button>
            </div>
          </form>
        </div>
      )}
    </AppShell>
  );
};
