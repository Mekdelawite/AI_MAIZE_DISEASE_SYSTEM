import React, { useState } from 'react';
import { ArrowLeft, RefreshCw, Send } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ConfirmDialog } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';

type SmsMode = 'direct' | 'disease' | 'outbreak' | 'retry';

export const OutbreakSmsPage: React.FC = () => {
  const { notify } = useApp();
  const [mode, setMode] = useState<SmsMode>('direct');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [disease, setDisease] = useState('');
  const [confidence, setConfidence] = useState('');
  const [region, setRegion] = useState('');
  const [woreda, setWoreda] = useState('');
  const [retryId, setRetryId] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [outcome, setOutcome] = useState<{ status: 'success' | 'error'; text: string; failedId?: string | number } | null>(null);

  const dispatch = async () => {
    setSending(true);
    setOutcome(null);
    try {
      let result: any;
      if (mode === 'direct') {
        result = await adminService.sendDirectSms({ recipient_phone: phone.trim(), message: message.trim() });
      } else if (mode === 'disease') {
        result = await adminService.sendDiseaseAlertSms({
          recipient_phone: phone.trim(), disease_name: disease.trim(), confidence: Number(confidence),
          region: region.trim() || undefined, woreda: woreda.trim() || undefined, message: message.trim() || undefined,
        });
      } else if (mode === 'outbreak') {
        result = await adminService.sendOutbreakAlertSms({
          recipient_phone: phone.trim(), disease_name: disease.trim(),
          location: [woreda.trim(), region.trim()].filter(Boolean).join(', '),
          region: region.trim() || undefined, woreda: woreda.trim() || undefined, message: message.trim() || undefined,
        });
      } else {
        result = await adminService.retryFailedSms({ sms_record_id: retryId.trim() });
      }

      const succeeded = result?.success !== false && result?.status !== 'failed';
      const text = result?.error || result?.message || (succeeded ? 'SMS request accepted by the server.' : 'SMS request failed.');
      setOutcome({ status: succeeded ? 'success' : 'error', text, failedId: result?.sms_record_id ?? result?.sms_id ?? result?.log_id });
      notify(text, succeeded ? 'success' : 'warning');
    } catch (error: any) {
      const text = error?.message || 'SMS request failed on the server.';
      setOutcome({ status: 'error', text });
      notify(text, 'error');
    } finally {
      setSending(false);
      setConfirmOpen(false);
    }
  };

  const inputClass = 'mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm dark:border-stone-700 dark:bg-stone-900';

  return <AppShell
    title="SMS Notification Dispatch"
    subtitle="Send direct, disease, or outbreak SMS messages, or retry a failed delivery. Sandbox messages appear in the Africa’s Talking simulator."
    actions={<Link to="/admin/outbreaks" className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-xs font-semibold text-stone-700 dark:border-stone-700 dark:text-stone-200"><ArrowLeft className="h-4 w-4" />Back to Outbreak Alerts</Link>}
  >
    <div className="max-w-3xl space-y-5 rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121A16] sm:p-7">
      <div className="flex flex-wrap gap-1 rounded-lg bg-stone-100 p-1 dark:bg-stone-800">
        {([
          ['direct', 'Direct SMS'], ['disease', 'Disease Alert'], ['outbreak', 'Outbreak Alert'], ['retry', 'Retry Failed SMS'],
        ] as const).map(([value, label]) => <button type="button" key={value} onClick={() => { setMode(value); setOutcome(null); }} className={`flex-1 rounded-md px-3 py-2 text-xs font-medium ${mode === value ? 'bg-white text-stone-900 shadow-sm dark:bg-stone-900 dark:text-stone-100' : 'text-stone-600 dark:text-stone-400'}`}>{label}</button>)}
      </div>

      {outcome && <div role="status" className={`space-y-2 rounded-lg border p-3.5 text-sm ${outcome.status === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200' : 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200'}`}>
        <p>{outcome.text}</p>
        {outcome.status === 'error' && outcome.failedId && <button type="button" onClick={() => { setRetryId(String(outcome.failedId)); setMode('retry'); }} className="inline-flex items-center gap-1 font-semibold underline"><RefreshCw className="h-3 w-3" />Retry record #{outcome.failedId}</button>}
      </div>}

      <form onSubmit={(event) => { event.preventDefault(); setConfirmOpen(true); }} className="space-y-4">
        {mode === 'direct' && <>
          <label className="block text-xs font-medium">Recipient Phone Number *<input required type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+251911000000" className={`${inputClass} font-mono`} /></label>
          <label className="block text-xs font-medium">SMS Message *<textarea required rows={4} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Enter an agricultural advisory message..." className={inputClass} /></label>
        </>}

        {mode === 'disease' && <>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs font-medium">Disease Class *<input required value={disease} onChange={(event) => setDisease(event.target.value)} placeholder="e.g. Common_Rust" className={inputClass} /></label>
            <label className="text-xs font-medium">Confidence (%) *<input required type="number" min="0" max="100" step="0.01" value={confidence} onChange={(event) => setConfidence(event.target.value)} placeholder="e.g. 92.5" className={`${inputClass} font-mono`} /></label>
            <label className="text-xs font-medium">Recipient Phone Number *<input required type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+251911000000" className={`${inputClass} font-mono`} /></label>
            <label className="text-xs font-medium">Region (Optional)<input value={region} onChange={(event) => setRegion(event.target.value)} className={inputClass} /></label>
            <label className="text-xs font-medium">Woreda (Optional)<input value={woreda} onChange={(event) => setWoreda(event.target.value)} className={inputClass} /></label>
          </div>
          <label className="block text-xs font-medium">Custom Message (Optional)<textarea rows={3} value={message} onChange={(event) => setMessage(event.target.value)} className={inputClass} /></label>
        </>}

        {mode === 'outbreak' && <>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs font-medium">Recipient Phone Number *<input required type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+251911000000" className={`${inputClass} font-mono`} /></label>
            <label className="text-xs font-medium">Disease Class *<input required value={disease} onChange={(event) => setDisease(event.target.value)} placeholder="e.g. Common_Rust" className={inputClass} /></label>
            <label className="text-xs font-medium">Region *<input required value={region} onChange={(event) => setRegion(event.target.value)} className={inputClass} /></label>
            <label className="text-xs font-medium">Woreda (Optional)<input value={woreda} onChange={(event) => setWoreda(event.target.value)} className={inputClass} /></label>
          </div>
          <label className="block text-xs font-medium">Custom Message (Optional)<textarea rows={3} value={message} onChange={(event) => setMessage(event.target.value)} className={inputClass} /></label>
        </>}

        {mode === 'retry' && <label className="block text-xs font-medium">Failed SMS Record ID *<input required value={retryId} onChange={(event) => setRetryId(event.target.value)} placeholder="Enter the failed SMS record ID" className={`${inputClass} font-mono`} /></label>}

        <button type="submit" disabled={sending} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-800 px-4 py-3 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50"><Send className="h-4 w-4" />{mode === 'retry' ? 'Retry Failed SMS' : 'Dispatch SMS'}</button>
      </form>
    </div>
    <ConfirmDialog open={confirmOpen} title="Confirm SMS Dispatch" description="Submit this SMS request to the Flask backend? Sandbox messages are routed to the Africa’s Talking simulator." confirmLabel="Submit SMS Request" loading={sending} onConfirm={dispatch} onCancel={() => setConfirmOpen(false)} />
  </AppShell>;
};
