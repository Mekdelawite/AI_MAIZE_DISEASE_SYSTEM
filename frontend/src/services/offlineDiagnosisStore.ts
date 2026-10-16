
import type { LocalDiagnosisResult } from './localDiagnosisService';

const DB_NAME = 'maizecare-offline-db';
const DB_VERSION = 1;
const STORE_NAME = 'diagnoses';
const MAX_IMAGE_SIZE = 450 * 1024;

export interface OfflineDiagnosisRecord {
  operation_id: string;
  className: LocalDiagnosisResult['className'];
  confidence: number;
  probabilities: number[];
  created_at: string;
  sync_status: 'pending' | 'synced';
  image: Blob;
}

async function compressImage(image: Blob): Promise<Blob> {
  if (image.size <= MAX_IMAGE_SIZE) {
    return image;
  }

  const bitmap = await createImageBitmap(image);

  try {
    let scale = Math.min(
      1,
      1600 / Math.max(bitmap.width, bitmap.height),
    );

    for (let resizeAttempt = 0; resizeAttempt < 8; resizeAttempt++) {
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));

      const context = canvas.getContext('2d');

      if (!context) {
        throw new Error('Could not prepare the diagnosis image.');
      }

      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

      for (const quality of [0.85, 0.75, 0.65, 0.55, 0.45, 0.35]) {
        const compressed = await new Promise<Blob>((resolve, reject) => {
          canvas.toBlob(
            (blob) => {
              if (blob) {
                resolve(blob);
              } else {
                reject(new Error('Could not compress the diagnosis image.'));
              }
            },
            'image/jpeg',
            quality,
          );
        });

        if (compressed.size <= MAX_IMAGE_SIZE) {
          return compressed;
        }
      }

      scale *= 0.8;
    }

    throw new Error(
      'Could not reduce the image below 450 KB. Please choose a smaller image.',
    );
  } finally {
    bitmap.close();
  }
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

      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, {
          keyPath: 'operation_id',
        });

        store.createIndex('created_at', 'created_at');
        store.createIndex('sync_status', 'sync_status');
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
  ): Promise<OfflineDiagnosisRecord> {
    const db = await openDatabase();

    try {
      const compressedImage = await compressImage(image);

      const record: OfflineDiagnosisRecord = {
        operation_id: crypto.randomUUID(),
        className: result.className,
        confidence: result.confidence,
        probabilities: [...result.probabilities],
        created_at: new Date().toISOString(),
        sync_status: 'pending',
        image: compressedImage,
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

      return record;
    } finally {
      db.close();
    }
  },

  async getAll(): Promise<OfflineDiagnosisRecord[]> {
    const db = await openDatabase();

    try {
      return await new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readonly');
        const request = transaction.objectStore(STORE_NAME).getAll();

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

  async getPending(): Promise<OfflineDiagnosisRecord[]> {
    const records = await this.getAll();
    return records.filter((record) => record.sync_status === 'pending');
  },

  async markSynced(operationId: string): Promise<void> {
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
    } finally {
      db.close();
    }
  },
};
