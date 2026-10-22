import React, { useState } from 'react';
import { ArrowLeft, BellRing, Send } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';

const REGIONS = ['Oromia', 'Amhara', 'SNNPR', 'Sidama', 'South West Ethiopia', 'Tigray', 'Benishangul-Gumuz', 'Gambela', 'Somali', 'Afar', 'Harari', 'Dire Dawa', 'Addis Ababa'];

export const RegionalAlertPage: React.FC = () => {
  const { notify } = useApp();
  const [regions, setRegions] = useState<string[]>([]);
  const [messageEn, setMessageEn] = useState('');
  const [messageAm, setMessageAm] = useState('');
  const [method, setMethod] = useState<'sms' | 'app' | 'both'>('both');
  const [sending, setSending] = useState(false);
  const [outcome, setOutcome] = useState('');

  const toggleRegion = (region: string) => setRegions((selected) => selected.includes(region)
    ? selected.filter((item) => item !== region) : [...selected, region]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!regions.length || !messageEn.trim() || !messageAm.trim()) return;
    if (!window.confirm(`Send this alert to all registered farmers in ${regions.join(', ')}?`)) return;
    setSending(true);
    setOutcome('');
    try {
      const result = await adminService.sendRegionalAlert({ regions, message_en: messageEn.trim(), message_am: messageAm.trim(), method });
      if (result?.code === 'NO_FARMERS') {
        setOutcome('No farmers registered in this region.');
        notify('No farmers registered in this region.', 'warning');
      } else {
        const farmerCount = result?.farmer_count ?? 0;
        const smsSummary = method === 'app' ? '' : ` SMS provider accepted ${result?.sms_accepted ?? 0}, pending ${result?.sms_pending ?? 0}, failed ${result?.sms_failed ?? 0}.`;
        const message = method === 'sms'
          ? `SMS requests processed for ${farmerCount} farmers.${smsSummary}`
          : `App notification and community alert created for ${farmerCount} farmers.${smsSummary}`;
        setOutcome(message);
        const smsIssue = method !== 'app' && ((result?.sms_failed ?? 0) > 0 || (result?.sms_pending ?? 0) > 0);
        notify(message, smsIssue ? 'warning' : 'success');
        if (method !== 'app' && Array.isArray(result?.sms_results)) {
          const details = result.sms_results.map((item: any) => `${item.phone}: ${item.status}${item.provider_status_code ? ` (${item.provider_status_code})` : ''}${item.provider_message_id ? ` ID ${item.provider_message_id}` : ''}${item.error ? ` — ${item.error}` : ''}`).join('\n');
          if (details) setOutcome(`${message}\n${details}`);
        }
        setMessageEn(''); setMessageAm(''); setRegions([]);
      }
    } catch (error: any) {
      notify(error?.message || 'Unable to send the regional alert.', 'error');
    } finally { setSending(false); }
  };

  return <AppShell
    title="Send Regional Alert"
    subtitle="Send a bilingual alert to farmers in selected regions."
    actions={<Link to="/admin/outbreaks" className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-xs font-semibold text-stone-700 dark:border-stone-700 dark:text-stone-200"><ArrowLeft className="h-4 w-4" />Back to Outbreak Alerts</Link>}
  >
    <form onSubmit={submit} className="max-w-3xl space-y-6 rounded-2xl border border-stone-200 bg-white p-6 dark:border-stone-800 dark:bg-[#121A16]">
      <section>
        <h2 className="mb-3 text-sm font-bold">Target regions</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {REGIONS.map((region) => <label key={region} className="flex items-center gap-2 rounded-lg border border-stone-200 p-2.5 text-sm dark:border-stone-700">
            <input type="checkbox" checked={regions.includes(region)} onChange={() => toggleRegion(region)} />{region}
          </label>)}
        </div>
      </section>
      <label className="block text-sm font-medium">Message in English<textarea required maxLength={5000} rows={4} value={messageEn} onChange={(event) => setMessageEn(event.target.value)} className="mt-1 w-full rounded-lg border border-stone-300 bg-white p-3 dark:border-stone-700 dark:bg-stone-900" /></label>
      <label className="block text-sm font-medium">መልእክት በአማርኛ<textarea required maxLength={5000} rows={4} dir="auto" value={messageAm} onChange={(event) => setMessageAm(event.target.value)} className="mt-1 w-full rounded-lg border border-stone-300 bg-white p-3 dark:border-stone-700 dark:bg-stone-900" /></label>
      <fieldset><legend className="mb-2 text-sm font-bold">Delivery method</legend><div className="flex flex-wrap gap-5">{(['sms', 'app', 'both'] as const).map((value) => <label key={value} className="flex items-center gap-2 text-sm"><input type="radio" name="delivery" value={value} checked={method === value} onChange={() => setMethod(value)} />{value === 'sms' ? 'SMS' : value === 'app' ? 'App (notification + community post)' : 'Both'}</label>)}</div></fieldset>
      {outcome && <p role="status" className="whitespace-pre-line rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100"><BellRing className="mr-2 inline h-4 w-4" />{outcome}</p>}
      <button type="submit" disabled={sending || !regions.length || !messageEn.trim() || !messageAm.trim()} className="inline-flex items-center gap-2 rounded-lg bg-emerald-900 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"><Send className="h-4 w-4" />{sending ? 'Sending…' : 'Send Alert'}</button>
    </form>
  </AppShell>;
};
