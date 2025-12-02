/* eslint-disable no-unused-vars */
const CACHE_NAME = 'rozhan-v1';

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
/* eslint-enable no-unused-vars */
