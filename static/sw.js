const CACHE_NAME = 'rozumnyk-offline-v5';
const OFFLINE_PAGE = '/offline';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll([
      OFFLINE_PAGE,
      '/static/favicon.svg',
      '/static/i18n-en.js?v=3',
    ])),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith('rozumnyk-offline-') && key !== CACHE_NAME)
      .map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', (event) => {
  if (event.data?.type !== 'CACHE_LESSON' || typeof event.data.url !== 'string') return;
  event.waitUntil((async () => {
    const url = new URL(event.data.url, self.location.origin);
    if (url.origin !== self.location.origin || !url.pathname.startsWith('/lesson/')) return;
    const response = await fetch(url.href, { credentials: 'same-origin' });
    if (!response.ok) return;
    const cache = await caches.open(CACHE_NAME);
    await cache.put(url.href, response.clone());
    event.source?.postMessage({ type: 'LESSON_CACHED', url: url.href });
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET' || request.mode !== 'navigate') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/teacher') || url.pathname.startsWith('/my-class') ||
      url.pathname.startsWith('/join') || url.pathname.startsWith('/f/') ||
      url.pathname.startsWith('/m/')) return;

  const publicPage = url.pathname === '/' || url.pathname === '/missions' ||
    url.pathname === '/laboratories' || url.pathname.startsWith('/subject/');

  if (publicPage) {
    const update = (async () => {
      const cache = await caches.open(CACHE_NAME);
      const response = await fetch(request);
      if (response.ok) await cache.put(request, response.clone());
      return response;
    })();
    event.waitUntil(update.then(() => undefined).catch(() => undefined));
    event.respondWith((async () => {
      const cached = await caches.match(request);
      if (cached) return cached;
      try {
        return await update;
      } catch (error) {
        return (await caches.match(OFFLINE_PAGE)) || Response.error();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    try {
      return await fetch(request);
    } catch (error) {
      if (url.pathname.startsWith('/lesson/')) {
        const cached = await caches.match(request);
        if (cached) return cached;
      }
      return (await caches.match(OFFLINE_PAGE)) || Response.error();
    }
  })());
});
