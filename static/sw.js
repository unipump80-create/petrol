// Service worker: офлайн-оболочка + кэш данных.
// __VERSION__ подставляет сервер (git-хеш деплоя) — бампать руками не нужно.
const VERSION = '__VERSION__';
const CACHE = 'petrol-' + VERSION;
const SHELL = [
  '/',
  '/static/icons/icon-192.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

self.addEventListener('install', e => {
  // НЕ вызываем skipWaiting автоматически — ждём команды от страницы,
  // чтобы показать пользователю баннер «доступно обновление».
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {}))
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Страница просит активировать новый SW немедленно.
self.addEventListener('message', e => {
  if (e.data === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  // данные API: сеть, при ошибке — кэш
  if (url.pathname.startsWith('/stations') || url.pathname.startsWith('/prices')) {
    e.respondWith(
      fetch(e.request)
        .then(r => { const c = r.clone(); caches.open(CACHE).then(ch => ch.put(e.request, c)); return r; })
        .catch(() => caches.match(e.request))
    );
    return;
  }
  // оболочка: кэш, при отсутствии — сеть
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
