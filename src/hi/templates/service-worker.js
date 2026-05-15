{% load static %}

var CACHE_VERSION = 1;
var OFFLINE_CACHE_NAME = 'offline-cache-' + CACHE_VERSION;
var STATIC_CACHE_NAME = 'static-cache-' + CACHE_VERSION;

// Assets to cache for offline use
var STATIC_ASSETS = [
  '/',
  '{% static "css/main.css" %}',
  '{% static "css/icons.css" %}',
  '{% static "css/attribute.css" %}',
  '{% static "js/jquery-3.7.0.min.js" %}',
  '{% static "js/antinode.js" %}',
  '{% static "js/main.js" %}',
  '{% static "bootstrap/css/bootstrap.css" %}',
  '{% static "bootstrap/js/bootstrap.js" %}',
  '{% static "img/hi-icon-128x128.png" %}',
  '{% static "img/hi-icon-196x196.png" %}',
  '{% static "img/hi-icon-512x512.png" %}',
  '{% static "favicon.png" %}'
];

// Install event - cache static assets
self.addEventListener('install', function(event) {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(function() {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== STATIC_CACHE_NAME && cacheName !== OFFLINE_CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      console.log('Service Worker: Activation complete');
      return self.clients.claim();
    })
  );
});

// Lookup set built from STATIC_ASSETS at install/parse time. The
// fetch handler below uses this to decide whether to intercept a
// request; anything not in this set bypasses the service worker
// entirely.
var STATIC_ASSET_PATHS = new Set(STATIC_ASSETS);

// Fetch event - scoped to pre-cached static assets only.
//
// MJPEG streams (multipart/x-mixed-replace) and other long-lived or
// dynamic responses are NOT routed through ``event.respondWith``.
// Browsers vary in how they proxy multipart responses through a
// service worker, and Firefox in particular fails on multiple
// concurrent multipart streams routed through a ``fetch`` inside
// respondWith. Letting non-static requests pass through unmodified
// keeps streams, the polling endpoint, and dynamic pages on the
// browser's native fetch path.
self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') {
    return;
  }
  if (!event.request.url.startsWith('http')) {
    return;
  }
  var pathname = new URL(event.request.url).pathname;
  if (!STATIC_ASSET_PATHS.has(pathname)) {
    return;
  }
  // Cache-first for pre-cached static assets; network on miss.
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      return cached || fetch(event.request);
    })
  );
});
