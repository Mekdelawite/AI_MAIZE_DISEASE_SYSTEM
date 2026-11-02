import { apiRequest } from './api';
import { FarmerNotificationPreferences, ProfileResponseData } from '../types/api';

export interface UpdateProfilePayload {
  full_name?: string;
  preferred_language?: 'en' | 'am';
  region?: string;
  woreda?: string;
  kebele?: string;
  latitude?: number | null;
  longitude?: number | null;
  sms_opt_in?: boolean;
  notification_preferences?: FarmerNotificationPreferences;
  planting_date?: string | null;
  soil_type?: string | null;
  available_water_capacity_mm_per_m?: number | null;
  crop_growth_stage?: 'initial' | 'development' | 'mid_season' | 'late_season' | null;
  irrigation_status?: 'unknown' | 'rainfed' | 'irrigated' | null;
  last_irrigation_date?: string | null;
  last_irrigation_mm?: number | null;
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
