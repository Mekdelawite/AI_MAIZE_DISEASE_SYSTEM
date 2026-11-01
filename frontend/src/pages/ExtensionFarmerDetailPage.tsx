import React, { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Layers, MapPin, UserRound } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { TreatmentGuidance } from '../components/diagnosis/TreatmentGuidance';
import { useApp } from '../context/AppContext';
import { apiDownloadBlob } from '../services/api';
import { extensionService } from '../services/extensionService';
import { AdvisoryRecord, DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime, normalizeConfidencePercent, resolveMediaUrl } from '../utils/media';

interface FarmerSummary {
  farmerId?: string | number;
  farmerName?: string;
  farmerPhone?: string;
  region?: string;
  woreda?: string;
  kebele?: string;
  diagnoses?: DiagnosisHistoryItem[];
}

function renderList(value?: string | string[] | null): React.ReactNode {
  if (!value) return null;
  const items = Array.isArray(value) ? value : [value];
  if (!items.length) return null;
  return (
    <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-stone-700 dark:text-stone-300">
      {items.map((entry, index) => <li key={`${index}-${entry}`}>{entry}</li>)}
    </ul>
  );
}

export const ExtensionFarmerDetailPage: React.FC = () => {
  const { farmerId = '', diagnosisId } = useParams<{ farmerId: string; diagnosisId?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { language } = useApp();
  const routeFarmer = (location.state as { farmer?: FarmerSummary } | null)?.farmer;

  const [history, setHistory] = useState<DiagnosisHistoryItem[]>([]);
  const [farmer, setFarmer] = useState<FarmerSummary | null>(routeFarmer || null);
  const [selectedDiagnosis, setSelectedDiagnosis] = useState<DiagnosisHistoryItem | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [leafImageUrl, setLeafImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);

  const numericFarmerId = /^\d+$/.test(farmerId) ? Number(farmerId) : undefined;

  const loadFarmerHistory = useCallback(async () => {
    setHistoryLoading(true);
    setError(null);
    try {
      const firstPage = await extensionService.getDiagnoses({
        farmer_id: numericFarmerId,
        page: 1,
        per_page: 100,
      });
      const allCases = [...firstPage.items];
      for (let page = 2; page <= firstPage.pages; page += 1) {
        const nextPage = await extensionService.getDiagnoses({
          farmer_id: numericFarmerId,
          page,
          per_page: 100,
        });
        allCases.push(...nextPage.items);
      }

      const farmerCases = allCases.filter((item) => {
        if (numericFarmerId !== undefined) {
          return String(item.farmer_id ?? item.user_id ?? '') === String(numericFarmerId);
        }
        return String(item.farmer_phone || '') === farmerId;
      });
      setHistory(farmerCases);

      if (farmerCases.length > 0) {
        const first = farmerCases[0];
        setFarmer({
          farmerId: first.farmer_id ?? first.user_id,
          farmerName: first.farmer_name,
          farmerPhone: first.farmer_phone,
          region: first.region,
          woreda: first.woreda,
          kebele: first.kebele,
          diagnoses: farmerCases,
        });
      } else if (routeFarmer) {
        setHistory(routeFarmer.diagnoses || []);
        setFarmer(routeFarmer);
      } else {
        setError(language === 'am' ? 'ለዚህ አርሶ አደር በተመደበው አካባቢ የተመዘገበ ምርመራ አልተገኘም።' : 'No assigned diagnoses were found for this farmer.');
      }
    } catch (err: any) {
      if (routeFarmer?.diagnoses?.length) {
        setHistory(routeFarmer.diagnoses);
      } else {
        setError(err?.message || 'Unable to load this farmer’s diagnosis history.');
      }
    } finally {
      setHistoryLoading(false);
    }
  }, [farmerId, language, numericFarmerId, routeFarmer]);

  useEffect(() => {
    void loadFarmerHistory();
  }, [loadFarmerHistory]);

  useEffect(() => {
    let cancelled = false;
    if (!diagnosisId) {
      setSelectedDiagnosis(null);
      setDetailError(null);
      return;
    }

    setDetailLoading(true);
    setDetailError(null);
    extensionService.getDiagnosisDetail(diagnosisId)
      .then((detail) => {
        const belongsToFarmer = numericFarmerId === undefined
          || String(detail.farmer_id ?? detail.user_id ?? '') === String(numericFarmerId);
        if (!belongsToFarmer) {
          throw new Error('This diagnosis does not belong to the selected farmer.');
        }
        if (!cancelled) setSelectedDiagnosis(detail);
      })
      .catch((err: any) => {
        if (!cancelled) setDetailError(err?.message || 'Unable to load this diagnosis result.');
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => { cancelled = true; };
  }, [diagnosisId, numericFarmerId]);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setLeafImageUrl(null);
    setImageError(false);
    const imageUrl = selectedDiagnosis?.image_url;
    if (!imageUrl) return;

    apiDownloadBlob(imageUrl)
      .then(({ blob }) => {
        objectUrl = URL.createObjectURL(blob);
        if (cancelled) URL.revokeObjectURL(objectUrl);
        else setLeafImageUrl(objectUrl);
      })
      .catch(() => { if (!cancelled) setImageError(true); });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedDiagnosis?.image_url]);

  const advisory: AdvisoryRecord | null = selectedDiagnosis?.advisory || null;
  const farmerName = farmer?.farmerName || farmer?.farmerPhone || 'Assigned Farmer';

  return (
    <AppShell
      title={language === 'am' ? 'የአርሶ አደር ምርመራ ታሪክ' : 'Farmer Diagnosis History'}
      subtitle={language === 'am' ? 'የተመደበውን የአርሶ አደር ምርመራ ታሪክና ሙሉ ውጤቶችን ይመልከቱ።' : 'Review this farmer’s assigned diagnosis history and full results.'}
      actions={
        <button
          type="button"
          onClick={() => navigate('/extension/cases')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 px-3 py-2 text-xs font-medium text-stone-700 hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {language === 'am' ? 'ወደ ጉዳዮች ተመለስ' : 'Back to Assigned Cases'}
        </button>
      }
    >
      <div className="mb-6 flex items-start gap-4 rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm dark:border-emerald-950 dark:bg-[#121A16]">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300"><UserRound className="h-6 w-6" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-xl font-bold text-stone-900 dark:text-stone-100">{farmerName}</h2>
          <p className="mt-1 text-sm text-stone-600 dark:text-stone-300">{farmer?.farmerPhone || (language === 'am' ? 'ስልክ አልተመዘገበም' : 'Phone not available')}</p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-stone-500 dark:text-stone-400"><MapPin className="h-3.5 w-3.5" />{[farmer?.region, farmer?.woreda, farmer?.kebele].filter(Boolean).join(' · ') || '—'}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">{history.length} {language === 'am' ? 'ምርመራዎች' : history.length === 1 ? 'diagnosis' : 'diagnoses'}</span>
          {diagnosisId && <Link to={`/extension/farmers/${encodeURIComponent(farmerId)}`} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 dark:border-emerald-900 dark:text-emerald-300 dark:hover:bg-emerald-950/40"><ArrowLeft className="h-3 w-3" />{language === 'am' ? 'ወደ ታሪክ ተመለስ' : 'Back to diagnosis history'}</Link>}
        </div>
      </div>

      {historyLoading ? <LoadingSkeleton rows={5} /> : error ? (
        <ErrorState title={language === 'am' ? 'ታሪኩን መክፈት አልተቻለም' : 'Could not load diagnosis history'} message={error} onRetry={() => void loadFarmerHistory()} />
      ) : history.length === 0 ? (
        <EmptyState title={language === 'am' ? 'ምርመራ የለም' : 'No diagnoses found'} description={language === 'am' ? 'የዚህ አርሶ አደር የምርመራ ታሪክ ባዶ ነው።' : 'This farmer has no diagnosis records in the assigned area.'} />
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          {!diagnosisId && <section className="xl:col-span-12 rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121A16]">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100">{language === 'am' ? 'የምርመራ ታሪክ' : 'Diagnosis history'}</h3>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1">
              {history.map((item) => {
                const id = item.diagnosis_id ?? item.id;
                const isSelected = String(id) === String(diagnosisId || '');
                return (
                  <Link
                    key={String(id)}
                    to={`/extension/farmers/${encodeURIComponent(farmerId)}/diagnoses/${encodeURIComponent(String(id))}`}
                    state={{ farmer }}
                    aria-current={isSelected ? 'page' : undefined}
                    className={`block rounded-xl border p-3 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 ${isSelected ? 'border-emerald-400 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30' : 'border-stone-200 hover:border-emerald-300 hover:bg-emerald-50/40 dark:border-stone-800 dark:hover:border-emerald-900 dark:hover:bg-emerald-950/20'}`}
                  >
                    <span className="flex items-center justify-between gap-2 text-sm font-semibold text-stone-900 dark:text-stone-100"><span className="truncate">{item.disease_class || item.class_name || 'Diagnosis'}</span><span className="shrink-0 text-emerald-800 dark:text-emerald-400">#{id}</span></span>
                    <span className="mt-1 flex items-center justify-between gap-2 text-xs text-stone-500 dark:text-stone-400"><span>{formatDateTime(item.created_at)}</span><span>{formatConfidence(item.confidence)}</span></span>
                    <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 dark:text-emerald-400">{language === 'am' ? 'ሙሉ ውጤት እይ' : 'Open full result'} <ArrowRight className="h-3 w-3" /></span>
                  </Link>
                );
              })}
            </div>
          </section>}

          {diagnosisId && (
            <section className="xl:col-span-12">
              {detailLoading ? <LoadingSkeleton rows={5} /> : detailError ? (
                <ErrorState title={language === 'am' ? 'የምርመራ ውጤቱን መክፈት አልተቻለም' : 'Could not load diagnosis result'} message={detailError} onRetry={() => navigate(0)} />
              ) : selectedDiagnosis ? (
                <div className="space-y-5 rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121A16] sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-stone-200 pb-4 dark:border-stone-800">
                    <div>
                      <p className="text-xs font-mono text-stone-500">{language === 'am' ? 'የምርመራ ቁጥር' : 'Diagnosis'} #{selectedDiagnosis.diagnosis_id ?? selectedDiagnosis.id} · {formatDateTime(selectedDiagnosis.created_at)}</p>
                      <h3 className="mt-1 text-xl font-bold text-stone-900 dark:text-stone-100">{selectedDiagnosis.disease_class || selectedDiagnosis.class_name}</h3>
                      {advisory?.scientific_name && <p className="mt-1 text-sm italic text-stone-600 dark:text-stone-400">{advisory.scientific_name}</p>}
                    </div>
                    <div className="rounded-xl bg-emerald-50 px-4 py-2 text-right dark:bg-emerald-950/30"><span className="block text-[11px] text-stone-500">{language === 'am' ? 'እምነት' : 'Confidence'}</span><span className="font-mono text-lg font-bold text-emerald-800 dark:text-emerald-400">{formatConfidence(selectedDiagnosis.confidence)}</span></div>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="overflow-hidden rounded-xl border border-stone-200 dark:border-stone-800">
                      <h4 className="border-b border-stone-200 px-4 py-2 text-xs font-semibold text-stone-600 dark:border-stone-800 dark:text-stone-300">{language === 'am' ? 'የተመረመረው ቅጠል' : 'Diagnosed leaf image'}</h4>
                      <div className="flex min-h-48 items-center justify-center bg-stone-950 p-3">
                        {leafImageUrl && !imageError ? <img src={leafImageUrl} alt="Farmer's diagnosed maize leaf" className="max-h-72 w-auto rounded object-contain" /> : <p className="text-xs text-stone-400">{imageError ? (language === 'am' ? 'የቅጠሉ ምስል አልተገኘም።' : 'Leaf image is unavailable.') : (language === 'am' ? 'ምስሉ በመጫን ላይ…' : 'Loading image…')}</p>}
                      </div>
                    </div>
                    {resolveMediaUrl(selectedDiagnosis.heatmap_url) && (
                      <div className="overflow-hidden rounded-xl border border-stone-200 dark:border-stone-800">
                        <h4 className="flex items-center gap-2 border-b border-stone-200 px-4 py-2 text-xs font-semibold text-stone-600 dark:border-stone-800 dark:text-stone-300"><Layers className="h-3.5 w-3.5 text-emerald-700" />Grad-CAM visual explanation</h4>
                        <div className="flex min-h-48 items-center justify-center bg-stone-950 p-3"><img src={resolveMediaUrl(selectedDiagnosis.heatmap_url)!} alt="Grad-CAM heatmap for this diagnosis" className="max-h-72 w-auto rounded object-contain" /></div>
                      </div>
                    )}
                  </div>

                  {advisory && (
                    <div className="space-y-4 border-t border-stone-200 pt-4 dark:border-stone-800">
                      <div>
                        <h4 className="text-sm font-bold text-stone-900 dark:text-stone-100">{language === 'am' ? 'የግብርና ምክር' : 'Agronomic advisory'}</h4>
                        {advisory.severity && <p className="mt-1 text-xs text-amber-800 dark:text-amber-300">{language === 'am' ? 'ክብደት' : 'Severity'}: {advisory.severity}</p>}
                        {(advisory.description || advisory.advisory_text) && <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-stone-700 dark:text-stone-300">{advisory.description || advisory.advisory_text}</p>}
                      </div>
                      {renderList(advisory.symptoms) && <div><h5 className="mb-1 text-xs font-semibold text-stone-600 dark:text-stone-300">{language === 'am' ? 'ምልክቶች' : 'Symptoms'}</h5>{renderList(advisory.symptoms)}</div>}
                      {renderList(advisory.causes) && <div><h5 className="mb-1 text-xs font-semibold text-stone-600 dark:text-stone-300">{language === 'am' ? 'መንስኤዎች' : 'Causes'}</h5>{renderList(advisory.causes)}</div>}
                      {renderList(advisory.favorable_conditions) && <div><h5 className="mb-1 text-xs font-semibold text-stone-600 dark:text-stone-300">{language === 'am' ? 'ተስማሚ ሁኔታዎች' : 'Favorable conditions'}</h5>{renderList(advisory.favorable_conditions)}</div>}
                      <TreatmentGuidance language={language} fieldPractices={advisory.management || advisory.treatment || advisory.recommendations} prevention={advisory.prevention || advisory.preventions} pesticideOptions={advisory.pesticide_recommendation} safetyInstructions={advisory.pesticide_safety} />
                      {advisory.sources?.length ? <div><h5 className="mb-2 text-xs font-semibold text-stone-600 dark:text-stone-300">{language === 'am' ? 'ምንጮች' : 'Sources'}</h5><ul className="space-y-2">{advisory.sources.map((source, index) => <li key={`${source.title || 'source'}-${index}`} className="text-sm">{source.url ? <a href={source.url} target="_blank" rel="noreferrer" className="font-medium text-emerald-800 underline dark:text-emerald-300">{source.title || source.url}</a> : source.title}<span className="ml-2 text-xs text-stone-500">{[source.organization, source.year].filter(Boolean).join(' · ')}</span></li>)}</ul></div> : null}
                    </div>
                  )}
                  {!advisory && <p className="text-sm text-stone-600 dark:text-stone-400">{language === 'am' ? 'ለዚህ ምርመራ የተቀመጠ የግብርና ምክር አልተገኘም።' : 'No saved agronomic advisory is available for this diagnosis.'}</p>}
                </div>
              ) : null}
            </section>
          )}
        </div>
      )}
    </AppShell>
  );
};
