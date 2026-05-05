const IS_DEV = import.meta.env.DEV;
const API_URL = import.meta.env.VITE_API_URL ||
  (IS_DEV ? "http://localhost:8000" : (() => { throw new Error("VITE_API_URL não definida em produção"); })());

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
    throw new Error(err.detail ?? `Erro HTTP ${res.status}`);
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
    throw new Error(err.detail ?? `Erro HTTP ${res.status}`);
  }
  return res.json();
}

export async function analisarComMapa(lat, lon) {
  const res = await fetch(`${API_URL}/analisar_com_mapa`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
    body: JSON.stringify({ lat, lon }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Erro HTTP ${res.status}`);
  }
  return res.json();
}
