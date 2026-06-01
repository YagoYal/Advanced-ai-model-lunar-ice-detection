const IS_DEV = import.meta.env.DEV;
const API_URL = import.meta.env.VITE_API_URL ||
  (IS_DEV ? "http://localhost:8000" : (() => { throw new Error("VITE_API_URL is not defined in production"); })());

if (!IS_DEV && API_URL.startsWith("http://")) {
  console.warn("[security] VITE_API_URL usa HTTP em produção — use HTTPS.");
}

const API_KEY = import.meta.env.VITE_API_KEY ?? "";
const authHeaders = API_KEY ? { "X-API-Key": API_KEY } : {};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchWithRetry(url, options, onRetry, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    if (options.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    try {
      const res = await fetch(url, options);
      if ((res.status === 502 || res.status === 503 || res.status === 504) && attempt < maxRetries - 1) {
        onRetry?.(attempt + 1, maxRetries);
        await sleep(4000 * (attempt + 1));
        continue;
      }
      return res;
    } catch (err) {
      if (err.name === "AbortError") throw err;
      if (attempt < maxRetries - 1) {
        onRetry?.(attempt + 1, maxRetries);
        await sleep(4000 * (attempt + 1));
        continue;
      }
      throw err;
    }
  }
}

export async function analisar(lat, lon, signal, onRetry) {
  const res = await fetchWithRetry(
    `${API_URL}/analisar`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ lat, lon }),
      signal,
    },
    onRetry,
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP error ${res.status}`);
  }
  return res.json();
}

export async function simular(lat, lon, passos = 10, onRetry) {
  const res = await fetchWithRetry(
    `${API_URL}/simular`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ lat, lon, passos }),
    },
    onRetry,
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP error ${res.status}`);
  }
  return res.json();
}

// Grid polar: 3 latitudes × 4 longitudes × 2 polos = 24 pontos
const POLAR_GRID = (() => {
  const lats = [160, 170, 179, 20, 10, 0]; // 70N, 80N, 90N, 70S, 80S, 90S
  const lons = [90, 180, 270, 359];        // 90°W, 0°, 90°E, 180°E
  const pts = [];
  for (const lat of lats)
    for (const lon of lons)
      pts.push({ lat, lon });
  return pts;
})();

export async function fetchPolarGrid(onProgress) {
  const total = POLAR_GRID.length;
  const results = [];
  const BATCH = 4;
  for (let i = 0; i < total; i += BATCH) {
    const batch = POLAR_GRID.slice(i, i + BATCH);
    const settled = await Promise.allSettled(
      batch.map((p) =>
        analisar(p.lat, p.lon).then((d) => ({ lat: p.lat, lon: p.lon, ...d }))
      )
    );
    for (const r of settled)
      if (r.status === "fulfilled") results.push(r.value);
    onProgress?.(Math.min(i + BATCH, total), total);
    if (i + BATCH < total) await sleep(600);
  }
  return results;
}

/**
 * Conecta ao endpoint WebSocket /ws/simular e transmite os passos do rover em tempo real.
 */
export function wsSimular(lat, lon, passos, onStep, onDone, onError) {
  const httpBase = API_URL.replace(/\/$/, "");
  const wsBase   = httpBase.replace(/^http/, "ws");
  const wsUrl    = `${wsBase}/ws/simular`;

  let ws;
  let stepCount = 0;
  let doneReceived = false;

  try {
    ws = new WebSocket(wsUrl);
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
    return () => {};
  }

  ws.onopen = () => {
    ws.send(JSON.stringify({ lat, lon, passos }));
  };

  ws.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }

    if (data.done) {
      doneReceived = true;
      onDone(stepCount);
      ws.close(1000, "done");
    } else {
      stepCount += 1;
      onStep(data);
    }
  };

  ws.onerror = () => {
    onError(new Error("WebSocket connection failed"));
  };

  ws.onclose = (event) => {
    if (!doneReceived && event.code !== 1000 && event.code !== 1005) {
      onError(new Error(`WebSocket closed unexpectedly (code ${event.code})`));
    }
  };

  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close(1000, "cancelled");
    }
  };
}

export async function analisarComMapa(lat, lon) {
  const res = await fetch(`${API_URL}/analisar_com_mapa`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
    body: JSON.stringify({ lat, lon }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP error ${res.status}`);
  }
  return res.json();
}
