import { apiRequest } from './api';
import { CompleteDiagnosisResponse, DiagnosisHistoryItem } from '../types/api';

export const diagnosisService = {
  /**
   * Calls POST /api/diagnosis/complete with multipart/form-data.
   * Returns combined diagnosis, Grad-CAM explainability, and advisory in one call.
   * Does not call POST /api/advisory a second time.
   */
  async runCompleteDiagnosis(params: {
    image: File;
    language: 'en' | 'am';
    explain: boolean;
  }): Promise<CompleteDiagnosisResponse> {
    const formData = new FormData();
    formData.append('image', params.image);
    formData.append('language', params.language);
    formData.append('explain', params.explain ? 'true' : 'false');

    const res = await apiRequest<any>('/api/diagnosis/complete', {
      method: 'POST',
      body: formData,
      timeoutMs: 90000,
    });

    // Normalize whether apiRequest unwrapped `.data` or returned the top-level object
    if (res && ('diagnosis' in res || 'advisory' in res || 'database' in res)) {
      return res as CompleteDiagnosisResponse;
    }
    if (res?.data && ('diagnosis' in res.data || 'advisory' in res.data)) {
      return res.data as CompleteDiagnosisResponse;
    }

    return {
      diagnosis: res?.diagnosis || {
        prediction: res?.prediction || {
          class_name: res?.class_name || res?.disease_class || 'Unknown',
          confidence: res?.confidence ?? 0,
        },
      },
      advisory: res?.advisory || null,
      database: res?.database || undefined,
    };
  },

  async getHistoryWithCount(limit = 20): Promise<{
    items: DiagnosisHistoryItem[];
    totalCount: number;
  }> {
    const res = await apiRequest<any>('/api/diagnosis/history', {
      method: 'GET',
      params: { limit },
    });

    const items: DiagnosisHistoryItem[] = Array.isArray(res)
      ? res
      : Array.isArray(res?.diagnoses)
        ? res.diagnoses
        : Array.isArray(res?.items)
          ? res.items
          : Array.isArray(res?.history)
            ? res.history
            : [];

    const countValue = Number(res?.total_count ?? res?.total ?? res?.count);
    return {
      items,
      totalCount: Number.isFinite(countValue) && countValue >= 0
        ? countValue
        : items.length,
    };
  },

  async getHistory(limit = 20): Promise<DiagnosisHistoryItem[]> {
    const { items } = await this.getHistoryWithCount(limit);
    return items;
  },

  async getHistoryDetail(diagnosisId: string | number): Promise<DiagnosisHistoryItem> {
    const res = await apiRequest<any>(`/api/diagnosis/history/${encodeURIComponent(String(diagnosisId))}`, {
      method: 'GET',
    });
    return res?.diagnosis || res;
  },

  async deleteHistoryItem(diagnosisId: string | number): Promise<any> {
    return apiRequest(`/api/diagnosis/history/${encodeURIComponent(String(diagnosisId))}`, {
      method: 'DELETE',
    });
  },
};
