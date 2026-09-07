// Kumpas service worker - basic offline cache for static assets
var CACHE_NAME = 'kumpas-cache-v1';
var PRECACHE_URLS = [
  'css/style.css',
  'css/dashboard.css',
  'css/dashboard-pro.css',
  'css/pages.css',
  'css/quiz.css',
  'css/bg-orbs.css',
  'js/main.js',
  'js/theme.js',
  'js/auth.js',
  'js/portal.js',
  'images/kumpas_logo.png',
  'images/kumpas_logo1.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(PRECACHE_URLS);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (key) {
          return key !== CACHE_NAME;
        }).map(function (key) {
          return caches.delete(key);
        })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

// Cache-first for same-origin static assets (css/js/images/fonts).
// Everything else (HTML pages, API calls) goes to the network so
// logged-in/dynamic content is never served stale.
self.addEventListener('fetch', function (event) {
  var request = event.request;

  if (request.method !== 'GET') {
    return;
  }

  var url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  var isStaticAsset = /\.(?:css|js|png|jpg|jpeg|svg|gif|webp|woff2?)$/.test(url.pathname);
  if (!isStaticAsset) {
    return;
  }

  event.respondWith(
    caches.match(request).then(function (cached) {
      if (cached) {
        return cached;
      }
      return fetch(request).then(function (response) {
        if (response && response.ok) {
          var responseClone = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(request, responseClone);
          });
        }
        return response;
      });
    })
  );
});
