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

// Fetch event - no caching, always use network
self.addEventListener('fetch', function(event) {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip non-HTTP(S) requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  // Always fetch from network, no caching
  event.respondWith(fetch(event.request));
});
