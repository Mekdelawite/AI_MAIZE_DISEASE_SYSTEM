import type * as tfTypes from '@tensorflow/tfjs';
import { offlineDiagnosisStore } from './offlineDiagnosisStore';
const MODEL_URL = `${import.meta.env.BASE_URL}models/maize/model.json`;
const MODEL_CACHE = 'maizecare-maize-model-v1';
const CLASS_NAMES = [
  'Northern Leaf Blight',
  'Common Rust',
  'Gray Leaf Spot',
  'Healthy',
] as const;

export interface LocalDiagnosisResult {
  className: (typeof CLASS_NAMES)[number];
  confidence: number;
  probabilities: number[];
}

async function readModelResource(url: string): Promise<Response> {
  const cache = await caches.open(MODEL_CACHE);
  const cached = await cache.match(url);
  if (cached) return cached;

  if (!navigator.onLine) {
    throw new Error('The offline model is not cached on this device yet. Connect to the internet and run a local diagnosis once to download it.');
  }

  const response = await fetch(url, { credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error(`Unable to download the offline model (${response.status}).`);
  }
  await cache.put(url, response.clone());
  return response;
}

async function cacheLoadedRuntimeAssets(): Promise<void> {
  if (!navigator.onLine || typeof caches === 'undefined') return;
  const cache = await caches.open('maizecare-shell-v2');
  const urls = performance
    .getEntriesByType('resource')
    .map((entry) => entry.name)
    .filter((rawUrl) => {
      try {
        const url = new URL(rawUrl);
        return url.origin === window.location.origin &&
          !url.pathname.includes('/api/') &&
          /\.(m?js|css)$/.test(url.pathname);
      } catch {
        return false;
      }
    });

  await Promise.all(urls.map(async (url) => {
    if (await cache.match(url)) return;
    try {
      const response = await fetch(url, { credentials: 'same-origin' });
      if (response.ok) await cache.put(url, response);
    } catch {
      // Keep online inference usable if an optional asset cache write fails.
    }
  }));
}

let tfRuntime: typeof import('@tensorflow/tfjs') | null = null;

async function getTensorflow(): Promise<typeof import('@tensorflow/tfjs')> {
  if (!tfRuntime) {
    tfRuntime = await import('@tensorflow/tfjs');
    await cacheLoadedRuntimeAssets();
  }
  return tfRuntime;
}

async function loadLocalModel(): Promise<tfTypes.LayersModel> {
  const tf = await getTensorflow();
  const modelUrl = new URL(MODEL_URL, window.location.href).toString();
  const modelResponse = await readModelResource(modelUrl);
  const artifacts = await modelResponse.json();

  if (artifacts.format !== 'layers-model' || !artifacts.modelTopology || !Array.isArray(artifacts.weightsManifest)) {
    throw new Error('The cached maize model files are invalid or incomplete.');
  }

  const groups = artifacts.weightsManifest as Array<{
    paths: string[];
    weights: tfTypes.io.WeightsManifestEntry[];
  }>;
  const shardUrls = groups.flatMap((group) =>
    group.paths.map((path) => new URL(path, modelUrl).toString())
  );
  const shardResponses = await Promise.all(shardUrls.map(readModelResource));
  const shardBuffers = await Promise.all(shardResponses.map((response) => response.arrayBuffer()));
  const totalBytes = shardBuffers.reduce((sum, buffer) => sum + buffer.byteLength, 0);
  const weightData = new Uint8Array(totalBytes);
  let offset = 0;
  shardBuffers.forEach((buffer) => {
    weightData.set(new Uint8Array(buffer), offset);
    offset += buffer.byteLength;
  });

  const model = await tf.loadLayersModel(
    tf.io.fromMemory({
      modelTopology: artifacts.modelTopology,
      weightSpecs: groups.flatMap((group) => group.weights),
      weightData: weightData.buffer,
      format: 'layers-model',
    })
  );

  const inputShape = model.inputs[0]?.shape;
  const outputShape = model.outputs[0]?.shape;
  if (inputShape?.[1] !== 224 || inputShape?.[2] !== 224 || inputShape?.[3] !== 3 || outputShape?.[outputShape.length - 1] !== 4) {
    model.dispose();
    throw new Error('The downloaded maize model has an unexpected input or output shape.');
  }
  return model;
}

let modelPromise: Promise<tfTypes.LayersModel> | null = null;

async function getModel(): Promise<tfTypes.LayersModel> {
  const tf = await getTensorflow();
  await tf.ready();
  if (!modelPromise) {
    modelPromise = loadLocalModel().catch((error) => {
      modelPromise = null;
      throw error;
    });
  }
  return modelPromise;
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('The selected image could not be decoded.'));
    };
    image.src = objectUrl;
  });
}

export const localDiagnosisService = {
  async isModelCached(): Promise<boolean> {
    if (typeof caches === 'undefined') return false;
    const cache = await caches.open(MODEL_CACHE);
    const modelUrl = new URL(MODEL_URL, window.location.href).toString();
    const cachedResponse = await cache.match(modelUrl);
    if (!cachedResponse) return false;

    try {
      const artifacts = await cachedResponse.json();
      const shardUrls: string[] = (artifacts.weightsManifest || []).flatMap(
        (group: { paths: string[] }) => group.paths.map((path) => new URL(path, modelUrl).toString())
      );
      return shardUrls.length > 0 && (await Promise.all(shardUrls.map((url) => cache.match(url)))).every(Boolean);
    } catch {
      return false;
    }
  },

  async predict(file: File): Promise<LocalDiagnosisResult> {
    const tf = await getTensorflow();
    const model = await getModel();
    const image = await loadImage(file);
    const canvas = document.createElement('canvas');
    canvas.width = 224;
    canvas.height = 224;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) throw new Error('This browser cannot prepare the image for local diagnosis.');

    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    context.drawImage(image, 0, 0, 224, 224);

    // Model training and server inference use MobileNetV2 preprocess_input.
    // Apply its (pixel / 127.5) - 1 transform exactly once here.
    const pixels = tf.browser.fromPixels(canvas).toFloat();
    const input = pixels.div(127.5).sub(1).expandDims(0);
    pixels.dispose();

    try {
      const output = model.predict(input) as tfTypes.Tensor;
      const probabilities: number[] = Array.from(await output.data()) as number[];
      output.dispose();
      if (probabilities.length !== CLASS_NAMES.length || probabilities.some((value) => !Number.isFinite(value))) {
        throw new Error('The local model returned invalid prediction values.');
      }
      const bestIndex = probabilities.indexOf(Math.max(...probabilities));
      const result: LocalDiagnosisResult = {
  className: CLASS_NAMES[bestIndex],
  confidence: probabilities[bestIndex],
  probabilities,
};

// Persist predictions made while offline.
// Online submissions remain under the existing backend workflow.
if (!navigator.onLine) {
  await offlineDiagnosisStore.save(result, file);
}

return result;
    } finally {
      input.dispose();
    }
  },
};
