// Pass-through service worker.
//
// Registered solely to satisfy the installable-PWA criteria
// (manifest + active SW with a fetch handler). No caching: the
// browser's HTTP cache handles repeat fetches for /static/ assets,
// and adding a SW cache layer on top introduced stale-content bugs
// every time a static file changed (cache key is the URL, which
// doesn't change between deploys).

self.addEventListener('install', function(event) {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function(event) {
  // Sweep every cache this SW has ever created so users upgrading
  // from a caching version don't keep serving stale content.
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(cacheNames.map(function(name) {
        return caches.delete(name);
      }));
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(event) {
  // Intentional no-op: let the browser handle every request
  // natively. Present only to satisfy PWA installability checks
  // that look for a fetch handler on the active SW.
});
