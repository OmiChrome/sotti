self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', (e) => {
  // Pass-through fetch (no caching). Just enough to make the app a valid PWA.
  e.respondWith(fetch(e.request).catch(() => new Response("Network error occurred.")));
});
