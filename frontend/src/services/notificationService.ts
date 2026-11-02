import { apiRequest } from './api';

export interface FarmerNotification {
  id: number;
  title: string;
  message: string;
  region: string;
  notification_type?: string;
  outbreak_alert_id?: number | null;
  discussion_post_id?: number | null;
  is_read: boolean;
  created_at: string;
}

export interface FarmerNotificationsResponse {
  notifications: FarmerNotification[];
}

export const notificationService = {
  async getFarmerNotifications(): Promise<FarmerNotification[]> {
    const response = await apiRequest<FarmerNotificationsResponse>('/api/farmer/notifications', { method: 'GET' });
    if (!Array.isArray(response?.notifications)) {
      throw new Error('The notification service returned an invalid response.');
    }
    return response.notifications;
  },

  async getUnreadCount(): Promise<number> {
    const response = await apiRequest<any>('/api/farmer/notifications/unread-count', { method: 'GET' });
    if (typeof response?.count !== 'number' || response.count < 0) {
      throw new Error('The notification service returned an invalid unread count.');
    }
    return response.count;
  },

  async markNotificationRead(notificationId: number): Promise<void> {
    await apiRequest<any>(`/api/farmer/notifications/${encodeURIComponent(String(notificationId))}/read`, {
      method: 'PATCH',
    });
  },

  async markAllNotificationsRead(): Promise<number> {
    const response = await apiRequest<any>('/api/farmer/notifications/read-all', {
      method: 'PATCH',
    });
    return typeof response?.updated === 'number' ? response.updated : 0;
  },
};
