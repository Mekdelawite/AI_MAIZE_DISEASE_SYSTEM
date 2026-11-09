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

export interface FarmerPushConfig {
  enabled: boolean;
  public_key: string | null;
}

export const notificationService = {
  async getPushConfig(): Promise<FarmerPushConfig> {
    const response = await apiRequest<FarmerPushConfig>('/api/farmer/push/config', {
      method: 'GET',
    });
    if (typeof response?.enabled !== 'boolean') {
      throw new Error('The push notification service returned an invalid configuration.');
    }
    return response;
  },

  async savePushSubscription(subscription: PushSubscriptionJSON): Promise<void> {
    await apiRequest('/api/farmer/push/subscriptions', {
      method: 'POST',
      body: subscription,
    });
  },

  async removePushSubscription(endpoint: string): Promise<void> {
    await apiRequest('/api/farmer/push/subscriptions', {
      method: 'DELETE',
      body: { endpoint },
    });
  },

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
