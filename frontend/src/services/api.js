const IS_DEV = import.meta.env.DEV;
const API_URL = import.meta.env.VITE_API_URL ||
  (IS_DEV ? "http://localhost:8000" : (() => { throw new Error("VITE_API_URL is not defined in production"); })());

if (!IS_DEV && API_URL.startsWith("http://")) {
  console.warn("[security] VITE_API_URL usa HTTP em produção — use HTTPS.");
}

const API_KEY = import.meta.env.VITE_API_KEY ?? "";
const authHeaders = API_KEY ? { "X-API-Key": API_KEY } : {};

export async function analisar(lat, lon, signal) {
  const res = await fetch(`${API_URL}/analisar`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
    body: JSON.stringify({ lat, lon }),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP error ${res.status}`);
  }
  return res.json();
}

export async function simular(lat, lon, passos = 10) {
  const res = await fetch(`${API_URL}/simular`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
    body: JSON.stringify({ lat, lon, passos }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP error ${res.status}`);
  }
  return res.json();
}

/**
 * Conecta ao endpoint WebSocket /ws/simular e transmite os passos do rover em tempo real.
 *
 * @param {number} lat    - Latitude em índice de grade (0-179)
 * @param {number} lon    - Longitude em índice de grade (0-359)
 * @param {number} passos - Número de passos
 * @param {(step: object) => void} onStep  - Chamado a cada passo recebido
 * @param {(total: number) => void} onDone  - Chamado ao fim ({done: true})
 * @param {(err: Error) => void}   onError - Chamado em erro de conexão
 * @returns {() => void} Função de cleanup que fecha o WebSocket
 */
export function wsSimular(lat, lon, passos, onStep, onDone, onError) {
  // Deriva URL WebSocket a partir da URL HTTP da API
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
    // Fecha anormal sem ter recebido {done:true} → reporta erro para fallback
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
