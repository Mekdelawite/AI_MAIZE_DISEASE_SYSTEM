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
const VALIDITY_MODEL_URL =
  `${import.meta.env.BASE_URL}models/maize-validity-graph/model.json`;
const VALIDITY_MODEL_CACHE = 'maizecare-maize-validity-model-v1';
const VALIDITY_IMAGE_SIZE = 160;
const VALID_MAIZE_THRESHOLD = 0.5;
const validatedFiles = new WeakMap<File, Promise<void>>();

export interface LocalDiagnosisResult {
  className: (typeof CLASS_NAMES)[number];
  confidence: number;
  probabilities: number[];
}

async function readModelResource(
  url: string | URL | Request,
  cacheName: string = MODEL_CACHE,
  requestInit?: RequestInit,
): Promise<Response> {
  const resourceUrl = typeof url === 'string'
    ? url
    : url instanceof URL
      ? url.toString()
      : url.url;
  const cache = await caches.open(cacheName);
  const cached = await cache.match(resourceUrl);

  if (cached) return cached;

  if (!navigator.onLine) {
    throw new Error(
      'The offline model is not cached on this device yet. Connect to the internet and run a local diagnosis once to download it.',
    );
  }

  const response = await fetch(resourceUrl, {
    ...requestInit,
    credentials: requestInit?.credentials ?? 'same-origin',
  });

  if (!response.ok) {
    throw new Error(`Unable to download the offline model (${response.status}).`);
  }

  await cache.put(resourceUrl, response.clone());
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
  const shardResponses = await Promise.all(shardUrls.map((url) => readModelResource(url)));
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
let validityModelPromise: Promise<tfTypes.GraphModel> | null = null;

async function loadValidityModel(): Promise<tfTypes.GraphModel> {
  const tf = await getTensorflow();

  const modelUrl = new URL(
    VALIDITY_MODEL_URL,
    window.location.href,
  ).toString();

  const model = await tf.loadGraphModel(modelUrl, {
    fetchFunc: (url, init) =>
      readModelResource(
        url,
        VALIDITY_MODEL_CACHE,
        init,
      ),
  });

  const inputShape = model.inputs[0]?.shape;

  if (
    inputShape?.[1] !== VALIDITY_IMAGE_SIZE ||
    inputShape?.[2] !== VALIDITY_IMAGE_SIZE ||
    inputShape?.[3] !== 3
  ) {
    model.dispose();
    throw new Error(
      'The maize-image validation model has an unexpected input shape.',
    );
  }

  return model;
}

async function getValidityModel(): Promise<tfTypes.GraphModel> {
  const tf = await getTensorflow();
  await tf.ready();

  if (!validityModelPromise) {
    validityModelPromise = loadValidityModel().catch((error) => {
      validityModelPromise = null;
      throw error;
    });
  }

  return validityModelPromise;
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

async function validateMaizeLeafImage(
  tf: typeof import('@tensorflow/tfjs'),
  image: HTMLImageElement,
): Promise<void> {
  const model = await getValidityModel();
  const canvas = document.createElement('canvas');
  canvas.width = VALIDITY_IMAGE_SIZE;
  canvas.height = VALIDITY_IMAGE_SIZE;

  const context = canvas.getContext('2d', {
    willReadFrequently: true,
  });

  if (!context) {
    throw new Error(
      'This browser cannot prepare the image for validation.',
    );
  }

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  context.drawImage(
    image,
    0,
    0,
    VALIDITY_IMAGE_SIZE,
    VALIDITY_IMAGE_SIZE,
  );

  const pixels = tf.browser.fromPixels(canvas).toFloat();
  const input = pixels.div(127.5).sub(1).expandDims(0);
  pixels.dispose();

  let output: tfTypes.Tensor | tfTypes.Tensor[] | tfTypes.NamedTensorMap | undefined;

  try {
    output = model.execute(input);

    let scoreTensor: tfTypes.Tensor;

    if (Array.isArray(output)) {
      scoreTensor = output[0];
    } else if (output instanceof tf.Tensor) {
      scoreTensor = output;
    } else {
      const namedOutput = output as tfTypes.NamedTensorMap;
      scoreTensor = namedOutput.output_0;
    }

    if (!scoreTensor) {
      throw new Error(
        'The maize-image validation model returned no prediction.',
      );
    }

    const scores = Array.from(await scoreTensor.data());

    if (
      scores.length !== 1 ||
      !Number.isFinite(scores[0]) ||
      scores[0] < 0 ||
      scores[0] > 1
    ) {
      throw new Error(
        'The maize-image validation model returned an invalid prediction.',
      );
    }

    if (scores[0] < VALID_MAIZE_THRESHOLD) {
      throw new Error(
        'This image does not appear to show a maize leaf. Please select a clear photo of a maize leaf and try again.',
      );
    }
  } finally {
    input.dispose();

    if (output) {
      if (Array.isArray(output)) {
        output.forEach((tensor) => tensor.dispose());
      } else if (output instanceof tf.Tensor) {
        output.dispose();
      } else {
        Object.values(output).forEach((tensor) => tensor.dispose());
      }
    }
  }
}

async function areModelResourcesCached(
  cacheName: string,
  modelUrl: string,
): Promise<boolean> {
  try {
    const cache = await caches.open(cacheName);
    const modelResponse = await cache.match(modelUrl);
    if (!modelResponse) return false;

    const artifacts = await modelResponse.json();
    const shardUrls: string[] = (artifacts.weightsManifest || []).flatMap(
      (group: { paths: string[] }) =>
        group.paths.map((path) => new URL(path, modelUrl).toString()),
    );

    return shardUrls.length > 0 &&
      (await Promise.all(shardUrls.map((url) => cache.match(url)))).every(Boolean);
  } catch {
    return false;
  }
}

export const localDiagnosisService = {
  async isModelCached(): Promise<boolean> {
    if (typeof caches === 'undefined') return false;
    const diseaseModelUrl = new URL(MODEL_URL, window.location.href).toString();
    const validityModelUrl = new URL(VALIDITY_MODEL_URL, window.location.href).toString();
    const [diseaseModelCached, validityModelCached] = await Promise.all([
      areModelResourcesCached(MODEL_CACHE, diseaseModelUrl),
      areModelResourcesCached(VALIDITY_MODEL_CACHE, validityModelUrl),
    ]);

    return diseaseModelCached && validityModelCached;
  },

  async validateImage(file: File): Promise<void> {
    const existingValidation = validatedFiles.get(file);
    if (existingValidation) {
      return existingValidation;
    }

    const validation = (async () => {
      const tf = await getTensorflow();
      const image = await loadImage(file);
      await validateMaizeLeafImage(tf, image);
    })();
    validatedFiles.set(file, validation);

    try {
      await validation;
    } catch (error: unknown) {
      if (validatedFiles.get(file) === validation) {
        validatedFiles.delete(file);
      }
      throw error;
    }
  },

  async predict(
    file: File,
    userId?: string | number,
  ): Promise<LocalDiagnosisResult> {
    await this.validateImage(file);
    const tf = await getTensorflow();
    const image = await loadImage(file);

    // Run the existing four-class disease model only after validity passes.
    const model = await getModel();
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

      // Persist predictions made while offline. Online submissions remain under the existing backend workflow.
      if (
        !navigator.onLine &&
        ((typeof userId === 'number' && Number.isFinite(userId)) ||
          (typeof userId === 'string' && userId.trim()))
      ) {
        await offlineDiagnosisStore.save(result, file, userId);
      }

      return result;
    } finally {
      input.dispose();
    }
  },
};
