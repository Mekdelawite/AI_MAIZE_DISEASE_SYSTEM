
import type { LocalDiagnosisResult } from './localDiagnosisService';

const DB_NAME = 'maizecare-offline-db';
const DB_VERSION = 2;
const STORE_NAME = 'diagnoses';
const MAX_SYNC_ATTEMPTS = 3;
const SYNC_RETRY_COOLDOWN_MS = 60 * 60 * 1000;
const QUEUE_CHANGED_EVENT = 'maizecare:offline-diagnosis-queue-changed';

function notifyQueueChanged(): void {
  window.dispatchEvent(new Event(QUEUE_CHANGED_EVENT));
}

export interface OfflineDiagnosisRecord {
  operation_id: string;
  user_id?: string | number;
  language: 'en' | 'am';
  explain: boolean;
  file_name: string;
  file_type: string;
  className: LocalDiagnosisResult['className'];
  confidence: number;
  probabilities: number[];
  created_at: string;
  sync_status: 'pending' | 'synced';
  sync_attempts?: number;
  next_retry_at?: string;
  synced_at?: string;
  server_result?: unknown;
  sync_error?: string;
  image: Blob;
}

export function createOfflineDiagnosisOperationId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `diagnosis_${crypto.randomUUID()}`;
  }
  return `diagnosis_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) {
      reject(new Error('IndexedDB is not supported by this browser.'));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      const store = db.objectStoreNames.contains(STORE_NAME)
        ? request.transaction!.objectStore(STORE_NAME)
        : db.createObjectStore(STORE_NAME, {
          keyPath: 'operation_id',
        });

      if (!store.indexNames.contains('created_at')) {
        store.createIndex('created_at', 'created_at');
      }
      if (!store.indexNames.contains('sync_status')) {
        store.createIndex('sync_status', 'sync_status');
      }
      if (!store.indexNames.contains('user_id')) {
        store.createIndex('user_id', 'user_id');
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error ?? new Error('Could not open offline storage.'));
  });
}

export const offlineDiagnosisStore = {
  async save(
    result: LocalDiagnosisResult,
    image: File,
    userId: string | number,
    metadata: {
      operationId?: string;
      language?: 'en' | 'am';
      explain?: boolean;
      createdAt?: string;
    } = {},
  ): Promise<OfflineDiagnosisRecord> {
    if (
      !(
        (typeof userId === 'number' && Number.isFinite(userId)) ||
        (typeof userId === 'string' && userId.trim())
      )
    ) {
      throw new Error('An authenticated user ID is required to save an offline diagnosis.');
    }

    const db = await openDatabase();

    try {
      const record: OfflineDiagnosisRecord = {
        operation_id: metadata.operationId ?? createOfflineDiagnosisOperationId(),
        user_id: userId,
        language: metadata.language ?? 'en',
        explain: metadata.explain ?? false,
        file_name: image.name,
        file_type: image.type || 'image/jpeg',
        className: result.className,
        confidence: result.confidence,
        probabilities: [...result.probabilities],
        created_at: metadata.createdAt ?? new Date().toISOString(),
        sync_status: 'pending',
        sync_attempts: 0,
        image,
      };

      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');

        transaction.objectStore(STORE_NAME).add(record);

        transaction.oncomplete = () => resolve();
        transaction.onerror = () =>
          reject(transaction.error ?? new Error('Could not save diagnosis.'));
        transaction.onabort = () =>
          reject(transaction.error ?? new Error('Saving diagnosis was aborted.'));
      });

      notifyQueueChanged();
      return record;
    } finally {
      db.close();
    }
  },

  async getAll(userId: string | number): Promise<OfflineDiagnosisRecord[]> {
    const db = await openDatabase();

    try {
      return await new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readonly');
        const request = transaction
          .objectStore(STORE_NAME)
          .index('user_id')
          .getAll(userId);

        request.onsuccess = () => {
          const records = request.result as OfflineDiagnosisRecord[];

          resolve(
            records.sort(
              (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime(),
            ),
          );
        };

        request.onerror = () =>
          reject(request.error ?? new Error('Could not load diagnoses.'));
      });
    } finally {
      db.close();
    }
  },

  async getPending(userId: string | number): Promise<OfflineDiagnosisRecord[]> {
    const records = await this.getAll(userId);
    return records.filter((record) => record.sync_status === 'pending');
  },

  async getReadyToSync(userId: string | number): Promise<OfflineDiagnosisRecord[]> {
    const now = Date.now();
    const pending = await this.getPending(userId);
    return pending.filter(
      (record) =>
        record.sync_attempts !== undefined &&
        record.sync_attempts >= MAX_SYNC_ATTEMPTS
          ? Boolean(
              record.next_retry_at &&
                new Date(record.next_retry_at).getTime() <= now,
            )
          : !record.next_retry_at ||
            new Date(record.next_retry_at).getTime() <= now,
    );
  },

  async deleteForUser(userId: string | number): Promise<void> {
    const db = await openDatabase();
    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const request = transaction.objectStore(STORE_NAME).openCursor();
        request.onsuccess = () => {
          const cursor = request.result;
          if (!cursor) return;
          const record = cursor.value as OfflineDiagnosisRecord;
          if (String(record.user_id) === String(userId)) cursor.delete();
          cursor.continue();
        };
        request.onerror = () => reject(request.error ?? new Error('Could not clear local diagnosis data.'));
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error ?? new Error('Could not clear local diagnosis data.'));
        transaction.onabort = () => reject(transaction.error ?? new Error('Clearing local diagnosis data was aborted.'));
      });
    } finally {
      db.close();
    }
  },

  async markSynced(operationId: string, serverResult?: unknown): Promise<void> {
    const db = await openDatabase();

    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.get(operationId);

        request.onsuccess = () => {
          if (!request.result) {
            reject(
              new Error(`Offline diagnosis ${operationId} was not found.`),
            );
            return;
          }

          store.put({
            ...request.result,
            sync_status: 'synced',
            synced_at: new Date().toISOString(),
            server_result: serverResult,
            sync_error: undefined,
            next_retry_at: undefined,
          });
        };

        request.onerror = () =>
          reject(request.error ?? new Error('Could not find diagnosis.'));

        transaction.oncomplete = () => resolve();
        transaction.onerror = () =>
          reject(transaction.error ?? new Error('Could not update diagnosis.'));
        transaction.onabort = () =>
          reject(transaction.error ?? new Error('Diagnosis update was aborted.'));
      });
      notifyQueueChanged();
    } finally {
      db.close();
    }
  },

  async recordSyncFailure(operationId: string, message: string): Promise<void> {
    const db = await openDatabase();

    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.get(operationId);

        request.onsuccess = () => {
          if (!request.result) {
            reject(new Error(`Offline diagnosis ${operationId} was not found.`));
            return;
          }

          const attempts = Math.min(
            (request.result.sync_attempts ?? 0) + 1,
            MAX_SYNC_ATTEMPTS,
          );
          const retryDelay =
            attempts >= MAX_SYNC_ATTEMPTS
              ? SYNC_RETRY_COOLDOWN_MS
              : 60_000 * 2 ** (attempts - 1);

          store.put({
            ...request.result,
            sync_error: message,
            sync_attempts: attempts,
            next_retry_at: new Date(Date.now() + retryDelay).toISOString(),
          });
        };

        request.onerror = () =>
          reject(request.error ?? new Error('Could not find diagnosis.'));
        transaction.oncomplete = () => resolve();
        transaction.onerror = () =>
          reject(transaction.error ?? new Error('Could not update diagnosis.'));
        transaction.onabort = () =>
          reject(transaction.error ?? new Error('Diagnosis update was aborted.'));
      });
      notifyQueueChanged();
    } finally {
      db.close();
    }
  },
};
