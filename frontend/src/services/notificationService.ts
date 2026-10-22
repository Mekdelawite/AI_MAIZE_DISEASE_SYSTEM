import { apiRequest } from './api';

export interface FarmerNotification {
  id: number;
  title: string;
  message: string;
  region: string;
  is_read: boolean;
  discussion_post_id?: number | null;
  created_at: string;
}

export const notificationService = {
  async getFarmerNotifications(): Promise<FarmerNotification[]> {
    const response = await apiRequest<any>('/api/farmer/notifications', { method: 'GET' });
    return Array.isArray(response?.notifications) ? response.notifications : [];
  },
};
