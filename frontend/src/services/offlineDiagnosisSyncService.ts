
import { apiRequest } from './api';
import { offlineDiagnosisStore } from './offlineDiagnosisStore';

interface OfflineSyncResponse {
  operation_id: string;
  operation_type: string;
  status: string;
  attempts?: number;
  diagnosis_id?: number | string;
}

export interface OfflineSyncSummary {
  synced: number;
  remaining: number;
}

const MAX_SYNC_IMAGE_SIZE = 450 * 1024;

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
      1600 / Math.max(bitmap.width, bitmap.height),
    );

    for (let attempt = 0; attempt < 8; attempt++) {
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

      for (const quality of [0.85, 0.75, 0.65, 0.55, 0.45, 0.35]) {
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

      scale *= 0.8;
    }

    throw new Error(
      'Could not compress the image below 450 KB. Please select a smaller image.',
    );
  } finally {
    bitmap.close();
  }
}

/**
 * Upload pending offline diagnoses to Flask.
 * Records remain pending unless the backend confirms completion.
 */
export async function syncPendingDiagnoses(
  userId: string | number,
  language: 'en' | 'am' = 'en',
): Promise<OfflineSyncSummary> {
  if (!navigator.onLine) {
    const pending = await offlineDiagnosisStore.getPending(userId);

    return {
      synced: 0,
      remaining: pending.length,
    };
  }

  const pendingRecords = await offlineDiagnosisStore.getPending(userId);
  let synced = 0;

  // Stop processing the queue when a record fails.
  for (const record of pendingRecords) {
    if (!navigator.onLine) break;

    try {
      // Compress old IndexedDB images before uploading.
      const image = await compressImageForSync(record.image);

      const formData = new FormData();

      formData.append('operation_id', record.operation_id);
      formData.append('operation_type', 'diagnosis');
      formData.append('language', language);
      formData.append('explain', 'false');
      formData.append('image', image, getImageFilename(image));

      const result = await apiRequest<OfflineSyncResponse>('/api/sync', {
        method: 'POST',
        body: formData,
        timeoutMs: 60000,
      });

      if (
        result?.operation_id === record.operation_id &&
        result.status === 'completed'
      ) {
        await offlineDiagnosisStore.markSynced(record.operation_id);
        synced += 1;
      } else {
        console.error('Offline sync was not confirmed:', result);
        break;
      }
    } catch (error) {
      console.error('Offline sync error:', {
        operationId: record.operation_id,
        message: error instanceof Error ? error.message : String(error),
        status: (error as { status?: number })?.status,
        code: (error as { code?: string })?.code,
        details: (error as { details?: unknown })?.details,
      });

      break;
    }
  }

  const remaining = (await offlineDiagnosisStore.getPending(userId)).length;

  return {
    synced,
    remaining,
  };
}
