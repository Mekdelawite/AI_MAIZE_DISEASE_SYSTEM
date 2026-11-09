
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

function readAuthSession(raw: any): { token: string; user: UserRecord } {
  if (raw?.success === false) {
    throw new Error(
      raw?.error?.message || raw?.message || 'Authentication failed.',
    );
  }

  const data = raw?.data?.data ?? raw?.data ?? raw;
  const token =
    data?.token ||
    data?.access_token ||
    raw?.token ||
    raw?.access_token;
  const user = data?.user || raw?.user || data;

  if (typeof token !== 'string' || !token.trim()) {
    throw new Error(
      'Authentication response did not include a valid JWT token.',
    );
  }

  return { token, user: user as UserRecord };
}

export const authService = {
  async login(
    payload: LoginPayload,
  ): Promise<{ token: string; user: UserRecord }> {
    const phone = payload.phone_number.trim();

    const raw = await apiRequest<any>('/api/auth/login', {
      method: 'POST',
      body: {
        phone_number: phone,
        phone,
        password: payload.password,
      },
      skipAuth: true,
    });

    return readAuthSession(raw);
  },

  async requestRegistrationOTP(phone_number: string): Promise<any> {
    return apiRequest('/api/auth/registration-otp/request', {
      method: 'POST',
      body: {
        phone_number: phone_number.trim(),
      },
      skipAuth: true,
    });
  },

  async verifyRegistrationOTP(
    phone_number: string,
    otp: string,
  ): Promise<any> {
    return apiRequest('/api/auth/registration-otp/verify', {
      method: 'POST',
      body: {
        phone_number: phone_number.trim(),
        otp: otp.trim(),
      },
      skipAuth: true,
    });
  },

  async register(
    payload: RegisterPayload,
  ): Promise<{ token: string; user: UserRecord }> {
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

    if (
      payload.latitude !== undefined &&
      Number.isFinite(payload.latitude)
    ) {
      cleanBody.latitude = payload.latitude;
    }

    if (
      payload.longitude !== undefined &&
      Number.isFinite(payload.longitude)
    ) {
      cleanBody.longitude = payload.longitude;
    }

    const raw = await apiRequest<any>('/api/auth/register', {
      method: 'POST',
      body: cleanBody,
      skipAuth: true,
    });

    const session = readAuthSession(raw);
    if (!session.user || session.user.role !== 'farmer') {
      throw new Error(
        'Registration response did not include a valid farmer account.',
      );
    }

    return session;
  },

  async getCurrentUser(): Promise<UserRecord> {
    const res = await apiRequest<any>('/api/auth/me', {
      method: 'GET',
    });

    return res?.user || res?.data?.user || res?.data || res;
  },

  async requestPasswordReset(phone_number: string): Promise<any> {
    return apiRequest('/api/auth/password-reset/request', {
      method: 'POST',
      body: {
        phone_number: phone_number.trim(),
      },
      skipAuth: true,
    });
  },

  async confirmPasswordReset(payload: {
    phone_number: string;
    otp: string;
    new_password: string;
  }): Promise<any> {
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

  async verifyExtensionAgentActivation(contact: string, code: string): Promise<{
    activation_token: string;
    expires_in_seconds: number;
  }> {
    return apiRequest('/api/auth/extension-agent/activation/verify', {
      method: 'POST',
      body: { contact: contact.trim(), code: code.trim() },
      skipAuth: true,
    });
  },

  async completeExtensionAgentActivation(
    activation_token: string,
    password: string,
  ): Promise<{ message: string }> {
    return apiRequest('/api/auth/extension-agent/activation/complete', {
      method: 'POST',
      body: { activation_token, password },
      skipAuth: true,
    });
  },
};
