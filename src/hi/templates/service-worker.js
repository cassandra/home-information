// Static-asset cache + pass-through for everything else.
//
// The service worker intercepts only requests whose path begins with
// Django's STATIC_URL. Cache-first with on-demand population on miss.
// Everything else — dynamic pages, the polling endpoint, MJPEG video
// streams (multipart/x-mixed-replace) — passes through to the
// browser's native fetch path. Firefox in particular mishandles
// multiple concurrent multipart streams routed through a service
// worker's respondWith, so this scoping is deliberate.

var CACHE_VERSION = 2;
var STATIC_CACHE_NAME = 'static-cache-' + CACHE_VERSION;
var STATIC_URL_PREFIX = '{{ STATIC_URL }}';

self.addEventListener('install', function(event) {
  // Take over immediately rather than waiting for all existing
  // controlled pages to close. Combined with ``clients.claim()`` on
  // activate, this ensures the new SW handles fetches as soon as it
  // is installed.
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function(event) {
  // Sweep any caches that don't match the current version. Bumping
  // CACHE_VERSION invalidates everything previously cached.
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(name) {
          if (name !== STATIC_CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') {
    return;
  }
  if (!event.request.url.startsWith('http')) {
    return;
  }
  var pathname = new URL(event.request.url).pathname;
  if (!pathname.startsWith(STATIC_URL_PREFIX)) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      if (cached) {
        return cached;
      }
      return fetch(event.request).then(function(response) {
        if (response && response.ok) {
          var clone = response.clone();
          caches.open(STATIC_CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      });
    })
  );
});
