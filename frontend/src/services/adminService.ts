import { apiDownloadBlob, apiRequest } from './api';
import { OutbreakAlert, UserRecord } from '../types/api';

export interface CreateExtensionAgentPayload {
  full_name: string;
  phone_number: string;
  password: string;
  region: string;
  woreda: string;
  kebele?: string;
  preferred_language?: 'en' | 'am';
}

export interface ManualOutbreakPayload {
  disease_class: string;
  region: string;
  woreda?: string;
  kebele?: string;
  risk_level?: string;
  risk_score?: number;
  message?: string;
}

export interface AutomaticOutbreakPayload {
  disease_class: string;
  region: string;
  woreda?: string;
  analysis_period_days?: number;
}

export const adminService = {
  async getDashboard(): Promise<any> {
    return apiRequest<any>('/api/admin/dashboard', { method: 'GET' });
  },

  async getUsers(params?: { role?: string; search?: string; is_active?: boolean; page?: number }): Promise<UserRecord[]> {
    const res = await apiRequest<any>('/api/admin/users', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.users)) return res.users;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async getFarmers(params?: { region?: string; woreda?: string; search?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/admin/farmers', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.farmers)) return res.farmers;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async getDiagnoses(params?: { disease_class?: string; region?: string; start_date?: string; end_date?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/admin/diagnoses', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.diagnoses)) return res.diagnoses;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async getExtensionAgents(params?: { region?: string; woreda?: string; search?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/admin/extension-agents', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.extension_agents)) return res.extension_agents;
    if (Array.isArray(res?.agents)) return res.agents;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async createExtensionAgent(payload: CreateExtensionAgentPayload): Promise<any> {
    return apiRequest('/api/admin/extension-agents', {
      method: 'POST',
      body: payload,
    });
  },

  async updateUserStatus(userId: string | number, is_active: boolean): Promise<any> {
    return apiRequest(`/api/admin/users/${encodeURIComponent(String(userId))}/status`, {
      method: 'PATCH',
      body: { is_active },
    });
  },

  async getRegionalStatistics(): Promise<any> {
    return apiRequest('/api/admin/regional-statistics', { method: 'GET' });
  },

  async getGeoDiseases(params?: { disease_class?: string; region?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/admin/geo-diseases', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.cases)) return res.cases;
    if (Array.isArray(res?.geo_diseases)) return res.geo_diseases;
    return [];
  },

  async getComments(): Promise<any[]> {
    const res = await apiRequest<any>('/api/admin/comments', { method: 'GET' });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.comments)) return res.comments;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  // Outbreak Alerts
  async getOutbreakAlerts(params?: { region?: string; disease_class?: string; risk_level?: string }): Promise<OutbreakAlert[]> {
    const res = await apiRequest<any>('/api/outbreak-alerts', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.alerts)) return res.alerts;
    if (Array.isArray(res?.outbreak_alerts)) return res.outbreak_alerts;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async getOutbreakAlertDetail(alertId: string | number): Promise<OutbreakAlert> {
    const res = await apiRequest<any>(`/api/outbreak-alerts/${encodeURIComponent(String(alertId))}`, {
      method: 'GET',
    });
    return res?.alert || res;
  },

  async createManualOutbreakAlert(payload: ManualOutbreakPayload): Promise<any> {
    return apiRequest('/api/outbreak-alerts/manual', {
      method: 'POST',
      body: payload,
    });
  },

  async runAutomaticOutbreakEvaluation(payload: AutomaticOutbreakPayload): Promise<any> {
    return apiRequest('/api/outbreak-alerts/automatic', {
      method: 'POST',
      body: payload,
    });
  },

  // SMS Services
  async sendDirectSms(payload: { phone_number: string; message: string }): Promise<any> {
    return apiRequest('/api/sms/send', {
      method: 'POST',
      body: payload,
    });
  },

  async sendDiseaseAlertSms(payload: {
    diagnosis_id?: string | number;
    phone_number?: string;
    disease_class: string;
    region?: string;
    woreda?: string;
    message?: string;
  }): Promise<any> {
    return apiRequest('/api/sms/disease-alert', {
      method: 'POST',
      body: payload,
    });
  },

  async sendOutbreakAlertSms(payload: {
    alert_id?: string | number;
    disease_class?: string;
    region?: string;
    woreda?: string;
    message?: string;
  }): Promise<any> {
    return apiRequest('/api/sms/outbreak-alert', {
      method: 'POST',
      body: payload,
    });
  },

  async retryFailedSms(payload: { sms_id?: string | number; log_id?: string | number }): Promise<any> {
    return apiRequest('/api/sms/retry', {
      method: 'POST',
      body: payload,
    });
  },

  // Reports
  async downloadPdfReport(filters: { disease_class?: string; start_date?: string; end_date?: string }) {
    return apiDownloadBlob('/api/admin/reports/pdf', filters);
  },

  async downloadCsvReport(filters: { disease_class?: string; start_date?: string; end_date?: string }) {
    return apiDownloadBlob('/api/admin/reports/csv', filters);
  },
};
