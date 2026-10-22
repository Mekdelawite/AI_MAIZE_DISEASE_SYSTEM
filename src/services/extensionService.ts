import { apiRequest } from './api';
import { DiagnosisHistoryItem } from '../types/api';

export interface ExtensionDiagnosesFilter {
  disease_class?: string;
  woreda?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  limit?: number;
}

function normalizeDiagnosis(item: any): DiagnosisHistoryItem {
  const farmer = item?.farmer || {};
  const location = item?.farmer_location || item?.location || {};

  return {
    ...item,
    id: item?.id ?? item?.diagnosis_id,
    diagnosis_id: item?.diagnosis_id ?? item?.id,
    farmer_name: item?.farmer_name ?? farmer.full_name ?? farmer.name,
    farmer_phone: item?.farmer_phone ?? farmer.phone_number ?? farmer.phone,
    region: item?.region ?? location.region,
    woreda: item?.woreda ?? location.woreda,
    kebele: item?.kebele ?? location.kebele,
    heatmap_url: item?.heatmap_url ?? item?.heatmap_path,
  };
}

export const extensionService = {
  async getDashboard(): Promise<any> {
    return apiRequest<any>('/api/extension/dashboard', {
      method: 'GET',
    });
  },

  async getDiagnoses(filters: ExtensionDiagnosesFilter = {}): Promise<{
    items: DiagnosisHistoryItem[];
    total: number;
  }> {
    const res = await apiRequest<any>('/api/extension/diagnoses', {
      method: 'GET',
      params: filters as Record<string, string | number | undefined>,
    });

    const rawItems = Array.isArray(res)
      ? res
      : Array.isArray(res?.diagnoses)
      ? res.diagnoses
      : Array.isArray(res?.items)
      ? res.items
      : [];
    const items = rawItems.map(normalizeDiagnosis);

    return {
      items,
      total: Number(res?.total ?? res?.pagination?.total ?? items.length),
    };
  },

  async getDiagnosisDetail(diagnosisId: string | number): Promise<DiagnosisHistoryItem> {
    const res = await apiRequest<any>(`/api/extension/diagnoses/${encodeURIComponent(String(diagnosisId))}`, {
      method: 'GET',
    });
    return normalizeDiagnosis(res?.diagnosis || res);
  },

  async getGeoDiseases(filters?: { disease_class?: string; start_date?: string; end_date?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/extension/geo-diseases', {
      method: 'GET',
      params: filters,
    });
    const items = Array.isArray(res)
      ? res
      : Array.isArray(res?.cases)
      ? res.cases
      : Array.isArray(res?.locations)
      ? res.locations
      : Array.isArray(res?.geo_diseases)
      ? res.geo_diseases
      : [];

    return items.map((item: any) => normalizeDiagnosis(item));
  },
};
