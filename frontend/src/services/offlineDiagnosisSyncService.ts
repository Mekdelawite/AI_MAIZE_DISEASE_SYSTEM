
import { apiRequest } from './api';
import { diagnosisService } from './diagnosisService';
import { offlineDiagnosisStore } from './offlineDiagnosisStore';

interface OfflineSyncResponse {
  operation_id: string;
  operation_type: string;
  status: string;
  attempts?: number;
  diagnosis_id?: number | string;
}

interface OfflineSyncBatchItem {
  operation_id: string;
  success?: boolean;
  data?: { status?: string; diagnosis_id?: number | string; result?: unknown };
  error?: { message?: string };
}

interface OfflineSyncBatchResponse {
  data?: { results?: OfflineSyncBatchItem[] };
  results?: OfflineSyncBatchItem[];
}

export interface OfflineSyncSummary {
  synced: number;
  remaining: number;
}

const MAX_SYNC_REQUEST_IMAGE_BYTES = 4.5 * 1024 * 1024;
const MAX_SYNC_IMAGE_SIZE = MAX_SYNC_REQUEST_IMAGE_BYTES;
const MAX_SYNC_IMAGE_DIMENSION = 4096;
const MAX_SYNC_IMAGE_PIXELS = 12_000_000;
const MAX_BATCH_SIZE = 10;
const activeSyncs = new Map<string, Promise<OfflineSyncSummary>>();

function publishSyncStatus(status: 'syncing' | 'succeeded' | 'failed'): void {
  window.dispatchEvent(
    new CustomEvent('maizecare:offline-diagnosis-sync-status', {
      detail: { status },
    }),
  );
}

function getImageFilename(image: Blob): string {
  if (image.type === 'image/png') return 'offline-diagnosis.png';
  if (image.type === 'image/webp') return 'offline-diagnosis.webp';
  return 'offline-diagnosis.jpg';
}

async function compressImageForSync(image: Blob): Promise<Blob> {
  if (image.size <= MAX_SYNC_IMAGE_SIZE) {
    return image;
  }

  const bitmap = await createImageBitmap(image);

  try {
    let scale = Math.min(
      1,
      MAX_SYNC_IMAGE_DIMENSION / Math.max(bitmap.width, bitmap.height),
      Math.sqrt(MAX_SYNC_IMAGE_PIXELS / (bitmap.width * bitmap.height)),
    );

    for (let attempt = 0; attempt < 6; attempt++) {
      const canvas = document.createElement('canvas');

      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));

      const context = canvas.getContext('2d');

      if (!context) {
        throw new Error(
          'Could not prepare the image for synchronization.',
        );
      }

      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

      for (const quality of [0.9, 0.85, 0.8]) {
        const compressed = await new Promise<Blob>((resolve, reject) => {
          canvas.toBlob(
            (blob) => {
              if (blob) {
                resolve(blob);
              } else {
                reject(new Error('Image compression failed.'));
              }
            },
            'image/jpeg',
            quality,
          );
        });

        if (compressed.size <= MAX_SYNC_IMAGE_SIZE) {
          return compressed;
        }
      }

      const nextScale = scale * 0.85;
      if (Math.max(bitmap.width, bitmap.height) * nextScale < 1280) break;
      scale = nextScale;
    }

    throw new Error(
      'Could not prepare the image for synchronization without reducing its quality too much. The original remains in your offline queue.',
    );
  } finally {
    bitmap.close();
  }
}

/**
 * Upload pending offline diagnoses to Flask.
 * Records remain pending unless the backend confirms completion.
 */
