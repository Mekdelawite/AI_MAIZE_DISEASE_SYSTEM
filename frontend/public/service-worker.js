const SHELL_CACHE = 'maizecare-shell-v2';
const LEGACY_SHELL_CACHE = 'maizecare-shell-v1';
const MODEL_CACHE = 'maizecare-maize-model-v1';
const VALIDITY_MODEL_CACHE = 'maizecare-maize-validity-model-v1';
const CRITICAL_ASSETS = '__MAIZECARE_CRITICAL_ASSETS__';
const OPTIONAL_ASSETS = '__MAIZECARE_OPTIONAL_ASSETS__';

const MODEL_ASSETS = [
  'models/maize/model.json',
  'models/maize/group1-shard1of3.bin',
  'models/maize/group1-shard2of3.bin',
  'models/maize/group1-shard3of3.bin',
];

const VALIDITY_MODEL_ASSETS = [
  'models/maize-validity-graph/model.json',
  'models/maize-validity-graph/group1-shard1of3.bin',
  'models/maize-validity-graph/group1-shard2of3.bin',
  'models/maize-validity-graph/group1-shard3of3.bin',
];

const scopeRoot = new URL('./', self.registration.scope);
const indexUrl = new URL('index.html', scopeRoot);

function cacheKey(url) {
  const normalized = new URL(url, self.registration.scope);
  normalized.search = '';
  normalized.hash = '';
  return normalized.href;
}

async function cacheShellResponse(response) {
  if (!response || !response.ok) throw new Error('Unable to cache the MaizeCare app entry page.');
  const cache = await caches.open(SHELL_CACHE);
  await cache.put(scopeRoot.href, response.clone());
  await cache.put(indexUrl.href, response.clone());
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE);
    const entryResponse = await fetch(indexUrl.href, { cache: 'reload' }).catch(() => fetch(scopeRoot.href));
    await cacheShellResponse(entryResponse);

    // Vite supplies the exact hashed JS/CSS output paths at build time. These
    // are required to render the app, so do not activate an incomplete shell.
    await Promise.all(CRITICAL_ASSETS.map(async (fileName) => {
      const url = new URL(fileName, scopeRoot).href;
      const response = await fetch(url, { cache: 'reload' });
      if (!response.ok) throw new Error(`Unable to precache required app asset: ${fileName}`);
      await cache.put(cacheKey(url), response);
    }));
    
    // Precache both models so validity checks and diagnosis work offline.
    const modelCache = await caches.open(MODEL_CACHE);

    await Promise.all(MODEL_ASSETS.map(async (fileName) => {
      const url = new URL(fileName, scopeRoot).href;
      const response = await fetch(url, { cache: 'reload' });

      if (!response.ok) {
        throw new Error(`Unable to cache required maize model file: ${fileName}`);
      }

      await modelCache.put(cacheKey(url), response);
    }));

    const validityModelCache = await caches.open(VALIDITY_MODEL_CACHE);
    await Promise.all(VALIDITY_MODEL_ASSETS.map(async (fileName) => {
      const url = new URL(fileName, scopeRoot).href;
      const response = await fetch(url, { cache: 'reload' });

      if (!response.ok) {
        throw new Error(`Unable to cache required maize validity model file: ${fileName}`);
      }

      await validityModelCache.put(cacheKey(url), response);
    }));

    // Images and fonts improve the experience but must not block SW install.
    await Promise.all(OPTIONAL_ASSETS.map(async (fileName) => {
      try {
        const url = new URL(fileName, scopeRoot).href;
        const response = await fetch(url, { cache: 'reload' });
        if (response.ok) await cache.put(cacheKey(url), response);
      } catch {
        // Retry on demand when the asset is requested later.
      }
    }));

    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // Keep model and other application caches; remove only the known obsolete
    // shell after the complete v2 shell has installed successfully.
    await caches.delete(LEGACY_SHELL_CACHE);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.includes('/api/')) return;

  const modelCacheName = url.pathname.includes('/models/maize-validity-graph/')
    ? VALIDITY_MODEL_CACHE
    : url.pathname.includes('/models/maize/')
      ? MODEL_CACHE
      : null;

  if (modelCacheName) {
    event.respondWith((async () => {
      const cache = await caches.open(modelCacheName);
      const key = cacheKey(request.url);
      const cached = await cache.match(key);
      if (cached) return cached;
      const response = await fetch(request);
      if (response.ok) await cache.put(key, response.clone());
      return response;
    })());
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        if (response.ok) await cacheShellResponse(response.clone());
        return response;
      } catch {
        const cache = await caches.open(SHELL_CACHE);
        return (await cache.match(scopeRoot.href)) || (await cache.match(indexUrl.href)) || Response.error();
      }
    })());
    return;
  }

  const isAppAsset = ['script', 'style', 'image', 'font', 'worker'].includes(request.destination) || url.pathname.includes('/assets/');
  if (!isAppAsset) return;

  event.respondWith((async () => {
    const cache = await caches.open(SHELL_CACHE);
    const key = cacheKey(request.url);
    const cached = await cache.match(key);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) await cache.put(key, response.clone());
    return response;
  })());
});
