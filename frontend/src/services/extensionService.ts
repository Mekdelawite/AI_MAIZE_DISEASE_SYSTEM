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

    const items = Array.isArray(res)
      ? res
      : Array.isArray(res?.diagnoses)
      ? res.diagnoses
      : Array.isArray(res?.items)
      ? res.items
      : [];

    return {
      items,
      total: Number(res?.total ?? items.length),
    };
  },

  async getDiagnosisDetail(diagnosisId: string | number): Promise<DiagnosisHistoryItem> {
    const res = await apiRequest<any>(`/api/extension/diagnoses/${encodeURIComponent(String(diagnosisId))}`, {
      method: 'GET',
    });
    return res?.diagnosis || res;
  },

  async getGeoDiseases(filters?: { disease_class?: string; start_date?: string; end_date?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/extension/geo-diseases', {
      method: 'GET',
      params: filters,
    });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.cases)) return res.cases;
    if (Array.isArray(res?.locations)) return res.locations;
    if (Array.isArray(res?.geo_diseases)) return res.geo_diseases;
    return [];
  },
};
