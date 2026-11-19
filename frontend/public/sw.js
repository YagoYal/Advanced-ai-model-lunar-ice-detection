// v2: só cacheia arquivos do próprio site. A v1 fazia cache-first de tudo
// (inclusive cada tile da NASA visitado) com um nome de cache fixo, então o
// cache crescia sem limite. Trocar o nome apaga o cache antigo na ativação.
const CACHE = "lunar-ice-v2";
const PRECACHE = ["/", "/index.html"];
// Cada deploy gera assets com hash novo; mantém só as entradas mais recentes
// para os arquivos de deploys antigos não se acumularem.
const MAX_ENTRIES = 40;

async function guardar(req, res) {
  const cache = await caches.open(CACHE);
  await cache.put(req, res);
  const keys = await cache.keys();
  const excesso = keys.length - MAX_ENTRIES;
  for (let i = 0; i < excesso; i++) {
    const k = keys[i];
    if (!PRECACHE.includes(new URL(k.url).pathname)) await cache.delete(k);
  }
}

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // Outra origem (API no Fly, tiles da NASA) ou método que não seja GET:
  // não intercepta; o navegador busca direto na rede.
  if (req.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // Navegação: rede primeiro; offline, cai no index.html em cache.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).catch(() => caches.match("/index.html"))
    );
    return;
  }

  // Assets com hash no nome (/assets/index-abc123.js): imutáveis, cache-first.
  if (url.pathname.startsWith("/assets/")) {
    e.respondWith(
      caches.match(req).then((cached) =>
        cached ||
        fetch(req).then((res) => {
          if (res.ok) e.waitUntil(guardar(req, res.clone()));
          return res;
        })
      )
    );
  }
  // Demais arquivos do site: rede, sem cache do service worker.
});
