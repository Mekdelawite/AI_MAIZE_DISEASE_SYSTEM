import { apiRequest } from './api';
import { QueuedSyncItem } from '../types/api';

const OFFLINE_QUEUE_STORAGE_KEY = 'maizecare_offline_sync_queue_v1';
const MAX_BATCH_SIZE = 10;

function dataUrlToBlob(dataUrl: string, fallbackType = 'image/jpeg'): Blob {
  const parts = dataUrl.split(',');
  const mimeMatch = parts[0]?.match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : fallbackType;
  const binary = atob(parts[1] || '');
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    array[i] = binary.charCodeAt(i);
  }
  return new Blob([array], { type: mime });
}

export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('Failed to read image file for offline storage.'));
    reader.readAsDataURL(file);
  });
}

export function generateOperationId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `op_${crypto.randomUUID()}`;
  }
  return `op_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export const syncService = {
  getQueue(): QueuedSyncItem[] {
    try {
      const raw = localStorage.getItem(OFFLINE_QUEUE_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  },

  saveQueue(items: QueuedSyncItem[]): void {
    try {
      localStorage.setItem(OFFLINE_QUEUE_STORAGE_KEY, JSON.stringify(items));
    } catch {
      throw new Error('Browser storage quota exceeded. Please sync or remove older queued items.');
    }
  },

  async enqueueDiagnosis(params: {
    file: File;
    language: 'en' | 'am';
    explain: boolean;
  }): Promise<QueuedSyncItem> {
    const imageDataUrl = await fileToDataUrl(params.file);
    const current = this.getQueue();
    const item: QueuedSyncItem = {
      operation_id: generateOperationId(),
      operation_type: 'diagnosis',
      language: params.language,
      explain: params.explain,
      fileName: params.file.name,
      fileType: params.file.type || 'image/jpeg',
      fileSize: params.file.size,
      imageDataUrl,
      createdAt: new Date().toISOString(),
      status: 'queued',
    };
    this.saveQueue([item, ...current]);
    return item;
  },

  removeItem(operationId: string): QueuedSyncItem[] {
    const filtered = this.getQueue().filter((item) => item.operation_id !== operationId);
    this.saveQueue(filtered);
    return filtered;
  },

  clearSucceeded(): QueuedSyncItem[] {
    const filtered = this.getQueue().filter((item) => item.status !== 'succeeded');
    this.saveQueue(filtered);
    return filtered;
  },

  /**
   * Synchronizes a single queued item via POST /api/sync
   */
  async syncSingleItem(operationId: string): Promise<QueuedSyncItem> {
    const queue = this.getQueue();
    const idx = queue.findIndex((item) => item.operation_id === operationId);
    if (idx === -1) {
      throw new Error('Queued operation not found.');
    }

    const target = queue[idx];
    if (target.status === 'syncing') {
      return target;
    }

    target.status = 'syncing';
    target.errorMessage = undefined;
    this.saveQueue(queue);

    try {
      const blob = dataUrlToBlob(target.imageDataUrl, target.fileType);
      const formData = new FormData();
      formData.append('operation_id', target.operation_id);
      formData.append('image', blob, target.fileName);
      formData.append('operation_type', target.operation_type);
      formData.append('language', target.language);
      formData.append('explain', target.explain ? 'true' : 'false');

      const res = await apiRequest<any>('/api/sync', {
        method: 'POST',
        body: formData,
        timeoutMs: 90000,
      });

      const updatedQueue = this.getQueue();
      const updatedIdx = updatedQueue.findIndex((i) => i.operation_id === operationId);
      if (updatedIdx !== -1) {
        updatedQueue[updatedIdx].status = 'succeeded';
        updatedQueue[updatedIdx].serverResult = res?.result || res?.data || res;
        updatedQueue[updatedIdx].errorMessage = undefined;
        this.saveQueue(updatedQueue);
        return updatedQueue[updatedIdx];
      }
      return target;
    } catch (err: any) {
      const updatedQueue = this.getQueue();
      const updatedIdx = updatedQueue.findIndex((i) => i.operation_id === operationId);
      if (updatedIdx !== -1) {
        updatedQueue[updatedIdx].status = 'failed';
        updatedQueue[updatedIdx].errorMessage = err?.message || 'Synchronization failed.';
        this.saveQueue(updatedQueue);
        throw err;
      }
      throw err;
    }
  },

  /**
   * Synchronizes up to 10 eligible items (queued or failed) via POST /api/sync/batch
   * Preserves matching order between operation_id and image fields.
   */
  async syncBatch(): Promise<{ syncedCount: number; failedCount: number; response: any }> {
    const queue = this.getQueue();
    const eligible = queue.filter((item) => item.status === 'queued' || item.status === 'failed').slice(0, MAX_BATCH_SIZE);

    if (eligible.length === 0) {
      return { syncedCount: 0, failedCount: 0, response: null };
    }

    const eligibleIds = new Set(eligible.map((i) => i.operation_id));
    queue.forEach((item) => {
      if (eligibleIds.has(item.operation_id)) {
        item.status = 'syncing';
        item.errorMessage = undefined;
      }
    });
    this.saveQueue(queue);

    try {
      const formData = new FormData();
      eligible.forEach((item) => {
        const blob = dataUrlToBlob(item.imageDataUrl, item.fileType);
        formData.append('operation_id', item.operation_id);
        formData.append('image', blob, item.fileName);
        formData.append('operation_type', item.operation_type);
        formData.append('language', item.language);
        formData.append('explain', item.explain ? 'true' : 'false');
      });

      const res = await apiRequest<any>('/api/sync/batch', {
        method: 'POST',
        body: formData,
        timeoutMs: 120000,
      });

      const resultsMap = new Map<string, any>();
      const resultsArray = Array.isArray(res?.results)
        ? res.results
        : Array.isArray(res?.operations)
        ? res.operations
        : Array.isArray(res)
        ? res
        : [];

      resultsArray.forEach((entry: any) => {
        if (entry?.operation_id) {
          resultsMap.set(String(entry.operation_id), entry);
        }
      });

      let syncedCount = 0;
      let failedCount = 0;
      const latestQueue = this.getQueue();

      latestQueue.forEach((item) => {
        if (!eligibleIds.has(item.operation_id)) return;
        const entry = resultsMap.get(item.operation_id);
        if (entry) {
          if (entry.success === false || entry.status === 'failed' || entry.error) {
            item.status = 'failed';
            item.errorMessage = entry.error?.message || entry.message || 'Batch item failed on server.';
            failedCount++;
          } else {
            item.status = 'succeeded';
            item.serverResult = entry.data || entry.result || entry;
            syncedCount++;
          }
        } else {
          // If server confirmed overall batch success without per-item array
          item.status = 'succeeded';
          syncedCount++;
        }
      });

      this.saveQueue(latestQueue);
      return { syncedCount, failedCount, response: res };
    } catch (err: any) {
      const latestQueue = this.getQueue();
      latestQueue.forEach((item) => {
        if (eligibleIds.has(item.operation_id)) {
          item.status = 'failed';
          item.errorMessage = err?.message || 'Batch synchronization request failed.';
        }
      });
      this.saveQueue(latestQueue);
      throw err;
    }
  },
};
