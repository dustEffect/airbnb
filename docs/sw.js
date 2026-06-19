// PWA service worker v7 — no HTTP cache for /airbnb/ assets.
const SCOPE_PATH = "/airbnb/";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (!url.pathname.startsWith(SCOPE_PATH)) return;
  event.respondWith(fetch(event.request, { cache: "no-store" }));
});
