// PWA service worker v8 — no HTTP cache for /airbnb/ assets; Web Push handler.
const SCOPE_PATH = "/airbnb/";
const DEFAULT_URL = "/airbnb/";

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

self.addEventListener("push", (event) => {
  let payload = {};
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (_error) {
      payload = { body: event.data.text() };
    }
  }
  const title = payload.title || "Estadias";
  const body = payload.body || "";
  const url = payload.url || DEFAULT_URL;
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/airbnb/icons/icon-192.png",
      badge: "/airbnb/icons/icon-192.png",
      data: { url },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || DEFAULT_URL;
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        for (const client of clients) {
          if (client.url.includes(SCOPE_PATH) && "focus" in client) {
            return client.focus();
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(targetUrl);
        }
        return undefined;
      }),
  );
});
