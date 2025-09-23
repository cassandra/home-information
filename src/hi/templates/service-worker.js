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

// Fetch event - serve from cache when possible
self.addEventListener('fetch', function(event) {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip non-HTTP(S) requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Return cached version if available
        if (response) {
          return response;
        }

        // For HTML pages, try network first, fall back to cache
        if (event.request.headers.get('accept').includes('text/html')) {
          return fetch(event.request)
            .then(function(response) {
              // Clone the response for caching
              var responseToCache = response.clone();

              // Cache successful responses
              if (response.status === 200) {
                caches.open(OFFLINE_CACHE_NAME)
                  .then(function(cache) {
                    cache.put(event.request, responseToCache);
                  });
              }

              return response;
            })
            .catch(function() {
              // Network failed, try to serve from cache
              return caches.match('/')
                .then(function(response) {
                  return response || new Response('Offline - Please check your connection', {
                    status: 503,
                    statusText: 'Service Unavailable',
                    headers: new Headers({
                      'Content-Type': 'text/html'
                    })
                  });
                });
            });
        }

        // For other resources, try network first
        return fetch(event.request)
          .then(function(response) {
            // Clone the response for caching
            var responseToCache = response.clone();

            // Cache successful responses for static assets
            if (response.status === 200 &&
                (event.request.url.includes('/static/') ||
                 event.request.url.includes('.css') ||
                 event.request.url.includes('.js') ||
                 event.request.url.includes('.png') ||
                 event.request.url.includes('.ico'))) {
              caches.open(STATIC_CACHE_NAME)
                .then(function(cache) {
                  cache.put(event.request, responseToCache);
                });
            }

            return response;
          })
          .catch(function() {
            // Network failed for static asset, serve from cache if available
            return caches.match(event.request);
          });
      })
  );
});
