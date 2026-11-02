import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, MapPin, RefreshCw, UserRound } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { extensionService } from '../services/extensionService';
import { DiagnosisHistoryItem } from '../types/api';
import { formatConfidence, formatDateTime } from '../utils/media';
import assignedMaizeImage from '../assets/images/extension_cases_maize.jpg';

interface FarmerCaseGroup {
  key: string;
  farmerId?: string | number;
  farmerName: string;
  farmerPhone?: string;
  region?: string;
  woreda?: string;
  kebele?: string;
  diagnoses: DiagnosisHistoryItem[];
}

export const ExtensionCasesPage: React.FC = () => {
  const { t, language } = useApp();
  const navigate = useNavigate();

  const [cases, setCases] = useState<DiagnosisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [diseaseFilter, setDiseaseFilter] = useState('');
  const [woredaFilter, setWoredaFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const farmerGroups = useMemo<FarmerCaseGroup[]>(() => {
    const groups = new Map<string, FarmerCaseGroup>();
    cases.forEach((diagnosis) => {
      const farmerId = diagnosis.farmer_id ?? diagnosis.user_id;
      const identity = farmerId != null
        ? `farmer:${farmerId}`
        : diagnosis.farmer_phone
          ? `phone:${diagnosis.farmer_phone}`
          : `name:${diagnosis.farmer_name || 'unknown'}|${diagnosis.region || ''}|${diagnosis.woreda || ''}`;
      const existing = groups.get(identity);
      if (existing) {
        existing.diagnoses.push(diagnosis);
        return;
      }
      groups.set(identity, {
        key: identity,
        farmerId,
        farmerName: diagnosis.farmer_name || diagnosis.farmer_phone || 'Assigned Farmer',
        farmerPhone: diagnosis.farmer_phone,
        region: diagnosis.region,
        woreda: diagnosis.woreda,
        kebele: diagnosis.kebele,
        diagnoses: [diagnosis],
      });
    });
    return [...groups.values()];
  }, [cases]);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await extensionService.getDiagnoses({
        disease_class: diseaseFilter.trim() || undefined,
        woreda: woredaFilter.trim() || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setCases(res.items);
    } catch (err: any) {
      setError(err?.message || 'Unable to load assigned diagnosis cases from /api/extension/diagnoses.');
    } finally {
      setLoading(false);
    }
  }, [diseaseFilter, woredaFilter, startDate, endDate]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleSelectFarmer = (farmer: FarmerCaseGroup) => {
    const farmerRouteId = farmer.farmerId ?? farmer.farmerPhone;
    if (farmerRouteId === undefined || farmerRouteId === null) return;
    navigate(`/extension/farmers/${encodeURIComponent(String(farmerRouteId))}`, {
      state: { farmer },
    });
  };

  return (
    <AppShell
      title={t('navExtCases')}
      subtitle="Inspect farmer maize leaf diagnoses assigned to your region and woreda via GET /api/extension/diagnoses."
      actions={
        <button
          type="button"
          onClick={loadCases}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('refresh')}</span>
        </button>
      }
    >
      <section
        className="relative mb-6 overflow-hidden rounded-2xl border border-emerald-900/10 bg-emerald-950 bg-cover bg-center shadow-md"
        style={{
          backgroundImage: `linear-gradient(90deg, rgba(4, 30, 23, 0.86) 0%, rgba(4, 36, 27, 0.58) 55%, rgba(4, 36, 27, 0.15) 100%), url(${assignedMaizeImage})`,
          backgroundPosition: 'center 46%',
        }}
      >
        <div className="flex min-h-[180px] flex-col justify-center p-6 sm:min-h-[210px] sm:p-8">
          <span className="text-xs font-semibold uppercase tracking-[0.15em] text-emerald-100">{language === 'am' ? 'የአካባቢዎ የእርሻ ሁኔታ' : 'Your local field activity'}</span>
          <h2 className="mt-2 text-2xl font-bold text-white font-display sm:text-3xl">{language === 'am' ? 'የተመደቡ የአርሶ አደር ጉዳዮች' : 'Assigned Farmer Cases'}</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-white/90">{language === 'am' ? 'በአካባቢዎ የተመዘገቡ የበቆሎ ቅጠል ምርመራዎችን ይመልከቱ፤ የአርሶ አደሩን ካርድ በመጫን የምርመራ ታሪኩን ይክፈቱ።' : 'Review diagnoses in your assigned area. Select a farmer card to open their diagnosis history.'}</p>
        </div>
      </section>

      {/* Filter Bar */}
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
        <div>
          <label className="block text-xs text-stone-500 mb-1">Disease Class</label>
          <input
            type="text"
            value={diseaseFilter}
            onChange={(e) => setDiseaseFilter(e.target.value)}
            placeholder="e.g. Common_Rust"
            className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div>
          <label className="block text-xs text-stone-500 mb-1">Woreda</label>
          <input
            type="text"
            value={woredaFilter}
            onChange={(e) => setWoredaFilter(e.target.value)}
            placeholder="Filter by woreda"
            className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div>
          <label className="block text-xs text-stone-500 mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div>
          <label className="block text-xs text-stone-500 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadCases}
            className="flex-1 py-1.5 px-3 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer"
          >
            Apply Filters
          </button>
          <button
            type="button"
            onClick={() => {
              setDiseaseFilter('');
              setWoredaFilter('');
              setStartDate('');
              setEndDate('');
            }}
            className="py-1.5 px-2.5 text-xs text-stone-600 dark:text-stone-400 hover:underline cursor-pointer"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-12">
          {loading ? (
            <LoadingSkeleton rows={5} />
          ) : error ? (
            <ErrorState title="Could not load assigned cases" message={error} onRetry={loadCases} />
          ) : cases.length === 0 ? (
            <EmptyState
              title="No assigned diagnosis cases found"
              description="Cases submitted by farmers within your assigned region and woreda will appear here."
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {farmerGroups.map((farmer) => {
                const latestDiagnosis = farmer.diagnoses[0];
                return (
                  <button
                    key={farmer.key}
                    type="button"
                    onClick={() => handleSelectFarmer(farmer)}
                    className="w-full rounded-2xl border border-stone-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 dark:border-stone-800 dark:bg-[#121A16] dark:hover:border-emerald-800"
                  >
                    <span className="flex items-start gap-3">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                        <UserRound className="h-5 w-5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-bold text-stone-900 dark:text-stone-100">{farmer.farmerName}</span>
                        <span className="mt-1 flex items-center gap-1 truncate text-xs text-stone-500 dark:text-stone-400"><MapPin className="h-3 w-3 shrink-0" />{[farmer.region, farmer.woreda, farmer.kebele].filter(Boolean).join(' · ') || 'Location unavailable'}</span>
                      </span>
                      <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-emerald-700 dark:text-emerald-400" />
                    </span>
                    <span className="mt-4 block border-t border-stone-100 pt-3 dark:border-stone-800">
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-semibold text-stone-800 dark:text-stone-200">{farmer.diagnoses.length} {language === 'am' ? 'ምርመራዎች' : farmer.diagnoses.length === 1 ? 'diagnosis' : 'diagnoses'}</span>
                        <span className="shrink-0 text-xs font-semibold text-emerald-800 dark:text-emerald-400">{language === 'am' ? 'ዝርዝር እይ' : 'View details'}</span>
                      </span>
                      <span className="mt-1 flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500 dark:text-stone-400">
                        <span>{formatDateTime(latestDiagnosis?.created_at)}</span>
                        <span className="truncate">{latestDiagnosis?.disease_class || latestDiagnosis?.class_name || '—'}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </AppShell>
  );
};
