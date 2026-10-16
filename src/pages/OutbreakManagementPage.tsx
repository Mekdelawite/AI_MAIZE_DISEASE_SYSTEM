import React, { useCallback, useEffect, useState } from 'react';
import { AlertOctagon, Plus, RefreshCw, ShieldAlert, X } from 'lucide-react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';
import { OutbreakAlert } from '../types/api';
import { formatDateTime } from '../utils/media';

export const OutbreakManagementPage: React.FC = () => {
  const { t, notify } = useApp();

  const [alerts, setAlerts] = useState<OutbreakAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [regionFilter, setRegionFilter] = useState('');
  const [diseaseFilter, setDiseaseFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');

  // Detail View
  const [selectedAlert, setSelectedAlert] = useState<OutbreakAlert | null>(null);

  // Manual Alert Form & Confirmation
  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [manDisease, setManDisease] = useState('');
  const [manRegion, setManRegion] = useState('Oromia');
  const [manWoreda, setManWoreda] = useState('');
  const [manKebele, setManKebele] = useState('');
  const [manRiskLevel, setManRiskLevel] = useState('high');
  const [manRiskScore, setManRiskScore] = useState('');
  const [manMessage, setManMessage] = useState('');
  const [confirmManualOpen, setConfirmManualOpen] = useState(false);
  const [submittingManual, setSubmittingManual] = useState(false);

  // Automatic Evaluation Form & Confirmation
  const [autoModalOpen, setAutoModalOpen] = useState(false);
  const [autoDisease, setAutoDisease] = useState('');
  const [autoRegion, setAutoRegion] = useState('Oromia');
  const [autoWoreda, setAutoWoreda] = useState('');
  const [autoDays, setAutoDays] = useState('14');
  const [confirmAutoOpen, setConfirmAutoOpen] = useState(false);
  const [submittingAuto, setSubmittingAuto] = useState(false);
  const [lastOutcomeMessage, setLastOutcomeMessage] = useState<string | null>(null);

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await adminService.getOutbreakAlerts({
        region: regionFilter.trim() || undefined,
        disease_class: diseaseFilter.trim() || undefined,
        risk_level: riskFilter || undefined,
      });
      setAlerts(list);
    } catch (err: any) {
      setError(err?.message || 'Unable to load outbreak alerts from /api/outbreak-alerts.');
    } finally {
      setLoading(false);
    }
  }, [regionFilter, diseaseFilter, riskFilter]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleInspectAlert = async (alertId: string | number) => {
    try {
      const detail = await adminService.getOutbreakAlertDetail(alertId);
      setSelectedAlert(detail);
    } catch (err: any) {
      notify(err?.message || 'Could not load outbreak alert detail.', 'error');
    }
  };

  const executeManualAlert = async () => {
    setSubmittingManual(true);
    setLastOutcomeMessage(null);
    try {
      const res = await adminService.createManualOutbreakAlert({
        disease_class: manDisease.trim(),
        region: manRegion.trim(),
        woreda: manWoreda.trim() || undefined,
        kebele: manKebele.trim() || undefined,
        risk_level: manRiskLevel || undefined,
        risk_score: manRiskScore.trim() ? Number(manRiskScore) : undefined,
        message: manMessage.trim() || undefined,
      });
      const outcome = res?.message || 'Manual outbreak alert created and confirmed by server.';
      setLastOutcomeMessage(outcome);
      notify(outcome, 'success');
      setConfirmManualOpen(false);
      setManualModalOpen(false);
      loadAlerts();
    } catch (err: any) {
      notify(err?.message || 'Manual outbreak creation failed on server.', 'error');
      setConfirmManualOpen(false);
    } finally {
      setSubmittingManual(false);
    }
  };

  const executeAutoEvaluation = async () => {
    setSubmittingAuto(true);
    setLastOutcomeMessage(null);
    try {
      const res = await adminService.runAutomaticOutbreakEvaluation({
        disease_class: autoDisease.trim(),
        region: autoRegion.trim(),
        woreda: autoWoreda.trim() || undefined,
        analysis_period_days: autoDays.trim() ? Number(autoDays) : undefined,
      });
      const outcome =
        res?.message ||
        (res?.outbreak_detected
          ? 'Automatic evaluation confirmed an outbreak alert threshold.'
          : 'Automatic evaluation completed by server. Inspect alert list for newly generated alerts.');
      setLastOutcomeMessage(outcome);
      notify(outcome, 'info');
      setConfirmAutoOpen(false);
      setAutoModalOpen(false);
      loadAlerts();
    } catch (err: any) {
      notify(err?.message || 'Automatic outbreak evaluation failed on server.', 'error');
      setConfirmAutoOpen(false);
    } finally {
      setSubmittingAuto(false);
    }
  };

  return (
    <AppShell
      title={t('navAdminOutbreaks')}
      subtitle="Monitor regional maize disease outbreak alerts, trigger manual alerts, or run automatic epidemiological threshold evaluations."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={loadAlerts}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <button
            type="button"
            onClick={() => setAutoModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-800 dark:text-stone-100 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg cursor-pointer whitespace-nowrap"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
            <span>Automatic Evaluation</span>
          </button>
          <button
            type="button"
            onClick={() => setManualModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Manual Outbreak Alert</span>
          </button>
        </div>
      }
    >
      {lastOutcomeMessage && (
        <div className="mb-6 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 p-4 text-xs text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
          <span>Server Outcome: {lastOutcomeMessage}</span>
          <button
            type="button"
            onClick={() => setLastOutcomeMessage(null)}
            className="text-stone-500 hover:text-stone-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 grid grid-cols-1 sm:grid-cols-4 gap-3">
        <input
          type="text"
          value={diseaseFilter}
          onChange={(e) => setDiseaseFilter(e.target.value)}
          placeholder="Filter by Disease Class..."
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
        <input
          type="text"
          value={regionFilter}
          onChange={(e) => setRegionFilter(e.target.value)}
          placeholder="Filter by Region..."
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        />
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          aria-label="Filter by risk level"
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
        >
          <option value="">All Risk Levels</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <button
          type="button"
          onClick={loadAlerts}
          className="py-1.5 px-3 text-xs font-semibold text-white bg-emerald-800 rounded-lg cursor-pointer"
        >
          Apply Filters
        </button>
      </div>

      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : error ? (
        <ErrorState title="Could not load outbreak alerts" message={error} onRetry={loadAlerts} />
      ) : alerts.length === 0 ? (
        <EmptyState
          title="No outbreak alerts recorded"
          description="Alerts returned by GET /api/outbreak-alerts will be listed here."
        />
      ) : (
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-800 text-xs font-semibold text-stone-500 bg-stone-50/60 dark:bg-stone-900/40">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Disease Class</th>
                  <th className="py-3 px-4">Region · Woreda</th>
                  <th className="py-3 px-4">Risk Level · Score</th>
                  <th className="py-3 px-4">Trigger</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {alerts.map((al) => {
                  const alertId = al.alert_id ?? al.id;
                  const risk = (al.risk_level || 'medium').toLowerCase();
                  const riskColor =
                    risk === 'critical' || risk === 'high'
                      ? 'text-red-700 dark:text-red-400 font-semibold'
                      : risk === 'medium'
                      ? 'text-amber-700 dark:text-amber-400 font-semibold'
                      : 'text-emerald-800 dark:text-emerald-400';

                  return (
                    <tr
                      key={String(alertId)}
                      onClick={() => handleInspectAlert(alertId)}
                      className="hover:bg-stone-50/80 dark:hover:bg-stone-800/40 cursor-pointer"
                    >
                      <td className="py-3 px-4 font-mono tabular-nums text-xs text-stone-500">
                        #{alertId}
                      </td>
                      <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                        {al.disease_class}
                      </td>
                      <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                        {al.region} {al.woreda ? `· ${al.woreda}` : ''}
                      </td>
                      <td className="py-3 px-4 text-xs">
                        <span className={`uppercase ${riskColor}`}>{al.risk_level || '—'}</span>
                        {al.risk_score !== undefined && (
                          <span className="font-mono tabular-nums text-stone-500">
                            {' '}
                            · Score: {al.risk_score}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs text-stone-600 dark:text-stone-400">
                        {al.trigger_type || '—'}
                      </td>
                      <td className="py-3 px-4 text-xs font-mono tabular-nums text-stone-500">
                        {formatDateTime(al.created_at)}
                      </td>
                      <td className="py-3 px-4 text-right text-xs font-semibold text-emerald-800 dark:text-emerald-400">
                        Inspect
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-mono text-stone-500">
                  Alert #{selectedAlert.alert_id ?? selectedAlert.id}
                </span>
                <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                  {selectedAlert.disease_class}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedAlert(null)}
                className="text-stone-400 hover:text-stone-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs space-y-2 text-stone-600 dark:text-stone-300">
              <p>
                <strong>Location:</strong> {selectedAlert.region}
                {selectedAlert.woreda ? ` · ${selectedAlert.woreda}` : ''}
                {selectedAlert.kebele ? ` · ${selectedAlert.kebele}` : ''}
              </p>
              <p>
                <strong>Risk Level:</strong> {selectedAlert.risk_level || '—'}{' '}
                {selectedAlert.risk_score !== undefined ? `(Score: ${selectedAlert.risk_score})` : ''}
              </p>
              {selectedAlert.case_count !== undefined && (
                <p>
                  <strong>Case Count:</strong> {selectedAlert.case_count}
                </p>
              )}
              {(selectedAlert.message || selectedAlert.description) && (
                <p className="pt-2 border-t border-stone-200 dark:border-stone-800">
                  {selectedAlert.message || selectedAlert.description}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Manual Outbreak Modal */}
      {manualModalOpen && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-lg rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-red-700" />
                <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                  Create Manual Outbreak Alert (/api/outbreak-alerts/manual)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setManualModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!manDisease.trim() || !manRegion.trim()) {
                  notify('Disease class and region are required.', 'warning');
                  return;
                }
                setConfirmManualOpen(true);
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Disease Class *</label>
                  <input
                    type="text"
                    required
                    value={manDisease}
                    onChange={(e) => setManDisease(e.target.value)}
                    placeholder="e.g. Northern_Leaf_Blight"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Region *</label>
                  <input
                    type="text"
                    required
                    value={manRegion}
                    onChange={(e) => setManRegion(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Woreda (Optional)</label>
                  <input
                    type="text"
                    value={manWoreda}
                    onChange={(e) => setManWoreda(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Kebele (Optional)</label>
                  <input
                    type="text"
                    value={manKebele}
                    onChange={(e) => setManKebele(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Risk Level</label>
                  <select
                    value={manRiskLevel}
                    onChange={(e) => setManRiskLevel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Risk Score (Optional)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={manRiskScore}
                    onChange={(e) => setManRiskScore(e.target.value)}
                    placeholder="e.g. 0.85"
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1">Advisory Message (Optional)</label>
                <textarea
                  rows={2}
                  value={manMessage}
                  onChange={(e) => setManMessage(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setManualModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 rounded-lg cursor-pointer"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-red-700 hover:bg-red-600 rounded-lg cursor-pointer"
                >
                  Review & Trigger Alert
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Automatic Outbreak Evaluation Modal */}
      {autoModalOpen && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                Automatic Outbreak Evaluation (/api/outbreak-alerts/automatic)
              </h3>
              <button
                type="button"
                onClick={() => setAutoModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!autoDisease.trim() || !autoRegion.trim()) {
                  notify('Disease class and region are required.', 'warning');
                  return;
                }
                setConfirmAutoOpen(true);
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium mb-1">Disease Class *</label>
                <input
                  type="text"
                  required
                  value={autoDisease}
                  onChange={(e) => setAutoDisease(e.target.value)}
                  placeholder="e.g. Gray_Leaf_Spot"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div>
                <label className="block text-xs font-medium mb-1">Region *</label>
                <input
                  type="text"
                  required
                  value={autoRegion}
                  onChange={(e) => setAutoRegion(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Woreda (Optional)</label>
                  <input
                    type="text"
                    value={autoWoreda}
                    onChange={(e) => setAutoWoreda(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Analysis Window (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="90"
                    value={autoDays}
                    onChange={(e) => setAutoDays(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setAutoModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 rounded-lg cursor-pointer"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer"
                >
                  Run Evaluation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialogs */}
      <ConfirmDialog
        open={confirmManualOpen}
        title="Confirm Manual Outbreak Alert"
        description={`Trigger a manual ${manRiskLevel.toUpperCase()} outbreak alert for ${manDisease} in ${manRegion}${
          manWoreda ? ` (${manWoreda})` : ''
        }? This action may dispatch notifications to opted-in farmers and extension officers.`}
        confirmLabel="Confirm & Create Alert"
        variant="danger"
        loading={submittingManual}
        onConfirm={executeManualAlert}
        onCancel={() => setConfirmManualOpen(false)}
      />

      <ConfirmDialog
        open={confirmAutoOpen}
        title="Confirm Automatic Outbreak Evaluation"
        description={`Execute automatic outbreak threshold analysis for ${autoDisease} in ${autoRegion} over the past ${autoDays} day(s)?`}
        confirmLabel="Execute Evaluation"
        variant="primary"
        loading={submittingAuto}
        onConfirm={executeAutoEvaluation}
        onCancel={() => setConfirmAutoOpen(false)}
      />
    </AppShell>
  );
};
