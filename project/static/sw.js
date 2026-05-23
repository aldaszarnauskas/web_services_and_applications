const CACHE = 'arll-v1'

// Files to cache for offline use
const ASSETS = [
    '/',
    '/static/style.css',
    '/static/background_image.png',
    '/static/manifest.json'
]

// Cache assets on install
self.addEventListener('install', e => {
    e.waitUntil(
        caches.open(CACHE).then(cache => cache.addAll(ASSETS))
    )
})

// Serve from cache when possible
self.addEventListener('fetch', e => {
    e.respondWith(
        caches.match(e.request).then(cached => cached || fetch(e.request))
    )
})