/// <reference lib="webworker" />
import { CacheableResponsePlugin } from 'workbox-cacheable-response'
import { ExpirationPlugin } from 'workbox-expiration'
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute, setCatchHandler } from 'workbox-routing'
import { CacheFirst, NetworkOnly } from 'workbox-strategies'

declare let self: ServiceWorkerGlobalScope

self.skipWaiting()
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

registerRoute(
  ({ url }) => url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/'),
  new NetworkOnly(),
)

registerRoute(
  ({ request }) =>
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'worker' ||
    request.destination === 'font' ||
    request.destination === 'image',
  new CacheFirst({
    cacheName: 'homelab-static',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 80, maxAgeSeconds: 60 * 60 * 24 * 30 }),
    ],
  }),
)

registerRoute(
  new NavigationRoute(createHandlerBoundToURL('/index.html'), {
    denylist: [/^\/api\//, /^\/health$/, /^\/ws\//, /^\/docs/, /^\/redoc/, /^\/offline\.html$/],
  }),
)

setCatchHandler(async ({ request }) => {
  if (request.destination === 'document') {
    const offline = await caches.match('/offline.html', { ignoreSearch: true })
    if (offline) {
      return offline
    }
  }
  return Response.error()
})
