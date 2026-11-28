/* litfass service worker: instant app shell, fresh data. */
const VERSION = 'litfass-v1';
const SHELL = ['/', '/manage', '/login', '/icon.png', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(VERSION)
			.then((cache) => cache.addAll(SHELL))
			.then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
			.then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	const request = event.request;
	if (request.method !== 'GET') return;
	const url = new URL(request.url);
	if (url.origin !== self.location.origin) return;
	// Feeds, events, statistics and payments must always hit the server
	if (url.pathname.startsWith('/litfass/')) return;

	if (url.pathname.startsWith('/_app/immutable/')) {
		event.respondWith(cacheFirst(request));
	} else if (request.mode === 'navigate') {
		event.respondWith(networkFirst(request));
	} else {
		event.respondWith(staleWhileRevalidate(request));
	}
});

async function cacheFirst(request) {
	const cached = await caches.match(request);
	if (cached) return cached;
	const response = await fetch(request);
	if (response.ok) {
		const cache = await caches.open(VERSION);
		cache.put(request, response.clone());
	}
	return response;
}

async function networkFirst(request) {
	try {
		const response = await fetch(request);
		if (response.ok) {
			const cache = await caches.open(VERSION);
			cache.put(request, response.clone());
		}
		return response;
	} catch {
		return (await caches.match(request)) || (await caches.match('/')) || Response.error();
	}
}

async function staleWhileRevalidate(request) {
	const cached = await caches.match(request);
	const network = fetch(request)
		.then((response) => {
			if (response.ok) caches.open(VERSION).then((cache) => cache.put(request, response.clone()));
			return response;
		})
		.catch(() => cached || Response.error());
	return cached || network;
}
