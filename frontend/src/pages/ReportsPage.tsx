import React, { useEffect, useState } from 'react';
import { CheckCircle2, Eye, FileSpreadsheet, FileText, X } from 'lucide-react';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { adminService } from '../services/adminService';

type ReportPreview =
  | { kind: 'pdf'; url: string; filename: string }
  | { kind: 'csv'; filename: string; rows: string[][] }
  | null;

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === '"') {
      if (quoted && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === ',' && !quoted) {
      row.push(field);
      field = '';
    } else if ((character === '\n' || character === '\r') && !quoted) {
      if (character === '\r' && text[index + 1] === '\n') index += 1;
      row.push(field);
      if (row.some((cell) => cell.length > 0)) rows.push(row);
      row = [];
      field = '';
    } else {
      field += character;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    if (row.some((cell) => cell.length > 0)) rows.push(row);
  }
  return rows;
}

export const ReportsPage: React.FC = () => {
  const { t, notify } = useApp();
  const [diseaseClass, setDiseaseClass] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'csv' | null>(null);
  const [previewingFormat, setPreviewingFormat] = useState<'pdf' | 'csv' | null>(null);
  const [reportOutcome, setReportOutcome] = useState<string | null>(null);
  const [preview, setPreview] = useState<ReportPreview>(null);

  useEffect(() => {
    const objectUrl = preview?.kind === 'pdf' ? preview.url : null;
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [preview]);

  const handlePreviewReport = async (format: 'pdf' | 'csv') => {
    setPreviewingFormat(format);
    setPreview(null);
    try {
      const filters = {
        disease_class: diseaseClass.trim() || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };
      const { blob, filename } = format === 'pdf'
        ? await adminService.downloadPdfReport(filters)
        : await adminService.downloadCsvReport(filters);
      if (format === 'pdf') {
        setPreview({ kind: 'pdf', url: URL.createObjectURL(blob), filename });
      } else {
        setPreview({ kind: 'csv', rows: parseCsv(await blob.text()), filename });
      }
    } catch (error: any) {
      notify(error?.message || `Failed to preview ${format.toUpperCase()} report.`, 'error');
    } finally {
      setPreviewingFormat(null);
    }
  };

  const handleDownloadReport = async (format: 'pdf' | 'csv') => {
    setDownloadingFormat(format);
    setReportOutcome(null);
    try {
      const filters = {
        disease_class: diseaseClass.trim() || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };
      const { blob, filename } = format === 'pdf'
        ? await adminService.downloadPdfReport(filters)
        : await adminService.downloadCsvReport(filters);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setReportOutcome(`Downloaded ${format.toUpperCase()} report (${filename}, ${(blob.size / 1024).toFixed(1)} KB).`);
      notify(`${format.toUpperCase()} report downloaded from server.`, 'success');
    } catch (error: any) {
      notify(error?.message || `Failed to download ${format.toUpperCase()} report.`, 'error');
    } finally {
      setDownloadingFormat(null);
    }
  };

  return <AppShell title={t('navAdminReports')} subtitle="Export administrative diagnostic reports in PDF or CSV format.">
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <section className="rounded-xl border border-stone-200 bg-white p-6 dark:border-stone-800 dark:bg-[#121A16] sm:p-8">
        <div className="mb-5"><h2 className="text-lg font-bold text-stone-900 dark:text-stone-100 font-display">Administrative Diagnostic Reports</h2></div>
        <div className="space-y-4">
          <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">Filter by Disease Class (Optional)
            <input type="text" value={diseaseClass} onChange={(event) => setDiseaseClass(event.target.value)} placeholder="e.g. Common_Rust, Northern_Leaf_Blight, Healthy" className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3.5 py-2 text-xs dark:border-stone-700 dark:bg-stone-900" />
          </label>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="text-xs font-medium text-stone-700 dark:text-stone-300">Start Date (Optional)
              <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-mono dark:border-stone-700 dark:bg-stone-900" />
            </label>
            <label className="text-xs font-medium text-stone-700 dark:text-stone-300">End Date (Optional)
              <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-mono dark:border-stone-700 dark:bg-stone-900" />
            </label>
          </div>
        </div>
        {reportOutcome && <div role="status" className="mt-5 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3.5 text-xs text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"><CheckCircle2 className="h-4 w-4 shrink-0" /><span>{reportOutcome}</span></div>}
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <button type="button" disabled={previewingFormat !== null} onClick={() => handlePreviewReport('pdf')} className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-emerald-800 px-4 py-2.5 text-xs font-semibold text-emerald-900 hover:bg-emerald-50 disabled:opacity-50 dark:border-emerald-600 dark:text-emerald-200 dark:hover:bg-emerald-950/30"><Eye className="h-4 w-4" />{previewingFormat === 'pdf' ? 'Loading preview...' : 'Preview PDF'}</button>
          <button type="button" disabled={downloadingFormat !== null} onClick={() => handleDownloadReport('pdf')} className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-emerald-900 px-4 py-2.5 text-xs font-semibold text-white disabled:opacity-50"><FileText className="h-4 w-4" />{downloadingFormat === 'pdf' ? 'Downloading PDF...' : 'Download PDF Report'}</button>
          <button type="button" disabled={previewingFormat !== null} onClick={() => handlePreviewReport('csv')} className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-stone-400 px-4 py-2.5 text-xs font-semibold text-stone-800 hover:bg-stone-100 disabled:opacity-50 dark:border-stone-600 dark:text-stone-100 dark:hover:bg-stone-800"><Eye className="h-4 w-4" />{previewingFormat === 'csv' ? 'Loading preview...' : 'Preview CSV'}</button>
          <button type="button" disabled={downloadingFormat !== null} onClick={() => handleDownloadReport('csv')} className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-stone-300 px-4 py-2.5 text-xs font-semibold text-stone-800 hover:bg-stone-100 disabled:opacity-50 dark:border-stone-700 dark:text-stone-100 dark:hover:bg-stone-800"><FileSpreadsheet className="h-4 w-4" />{downloadingFormat === 'csv' ? 'Downloading CSV...' : 'Download CSV Dataset'}</button>
        </div>
      </section>

      <section className="flex min-h-[560px] flex-col overflow-hidden rounded-xl border border-stone-200 bg-white dark:border-stone-800 dark:bg-[#121A16] lg:sticky lg:top-4">
        <header className="flex items-center justify-between gap-3 border-b border-stone-200 px-5 py-4 dark:border-stone-800">
          <div className="min-w-0"><h2 className="text-sm font-bold text-stone-900 dark:text-stone-100">Preview</h2><p className="truncate text-xs text-stone-500">{preview ? `${preview.filename} · ${preview.kind.toUpperCase()}` : 'Choose Preview PDF or Preview CSV to view a report here.'}</p></div>
          {preview && <button type="button" onClick={() => setPreview(null)} aria-label="Clear report preview" className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"><X className="h-4 w-4" /></button>}
        </header>
        {!preview ? <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-stone-500">Report previews will appear in this pane.</div> : preview.kind === 'pdf' ? <iframe title={`${preview.filename} preview`} src={preview.url} className="min-h-[560px] flex-1 bg-stone-100 dark:bg-stone-900" /> : <div className="min-h-[560px] flex-1 overflow-auto p-4">
          {preview.rows.length === 0 ? <p className="text-sm text-stone-500">The CSV report is empty.</p> : <><p className="mb-3 text-xs text-stone-500">Showing {Math.min(Math.max(preview.rows.length - 1, 0), 100)} of {Math.max(preview.rows.length - 1, 0)} data rows.</p><div className="overflow-auto rounded-lg border border-stone-200 dark:border-stone-800"><table className="min-w-full border-collapse text-left text-xs"><thead className="sticky top-0 bg-stone-100 dark:bg-stone-800"><tr>{preview.rows[0].map((heading, index) => <th key={`${heading}-${index}`} className="whitespace-nowrap border-b border-stone-200 px-3 py-2 font-semibold dark:border-stone-700">{heading}</th>)}</tr></thead><tbody>{preview.rows.slice(1, 101).map((row, rowIndex) => <tr key={rowIndex} className="odd:bg-white even:bg-stone-50 dark:odd:bg-[#121A16] dark:even:bg-stone-900">{preview.rows[0].map((_, columnIndex) => <td key={columnIndex} className="max-w-xs border-b border-stone-100 px-3 py-2 align-top dark:border-stone-800">{row[columnIndex] ?? ''}</td>)}</tr>)}</tbody></table></div></>}
        </div>}
      </section>
    </div>
  </AppShell>;
};
