import { apiRequest } from './api';
import { CompleteDiagnosisResponse, DiagnosisHistoryItem } from '../types/api';

export const diagnosisService = {
  async isBackendAvailable(): Promise<boolean> {
    try {
      const health = await apiRequest<{ status?: string }>('/health', {
        method: 'GET',
        skipAuth: true,
        timeoutMs: 5000,
      });
      return health?.status === 'healthy';
    } catch {
      return false;
    }
  },

  async getAdvisoryForLanguage(diagnosis: { prediction: { class_name: string; confidence?: number } }, language: 'en' | 'am') {
    const res = await apiRequest<any>('/api/advisory', {
      method: 'POST',
      body: { diagnosis, language },
    });
    return (res?.data || res?.advisory || res) as import('../types/api').AdvisoryRecord;
  },

  /**
   * Calls the idempotent POST /api/sync diagnosis pipeline.
   * Returns the combined diagnosis, Grad-CAM explainability, and advisory.
   */
  async runCompleteDiagnosis(params: {
    image: File;
    language: 'en' | 'am';
    explain: boolean;
    operationId: string;
  }): Promise<CompleteDiagnosisResponse> {
    const formData = new FormData();
    formData.append('operation_id', params.operationId);
    formData.append('image', params.image);
    formData.append('operation_type', 'diagnosis');
    formData.append('language', params.language);
    formData.append('explain', params.explain ? 'true' : 'false');

    const res = await apiRequest<any>('/api/sync', {
      method: 'POST',
      body: formData,
      timeoutMs: 90000,
    });

    const response = res?.data ?? res;
    const result = response?.result ?? response;
    if (result && ('diagnosis' in result || 'advisory' in result || 'database' in result)) {
      return result as CompleteDiagnosisResponse;
    }

    return {
      diagnosis: result?.diagnosis || {
        prediction: result?.prediction || {
          class_name: result?.class_name || result?.disease_class || 'Unknown',
          confidence: result?.confidence ?? 0,
        },
      },
      advisory: result?.advisory || null,
      database: result?.database || undefined,
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
