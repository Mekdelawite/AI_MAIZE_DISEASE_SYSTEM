import { apiRequest } from './api';
import { ProfileResponseData } from '../types/api';

export interface UpdateProfilePayload {
  full_name?: string;
  preferred_language?: 'en' | 'am';
  region?: string;
  woreda?: string;
  kebele?: string;
  latitude?: number | null;
  longitude?: number | null;
  sms_opt_in?: boolean;
}

export const profileService = {
  async getProfile(): Promise<ProfileResponseData> {
    const res = await apiRequest<any>('/api/profile', {
      method: 'GET',
    });
    return {
      user: res?.user || res,
      farmer_profile: res?.farmer_profile ?? null,
    };
  },

  async updateProfile(payload: UpdateProfilePayload): Promise<ProfileResponseData> {
    const res = await apiRequest<any>('/api/profile', {
      method: 'PUT',
      body: payload,
    });
    return {
      user: res?.user || res,
      farmer_profile: res?.farmer_profile ?? null,
    };
  },
};
