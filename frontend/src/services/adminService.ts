import { apiDownloadBlob, apiRequest } from './api';
import { OutbreakAlert, UserRecord } from '../types/api';

export interface CreateExtensionAgentPayload {
  full_name: string;
  phone_number: string;
  email: string;
  employee_id: string;
  organization: string;
  region_id: string;
  zone_id: string;
  woreda_id: string;
  verification_method: 'email' | 'sms';
  professional_info_verified: true;
  preferred_language?: 'en' | 'am';
}
export interface AdminGeographyOption {
  id: string;
  name_en: string;
  name_local?: string | null;
  parent_id?: string;
}

export interface ExtensionAgentRecord {
  id: number;
  agent_id: number;
  full_name: string;
  phone_number: string;
  email: string | null;
  employee_id: string | null;
  organization: string | null;
  region: string | null;
  region_id: string | null;
  zone: string | null;
  zone_id: string | null;
  woreda: string | null;
  woreda_id: string | null;
  professional_info_verified: boolean;
  professional_info_verified_by_id: number | null;
  professional_info_verified_by: string | null;
  professional_info_verified_at: string | null;
  account_status: 'pending_activation' | 'active' | 'suspended';
  is_active: boolean;
  preferred_language?: 'en' | 'am';
  created_at?: string | null;
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
  async sendRegionalAlert(payload: { regions: string[]; message_en: string; message_am: string; method: 'sms' | 'app' | 'both' }): Promise<any> {
    return apiRequest('/api/admin/regional-alerts', { method: 'POST', body: payload });
  },
  async getDashboard(): Promise<any> {
    return apiRequest<any>('/api/admin/dashboard', { method: 'GET' });
  },

  async getUsers(params?: { role?: string; region?: string; kebele?: string; search?: string; is_active?: boolean; page?: number }): Promise<UserRecord[]> {
    const res = await apiRequest<any>('/api/admin/users', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.users)) return res.users;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async getFarmers(params?: { region?: string; woreda?: string; kebele?: string; search?: string }): Promise<any[]> {
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

  async getExtensionAgents(params?: {
    region?: string;
    woreda?: string;
    search?: string;
    account_status?: string;
    professional_info_verified?: boolean;
  }): Promise<ExtensionAgentRecord[]> {
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

  async getExtensionAgentGeography(
    level: 'regions' | 'zones' | 'woredas',
    parentId?: string,
  ): Promise<AdminGeographyOption[]> {
    const res = await apiRequest<any>('/api/admin/extension-agent-geography', {
      method: 'GET',
      params: { level, parent_id: parentId },
    });
    if (Array.isArray(res)) return res as AdminGeographyOption[];
    if (Array.isArray(res?.items)) return res.items as AdminGeographyOption[];
    return [];
  },

  async resendExtensionAgentActivation(userId: number): Promise<any> {
    return apiRequest(
      `/api/admin/extension-agents/${encodeURIComponent(String(userId))}/activation-code`,
      { method: 'POST', body: {} },
    );
  },

  async updateExtensionAgentStatus(
    userId: number,
    account_status: 'active' | 'suspended',
  ): Promise<any> {
    return apiRequest(
      `/api/admin/extension-agents/${encodeURIComponent(String(userId))}/status`,
      { method: 'PATCH', body: { account_status } },
    );
  },

  async transferExtensionAgent(
    userId: number,
    assignment: { region_id: string; zone_id: string; woreda_id: string },
  ): Promise<any> {
    return apiRequest(
      `/api/admin/extension-agents/${encodeURIComponent(String(userId))}/assignment`,
      { method: 'PATCH', body: assignment },
    );
  },

  async getExtensionAgentAssignmentHistory(userId: number): Promise<any[]> {
    const res = await apiRequest<any>(
      `/api/admin/extension-agents/${encodeURIComponent(String(userId))}/assignment-history`,
      { method: 'GET' },
    );
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  },

  async updateExtensionAgent(
    userId: string | number,
    payload: Partial<CreateExtensionAgentPayload> & { is_active?: boolean },
  ): Promise<any> {
    return apiRequest(
      `/api/admin/extension-agents/${encodeURIComponent(String(userId))}`,
      { method: 'PATCH', body: payload },
    );
  },


  async deleteExtensionAgent(userId: string | number): Promise<any> {
    return apiRequest(
      `/api/admin/extension-agents/${encodeURIComponent(String(userId))}`,
      { method: 'DELETE' },
    );
  },

  async updateUserStatus(userId: string | number, is_active: boolean): Promise<any> {
    return apiRequest(`/api/admin/users/${encodeURIComponent(String(userId))}/status`, {
      method: 'PATCH',
      body: { is_active },
    });
  },

  async getRegionalStatistics(params?: { disease_class?: string; start_date?: string; end_date?: string }): Promise<any> {
    return apiRequest('/api/admin/regional-statistics', { method: 'GET', params });
  },

  async getGeoDiseases(params?: { disease_class?: string; start_date?: string; end_date?: string }): Promise<any[]> {
    const res = await apiRequest<any>('/api/admin/geo-diseases', { method: 'GET', params });
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.cases)) return res.cases;
    if (Array.isArray(res?.geo_diseases)) return res.geo_diseases;
    return [];
  },

  async getGeoDiseaseMapData(params?: { disease_class?: string; start_date?: string; end_date?: string }): Promise<{ cases: any[]; summary: any }> {
    const res = await apiRequest<any>('/api/admin/geo-diseases', {
      method: 'GET',
      params: { ...params, include_coverage: 'true' },
    });
    return {
      cases: Array.isArray(res?.cases) ? res.cases : [],
      summary: res?.summary || {},
    };
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
  async sendDirectSms(payload: { recipient_phone: string; message: string }): Promise<any> {
    return apiRequest('/api/sms/send', {
      method: 'POST',
      body: payload,
    });
  },

  async sendDiseaseAlertSms(payload: {
    recipient_phone: string;
    disease_name: string;
    confidence: number;
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
    recipient_phone: string;
    disease_name: string;
    location: string;
    region?: string;
    woreda?: string;
    message?: string;
  }): Promise<any> {
    return apiRequest('/api/sms/outbreak-alert', {
      method: 'POST',
      body: payload,
    });
  },

  async retryFailedSms(payload: { sms_record_id: string | number }): Promise<any> {
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
