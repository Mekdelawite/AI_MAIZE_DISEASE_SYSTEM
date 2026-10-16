import { apiRequest } from './api';
import { UserRecord } from '../types/api';

export interface LoginPayload {
  phone_number: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  phone_number: string;
  password: string;
  region: string;
  woreda: string;
  kebele?: string;
  preferred_language?: 'en' | 'am';
  latitude?: number;
  longitude?: number;
  sms_opt_in?: boolean;
}

export interface AuthSessionResponse {
  token?: string;
  access_token?: string;
  user?: UserRecord;
}

export const authService = {
  async login(payload: LoginPayload): Promise<{ token: string; user: UserRecord }> {
    const raw = await apiRequest<any>('/api/auth/login', {
      method: 'POST',
      body: {
        phone_number: payload.phone_number.trim(),
        phone: payload.phone_number.trim(),
        password: payload.password,
      },
      skipAuth: true,
    });

    const token = raw?.token || raw?.access_token || raw?.data?.token || raw?.data?.access_token;
    const user = raw?.user || raw?.data?.user || raw;

    if (!token) {
      throw new Error('Authentication response did not include a valid JWT token.');
    }

    return { token, user };
  },

  async register(payload: RegisterPayload): Promise<any> {
    const cleanBody: Record<string, unknown> = {
      full_name: payload.full_name.trim(),
      phone_number: payload.phone_number.trim(),
      password: payload.password,
      region: payload.region.trim(),
      woreda: payload.woreda.trim(),
      preferred_language: payload.preferred_language || 'en',
      sms_opt_in: Boolean(payload.sms_opt_in),
    };

    if (payload.kebele?.trim()) {
      cleanBody.kebele = payload.kebele.trim();
    }
    if (payload.latitude !== undefined && !Number.isNaN(payload.latitude)) {
      cleanBody.latitude = payload.latitude;
    }
    if (payload.longitude !== undefined && !Number.isNaN(payload.longitude)) {
      cleanBody.longitude = payload.longitude;
    }

    return apiRequest('/api/auth/register', {
      method: 'POST',
      body: cleanBody,
      skipAuth: true,
    });
  },

  async getCurrentUser(): Promise<UserRecord> {
    const res = await apiRequest<any>('/api/auth/me', {
      method: 'GET',
    });
    return res?.user || res;
  },

  async requestPasswordReset(phone_number: string): Promise<any> {
    return apiRequest('/api/auth/password-reset/request', {
      method: 'POST',
      body: { phone_number: phone_number.trim() },
      skipAuth: true,
    });
  },

  async confirmPasswordReset(payload: { phone_number: string; otp: string; new_password: string }): Promise<any> {
    return apiRequest('/api/auth/password-reset/confirm', {
      method: 'POST',
      body: {
        phone_number: payload.phone_number.trim(),
        otp: payload.otp.trim(),
        new_password: payload.new_password,
      },
      skipAuth: true,
    });
  },
};
