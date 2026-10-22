import React, { useState } from 'react';
import { CheckCircle2, Download, FileSpreadsheet, FileText, RefreshCw, Send } from 'lucide-react';
import { ConfirmDialog } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';

export const ReportsPage: React.FC = () => {
  const { t, notify } = useApp();

  // Report Export State
  const [diseaseClass, setDiseaseClass] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'csv' | null>(null);
  const [reportOutcome, setReportOutcome] = useState<string | null>(null);

  // SMS Services State
  const [smsTab, setSmsTab] = useState<'direct' | 'disease' | 'outbreak' | 'retry'>('direct');
  const [smsPhone, setSmsPhone] = useState('');
  const [smsMessage, setSmsMessage] = useState('');
  const [smsDiseaseClass, setSmsDiseaseClass] = useState('');
  const [smsDiagnosisId, setSmsDiagnosisId] = useState('');
  const [smsAlertId, setSmsAlertId] = useState('');
  const [smsRegion, setSmsRegion] = useState('');
  const [smsWoreda, setSmsWoreda] = useState('');
  const [retrySmsId, setRetrySmsId] = useState('');

  const [confirmSmsOpen, setConfirmSmsOpen] = useState(false);
  const [sendingSms, setSendingSms] = useState(false);
  const [smsServerResponse, setSmsServerResponse] = useState<{
    status: 'success' | 'error';
    text: string;
    failedSmsId?: string | number;
  } | null>(null);

  const handleDownloadReport = async (format: 'pdf' | 'csv') => {
    setDownloadingFormat(format);
    setReportOutcome(null);
    try {
      const filters = {
        disease_class: diseaseClass.trim() || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };

      const { blob, filename } =
        format === 'pdf'
          ? await adminService.downloadPdfReport(filters)
          : await adminService.downloadCsvReport(filters);

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setReportOutcome(`Downloaded verified ${format.toUpperCase()} report (${filename}, ${(blob.size / 1024).toFixed(1)} KB).`);
      notify(`${format.toUpperCase()} report downloaded from server.`, 'success');
    } catch (err: any) {
      notify(err?.message || `Failed to download ${format.toUpperCase()} report.`, 'error');
    } finally {
      setDownloadingFormat(null);
    }
  };

  const executeSmsRequest = async () => {
    setSendingSms(true);
    setSmsServerResponse(null);
    try {
      let res: any;
      if (smsTab === 'direct') {
        res = await adminService.sendDirectSms({
          phone_number: smsPhone.trim(),
          message: smsMessage.trim(),
        });
      } else if (smsTab === 'disease') {
        res = await adminService.sendDiseaseAlertSms({
          diagnosis_id: smsDiagnosisId.trim() || undefined,
          phone_number: smsPhone.trim() || undefined,
          disease_class: smsDiseaseClass.trim(),
          region: smsRegion.trim() || undefined,
          woreda: smsWoreda.trim() || undefined,
          message: smsMessage.trim() || undefined,
        });
      } else if (smsTab === 'outbreak') {
        res = await adminService.sendOutbreakAlertSms({
          alert_id: smsAlertId.trim() || undefined,
          disease_class: smsDiseaseClass.trim() || undefined,
          region: smsRegion.trim() || undefined,
          woreda: smsWoreda.trim() || undefined,
          message: smsMessage.trim() || undefined,
        });
      } else {
        res = await adminService.retryFailedSms({
          sms_id: retrySmsId.trim(),
          log_id: retrySmsId.trim(),
        });
      }

      const providerDelivered = res?.delivered !== false && res?.status !== 'failed';
      const msg =
        res?.message ||
        (providerDelivered
          ? 'SMS dispatch confirmed by server.'
          : 'Request processed, but SMS provider reported delivery failure.');

      setSmsServerResponse({
        status: providerDelivered ? 'success' : 'error',
        text: msg,
        failedSmsId: res?.sms_id ?? res?.log_id,
      });

      notify(msg, providerDelivered ? 'success' : 'warning');
    } catch (err: any) {
      setSmsServerResponse({
        status: 'error',
        text: err?.message || 'SMS request failed on server.',
      });
      notify(err?.message || 'SMS dispatch failed.', 'error');
    } finally {
      setSendingSms(false);
      setConfirmSmsOpen(false);
    }
  };

  return (
    <AppShell
      title={t('navAdminReports')}
      subtitle="Export authenticated binary PDF & CSV diagnostic reports and dispatch SMS notifications via verified backend endpoints."
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Administrative Reports (PDF & CSV) */}
        <div className="lg:col-span-6 space-y-6">
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-5">
            <div>
              <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                Administrative Diagnostic Reports
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                  Filter by Disease Class (Optional)
                </label>
                <input
                  type="text"
                  value={diseaseClass}
                  onChange={(e) => setDiseaseClass(e.target.value)}
                  placeholder="e.g. Common_Rust, Northern_Leaf_Blight, Healthy"
                  className="w-full px-3.5 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    Start Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                    End Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              </div>
            </div>

            {reportOutcome && (
              <div className="rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 p-3.5 flex items-center gap-2 text-xs text-emerald-900 dark:text-emerald-200">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{reportOutcome}</span>
              </div>
            )}

            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={downloadingFormat !== null}
                onClick={() => handleDownloadReport('pdf')}
                className="flex-1 inline-flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50 cursor-pointer whitespace-nowrap"
              >
                <FileText className="w-4 h-4" />
                <span>
                  {downloadingFormat === 'pdf' ? 'Downloading PDF...' : 'Download PDF Report'}
                </span>
              </button>

              <button
                type="button"
                disabled={downloadingFormat !== null}
                onClick={() => handleDownloadReport('csv')}
                className="flex-1 inline-flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-semibold text-stone-800 dark:text-stone-100 border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg disabled:opacity-50 cursor-pointer whitespace-nowrap"
              >
                <FileSpreadsheet className="w-4 h-4" />
                <span>
                  {downloadingFormat === 'csv' ? 'Downloading CSV...' : 'Download CSV Dataset'}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Right: SMS Notification Services */}
        <div className="lg:col-span-6 space-y-6">
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 space-y-5">
            <div>
              <h2 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                SMS Notification Dispatch
              </h2>
              <p className="mt-1 text-xs text-stone-500">
                Restricted to authorized extension agents and administrators.
              </p>
            </div>

            {/* Segmented Mode Tabs */}
            <div className="flex flex-wrap items-center gap-1 p-1 rounded-lg bg-stone-100 dark:bg-stone-800">
              {[
                { id: 'direct', label: 'Direct SMS' },
                { id: 'disease', label: 'Disease Alert' },
                { id: 'outbreak', label: 'Outbreak Alert' },
                { id: 'retry', label: 'Retry Failed SMS' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    setSmsTab(tab.id as any);
                    setSmsServerResponse(null);
                  }}
                  className={`flex-1 py-1.5 px-2.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                    smsTab === tab.id
                      ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                      : 'text-stone-600 dark:text-stone-400'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {smsServerResponse && (
              <div
                className={`rounded-lg border p-3.5 text-xs space-y-2 ${
                  smsServerResponse.status === 'success'
                    ? 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 text-emerald-900 dark:text-emerald-200'
                    : 'border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/30 text-red-800 dark:text-red-200'
                }`}
              >
                <p>{smsServerResponse.text}</p>
                {smsServerResponse.status === 'error' && smsServerResponse.failedSmsId && (
                  <button
                    type="button"
                    onClick={() => {
                      setRetrySmsId(String(smsServerResponse.failedSmsId));
                      setSmsTab('retry');
                    }}
                    className="inline-flex items-center gap-1 font-semibold underline cursor-pointer"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Retry Eligible Record #{smsServerResponse.failedSmsId}</span>
                  </button>
                )}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setConfirmSmsOpen(true);
              }}
              className="space-y-4"
            >
              {smsTab === 'direct' && (
                <>
                  <div>
                    <label className="block text-xs font-medium mb-1">
                      Recipient Phone Number * (<code className="font-mono">/api/sms/send</code>)
                    </label>
                    <input
                      type="tel"
                      required
                      value={smsPhone}
                      onChange={(e) => setSmsPhone(e.target.value)}
                      placeholder="+251911000000"
                      className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1">SMS Message *</label>
                    <textarea
                      rows={3}
                      required
                      value={smsMessage}
                      onChange={(e) => setSmsMessage(e.target.value)}
                      placeholder="Enter agricultural advisory message..."
                      className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                    />
                  </div>
                </>
              )}

              {smsTab === 'disease' && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium mb-1">Disease Class *</label>
                      <input
                        type="text"
                        required
                        value={smsDiseaseClass}
                        onChange={(e) => setSmsDiseaseClass(e.target.value)}
                        placeholder="e.g. Common_Rust"
                        className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Diagnosis ID (Optional)</label>
                      <input
                        type="text"
                        value={smsDiagnosisId}
                        onChange={(e) => setSmsDiagnosisId(e.target.value)}
                        className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium mb-1">Phone Number (Optional)</label>
                      <input
                        type="tel"
                        value={smsPhone}
                        onChange={(e) => setSmsPhone(e.target.value)}
                        className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Region (Optional)</label>
                      <input
                        type="text"
                        value={smsRegion}
                        onChange={(e) => setSmsRegion(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1">Custom Message (Optional)</label>
                    <textarea
                      rows={2}
                      value={smsMessage}
                      onChange={(e) => setSmsMessage(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                    />
                  </div>
                </>
              )}

              {smsTab === 'outbreak' && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium mb-1">Outbreak Alert ID</label>
                      <input
                        type="text"
                        value={smsAlertId}
                        onChange={(e) => setSmsAlertId(e.target.value)}
                        placeholder="Alert ID"
                        className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Disease Class</label>
                      <input
                        type="text"
                        value={smsDiseaseClass}
                        onChange={(e) => setSmsDiseaseClass(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium mb-1">Region</label>
                      <input
                        type="text"
                        value={smsRegion}
                        onChange={(e) => setSmsRegion(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Woreda</label>
                      <input
                        type="text"
                        value={smsWoreda}
                        onChange={(e) => setSmsWoreda(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                    </div>
                  </div>
                </>
              )}

              {smsTab === 'retry' && (
                <div>
                  <label className="block text-xs font-medium mb-1">
                    Failed SMS Record ID * (<code className="font-mono">POST /api/sms/retry</code>)
                  </label>
                  <input
                    type="text"
                    required
                    value={retrySmsId}
                    onChange={(e) => setRetrySmsId(e.target.value)}
                    placeholder="Enter failed SMS log ID returned by backend"
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                  />
                </div>
              )}

              <button
                type="submit"
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>
                  {smsTab === 'retry' ? 'Retry Failed SMS Delivery' : 'Dispatch SMS Request'}
                </span>
              </button>
            </form>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmSmsOpen}
        title="Confirm SMS Dispatch"
        description="Submit this SMS notification request to the Flask backend? Delivery status will only be confirmed once the server and SMS gateway respond."
        confirmLabel="Submit SMS Request"
        loading={sendingSms}
        onConfirm={executeSmsRequest}
        onCancel={() => setConfirmSmsOpen(false)}
      />
    </AppShell>
  );
};
