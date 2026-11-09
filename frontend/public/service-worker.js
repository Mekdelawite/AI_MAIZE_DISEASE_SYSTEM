const SHELL_CACHE = 'maizecare-shell-v3';
const LEGACY_SHELL_CACHES = ['maizecare-shell-v1', 'maizecare-shell-v2'];
const MODEL_CACHE = 'maizecare-maize-model-v1';
const VALIDITY_MODEL_CACHE = 'maizecare-maize-validity-model-v1';
const CRITICAL_ASSETS = '__MAIZECARE_CRITICAL_ASSETS__';

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

    // Vite supplies the entry and offline-critical route dependency graph.
    // Other route chunks and images are cached only when requested.
    await Promise.all(CRITICAL_ASSETS.map(async (fileName) => {
      const url = new URL(fileName, scopeRoot).href;
      const key = cacheKey(url);
      if (await cache.match(key)) return;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Unable to precache required app asset: ${fileName}`);
      await cache.put(key, response);
    }));

    // Keep model caches across app updates; bump the cache version when model
    // contents change so unchanged weights are not downloaded again.
    const modelCache = await caches.open(MODEL_CACHE);

    await Promise.all(MODEL_ASSETS.map(async (fileName) => {
      const url = new URL(fileName, scopeRoot).href;
      const key = cacheKey(url);
      if (await modelCache.match(key)) return;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Unable to cache required maize model file: ${fileName}`);
      }

      await modelCache.put(key, response);
    }));

    const validityModelCache = await caches.open(VALIDITY_MODEL_CACHE);
    await Promise.all(VALIDITY_MODEL_ASSETS.map(async (fileName) => {
      const url = new URL(fileName, scopeRoot).href;
      const key = cacheKey(url);
      if (await validityModelCache.match(key)) return;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Unable to cache required maize validity model file: ${fileName}`);
      }

      await validityModelCache.put(key, response);
    }));

    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // Keep model and other application caches; remove only the known obsolete
    // shell after the complete v2 shell has installed successfully.
    await Promise.all(LEGACY_SHELL_CACHES.map((cacheName) => caches.delete(cacheName)));
    await self.clients.claim();
  })());
});

self.addEventListener('push', (event) => {
  event.waitUntil((async () => {
    let payload = {};
    try {
      const parsed = event.data ? event.data.json() : {};
      payload = parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      payload = {};
    }

    const body = typeof payload.body === 'string' && payload.body
      ? payload.body
      : 'A new farm update is ready. Open MaizeCare AI to view it.';
    const requestedUrl = typeof payload.url === 'string'
      ? new URL(payload.url, self.location.origin)
      : new URL('/farmer/dashboard', self.location.origin);
    const targetUrl = requestedUrl.origin === self.location.origin &&
      requestedUrl.pathname.startsWith('/farmer/')
      ? requestedUrl.href
      : new URL('/farmer/dashboard', self.location.origin).href;

    await self.registration.showNotification('MaizeCare AI', {
      body,
      icon: new URL('maizecare-icon-192.png', scopeRoot).href,
      badge: new URL('maizecare-icon-192.png', scopeRoot).href,
      data: { url: targetUrl },
    });
  })());
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const requestedUrl = typeof event.notification.data?.url === 'string'
      ? new URL(event.notification.data.url, self.location.origin)
      : new URL('/farmer/dashboard', self.location.origin);
    const targetUrl = requestedUrl.origin === self.location.origin &&
      requestedUrl.pathname.startsWith('/farmer/')
      ? requestedUrl.href
      : new URL('/farmer/dashboard', self.location.origin).href;
    const windows = await self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true,
    });
    for (const client of windows) {
      if (new URL(client.url).origin !== self.location.origin) continue;
      const navigatedClient = await client.navigate(targetUrl);
      await (navigatedClient || client).focus();
      return;
    }
    await self.clients.openWindow(targetUrl);
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