async function performPendingDiagnosisSync(
  userId: string | number,
  language: 'en' | 'am' = 'en',
): Promise<OfflineSyncSummary> {
  const allPendingRecords = await offlineDiagnosisStore.getPending(userId);

  if (allPendingRecords.length === 0) {
    return { synced: 0, remaining: 0 };
  }

  if (!navigator.onLine) {
    return {
      synced: 0,
      remaining: allPendingRecords.length,
    };
  }

  const pendingRecords = await offlineDiagnosisStore.getReadyToSync(userId);
  if (pendingRecords.length === 0) {
    return { synced: 0, remaining: allPendingRecords.length };
  }

  if (!(await diagnosisService.isBackendAvailable())) {
    publishSyncStatus('failed');
    return { synced: 0, remaining: allPendingRecords.length };
  }

  publishSyncStatus('syncing');
  let synced = 0;
  const recordsByMetadata = new Map<string, typeof pendingRecords>();
  pendingRecords.forEach((record) => {
    const recordLanguage = record.language ?? language;
    const explain = record.explain ?? false;
    const key = `${recordLanguage}:${explain}`;
    const records = recordsByMetadata.get(key) ?? [];
    records.push(record);
    recordsByMetadata.set(key, records);
  });

  for (const [metadataKey, records] of recordsByMetadata) {
    const [recordLanguage, explainValue] = metadataKey.split(':');

    for (let offset = 0; offset < records.length; offset += MAX_BATCH_SIZE) {
      if (!navigator.onLine) break;

      const batch = records.slice(offset, offset + MAX_BATCH_SIZE);
      const prepared: Array<{ record: (typeof batch)[number]; image: Blob }> = [];
      for (const record of batch) {
        try {
          prepared.push({
            record,
            image: await compressImageForSync(record.image),
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          await offlineDiagnosisStore.recordSyncFailure(record.operation_id, message);
          console.error('Could not prepare an offline diagnosis for sync:', {
            operationId: record.operation_id,
            message,
          });
        }
      }

      if (prepared.length === 0) continue;

      const requestBatches: Array<typeof prepared> = [];
      let requestBatch: typeof prepared = [];
      let requestImageBytes = 0;
      for (const entry of prepared) {
        if (entry.image.size > MAX_SYNC_REQUEST_IMAGE_BYTES) {
          const message = 'The prepared image is larger than the synchronization request limit.';
          await offlineDiagnosisStore.recordSyncFailure(entry.record.operation_id, message);
          continue;
        }

        if (
          requestBatch.length > 0 &&
          requestImageBytes + entry.image.size > MAX_SYNC_REQUEST_IMAGE_BYTES
        ) {
          requestBatches.push(requestBatch);
          requestBatch = [];
          requestImageBytes = 0;
        }

        requestBatch.push(entry);
        requestImageBytes += entry.image.size;
      }
      if (requestBatch.length > 0) requestBatches.push(requestBatch);

      let stopAfterBatch = false;
      for (const requestItems of requestBatches) {
        if (!navigator.onLine) break;

        const formData = new FormData();
        requestItems.forEach(({ record, image }) => {
          formData.append('operation_ids', record.operation_id);
          formData.append('images', image, getImageFilename(image));
        });
        formData.append('operation_type', 'diagnosis');
        formData.append('language', recordLanguage);
        formData.append('explain', explainValue);

        try {
          const response = await apiRequest<OfflineSyncBatchResponse>(
            '/api/sync/batch',
            { method: 'POST', body: formData, timeoutMs: 120000 },
          );
          const results = response?.data?.results ?? response?.results ?? [];
          const resultById = new Map(
            results.map((item) => [item.operation_id, item]),
          );

          for (const { record } of requestItems) {
            const result = resultById.get(record.operation_id);
            if (result?.success) {
              await offlineDiagnosisStore.markSynced(
                record.operation_id,
                result.data,
              );
              synced += 1;
            } else {
              const message = result?.error?.message || 'Server did not confirm completion.';
              await offlineDiagnosisStore.recordSyncFailure(
                record.operation_id,
                message,
              );
              console.error('Offline diagnosis remains pending:', {
                operationId: record.operation_id,
                message,
              });
            }
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          for (const { record } of requestItems) {
            await offlineDiagnosisStore.recordSyncFailure(
              record.operation_id,
              message,
            );
          }
          console.error('Offline diagnosis batch sync failed:', {
            message,
            status: (error as { status?: number })?.status,
            code: (error as { code?: string })?.code,
          });
          stopAfterBatch = true;
          break;
        }
      }

      if (stopAfterBatch) break;
      if (!navigator.onLine) break;
    }

    if (!navigator.onLine) {
      break;
    }
  }

  const remaining = (await offlineDiagnosisStore.getPending(userId)).length;
  publishSyncStatus(remaining === 0 ? 'succeeded' : 'failed');

  return {
    synced,
    remaining,
  };
}

export function syncPendingDiagnoses(
  userId: string | number,
  language: 'en' | 'am' = 'en',
): Promise<OfflineSyncSummary> {
  const userKey = String(userId);
  const currentSync = activeSyncs.get(userKey);
  if (currentSync) return currentSync;

  const lockManager =
    typeof navigator !== 'undefined' ? navigator.locks : undefined;
  const syncPromise = lockManager
    ? lockManager.request(
        `maizecare-offline-diagnosis-sync-${userKey}`,
        { ifAvailable: true },
        async (lock) => {
          if (!lock) {
            return {
              synced: 0,
              remaining: (await offlineDiagnosisStore.getPending(userId)).length,
            };
          }
          return performPendingDiagnosisSync(userId, language);
        },
      )
    : performPendingDiagnosisSync(userId, language);

  activeSyncs.set(userKey, syncPromise);
  const clearSync = () => {
    if (activeSyncs.get(userKey) === syncPromise) {
      activeSyncs.delete(userKey);
    }
  };
  void syncPromise.then(clearSync, clearSync);
  return syncPromise;
}
