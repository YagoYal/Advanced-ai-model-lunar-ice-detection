import { useState, useEffect, useRef, useCallback } from "react";
import { motion, useInView } from "framer-motion";
import {
  MapContainer, TileLayer, useMapEvents, useMap, Marker, Popup,
} from "react-leaflet";
import { analisar, simular } from "../services/api";
import RoverPath from "../components/RoverPath";

function coordParaGrid(lat, lng) {
  const gridLat = Math.max(0, Math.min(179, Math.round(lat + 90)));
  const gridLon = Math.max(0, Math.min(359, Math.round(lng + 180)));
  return { gridLat, gridLon };
}

function ClickHandler({ onClick }) {
  useMapEvents({ click(e) { onClick(e.latlng); } });
  return null;
}

function MapResizer({ shouldResize }) {
  const map = useMap();
  useEffect(() => {
    if (shouldResize) {
      const t = setTimeout(() => map.invalidateSize(), 120);
      return () => clearTimeout(t);
    }
  }, [shouldResize, map]);
  return null;
}

function probColor(prob) {
  if (prob > 0.8) return "#4ade80";
  if (prob > 0.5) return "#facc15";
  return "#f87171";
}

export default function AnaliseSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });
  const [animDone, setAnimDone] = useState(false);

  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [loadingRL, setLoadingRL] = useState(false);
  const [ponto,     setPonto]     = useState(null);
  const [historico, setHistorico] = useState([]);
  const [erro,      setErro]      = useState(null);
  const [caminho,   setCaminho]   = useState(null);

  const abortRef = useRef(null);

  useEffect(() => {
    if (inView && !animDone) {
      const t = setTimeout(() => setAnimDone(true), 800);
      return () => clearTimeout(t);
    }
  }, [inView, animDone]);

  const handleAnalisar = useCallback(async (lat, lng) => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    setLoading(true);
    setErro(null);
    const { gridLat, gridLon } = coordParaGrid(lat, lng);
    try {
      const data = await analisar(gridLat, gridLon, signal);
      if (signal.aborted) return;
      setResult(data);
      setHistorico(prev => [...prev, { lat: lat.toFixed(2), lon: lng.toFixed(2), prob: data.probabilidade_gelo }]);
    } catch (err) {
      if (err.name === "AbortError") return;
      setErro(err.message ?? "Falha ao conectar com o backend.");
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, []);

  const handleSimularRover = async () => {
    if (!ponto) return;
    setLoadingRL(true);
    setErro(null);
    const { gridLat, gridLon } = coordParaGrid(ponto.lat, ponto.lng);
    try {
      const data = await simular(gridLat, gridLon, 20);
      setCaminho(data.caminho);
    } catch (err) {
      setErro(err.message ?? "Falha ao simular rover.");
    } finally {
      setLoadingRL(false);
    }
  };

  const handleSelect = (coord) => {
    setPonto(coord);
    setCaminho(null);
    handleAnalisar(coord.lat, coord.lng);
  };

  return (
    <section id="analise" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        {/* motion.div wraps content; MapContainer is child of a plain div — not direct child of motion.div */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          onAnimationComplete={() => setAnimDone(true)}
          style={{ isolation: "auto" }}
        >
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <p style={{ color: "#38bdf8", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              Interativo
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0", marginBottom: 14 }}>
              Análise ao Vivo
            </h2>
            <p style={{ color: "#64748b", fontSize: "0.97rem" }}>
              Clique na superfície lunar para analisar a probabilidade de gelo
            </p>
          </div>

          {/* Plain div parent of MapContainer */}
          <div style={{
            borderRadius: 16,
            overflow: "hidden",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 0 0 1px rgba(255,255,255,0.03), 0 12px 32px rgba(0,0,0,0.6)",
            marginBottom: 24,
          }}>
            <MapContainer
              center={[0, 0]}
              zoom={2}
              className="lunar-map"
            >
              <TileLayer
                url="https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg"
                attribution="NASA Trek / LRO WAC"
                minZoom={1}
                maxZoom={7}
              />
              <MapResizer shouldResize={animDone} />
              <ClickHandler onClick={handleSelect} />
              {ponto && (
                <Marker position={ponto}>
                  <Popup>
                    Lat: {ponto.lat.toFixed(2)}°<br />
                    Lon: {ponto.lng.toFixed(2)}°
                  </Popup>
                </Marker>
              )}
              {caminho && <RoverPath caminho={caminho} />}
            </MapContainer>
          </div>

          {/* Status messages */}
          {(loading || loadingRL || erro) && (
            <div style={{ marginBottom: 20, textAlign: "center" }}>
              {loading && (
                <p style={{ color: "#7dd3fc", fontSize: "0.9rem", animation: "pulse 1.5s infinite" }}>
                  Analisando dados...
                </p>
              )}
              {loadingRL && (
                <p style={{ color: "#7dd3fc", fontSize: "0.9rem", animation: "pulse 1.5s infinite" }}>
                  Simulando rover...
                </p>
              )}
              {erro && (
                <p style={{
                  color: "#f87171",
                  padding: "12px 20px",
                  background: "rgba(248,113,113,0.08)",
                  borderRadius: 10,
                  border: "1px solid rgba(248,113,113,0.25)",
                  display: "inline-block",
                }}>
                  {erro}
                </p>
              )}
            </div>
          )}

          {/* Result card */}
          {result && (
            <div style={{
              padding: 28,
              borderRadius: 16,
              background: "rgba(15,23,42,0.9)",
              border: result.probabilidade_gelo > 0.7
                ? "1px solid rgba(125,211,252,0.38)"
                : "1px solid rgba(255,255,255,0.08)",
              boxShadow: result.probabilidade_gelo > 0.7
                ? "0 0 22px rgba(125,211,252,0.12)"
                : "none",
              marginBottom: 20,
            }}>
              <h3 style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "1.05rem", marginBottom: 22 }}>
                Resultado da Análise
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 18 }}>
                <div>
                  <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>Probabilidade de Gelo</p>
                  <p style={{ fontSize: "2rem", fontWeight: 700, color: probColor(result.probabilidade_gelo), lineHeight: 1 }}>
                    {(result.probabilidade_gelo * 100).toFixed(2)}%
                  </p>
                </div>

                {result.confianca != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>Confiança</p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>{result.confianca}</p>
                    {result.variancia != null && (
                      <p style={{ color: "#64748b", fontSize: "0.78rem" }}>var = {result.variancia.toFixed(4)}</p>
                    )}
                  </div>
                )}

                {result.temperatura != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>Temp. Superfície</p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>{result.temperatura.toFixed(2)} K</p>
                  </div>
                )}

                {result.insolacao != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>Insolação (média)</p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>{result.insolacao.toFixed(1)} W/m²</p>
                    {result.insolacao_atual != null && (
                      <p style={{ color: "#64748b", fontSize: "0.78rem" }}>
                        atual: {result.insolacao_atual.toFixed(1)} W/m²
                        {result.fase_lunar != null && ` · fase=${result.fase_lunar.toFixed(2)}`}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {result.temperatura_subsolo != null && (
                <div style={{ marginTop: 18, padding: "12px 16px", background: "rgba(0,0,0,0.22)", borderRadius: 10 }}>
                  <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 10 }}>Temperatura Subsolo (MC Dropout)</p>
                  <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
                    {result.temperatura_subsolo.map((t, i) => (
                      <div key={i}>
                        <span style={{ color: "#64748b", fontSize: "0.8rem" }}>{["0.1m", "0.5m", "1.0m"][i]}: </span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{t.toFixed(1)} K</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={handleSimularRover}
                disabled={loadingRL}
                style={{
                  marginTop: 22,
                  padding: "10px 22px",
                  borderRadius: 10,
                  border: "none",
                  cursor: loadingRL ? "not-allowed" : "pointer",
                  background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                  color: "white",
                  fontWeight: 500,
                  fontSize: "0.9rem",
                  opacity: loadingRL ? 0.6 : 1,
                  transition: "opacity 0.2s, transform 0.2s",
                }}
                onMouseEnter={e => { if (!loadingRL) e.currentTarget.style.transform = "translateY(-2px)"; }}
                onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
              >
                {loadingRL ? "Simulando..." : "Simular Rover (20 passos)"}
              </button>
            </div>
          )}

          {/* Rover path summary */}
          {caminho && (
            <div style={{
              padding: 22,
              borderRadius: 14,
              background: "rgba(15,23,42,0.85)",
              border: "1px solid rgba(255,255,255,0.07)",
              marginBottom: 20,
            }}>
              <h3 style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.97rem", marginBottom: 10 }}>
                Trajetória do Rover
              </h3>
              <p style={{ color: "#94a3b8", fontSize: "0.88rem", marginBottom: 8 }}>
                {caminho.length} passos executados
              </p>
              {(() => {
                const melhor = caminho.reduce((a, b) =>
                  (b.probabilidade_gelo ?? 0) > (a.probabilidade_gelo ?? 0) ? b : a, caminho[0]);
                return melhor.probabilidade_gelo > 0 ? (
                  <p style={{ color: "#64748b", fontSize: "0.88rem" }}>
                    Melhor ponto:{" "}
                    <strong style={{ color: probColor(melhor.probabilidade_gelo) }}>
                      {(melhor.probabilidade_gelo * 100).toFixed(1)}%
                    </strong>{" "}
                    em grid [{melhor.posicao[0]}, {melhor.posicao[1]}]
                  </p>
                ) : null;
              })()}
            </div>
          )}

          {/* History */}
          {historico.length > 0 && (
            <div style={{
              padding: "18px 22px",
              borderRadius: 14,
              background: "rgba(15,23,42,0.8)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}>
              <h3 style={{ color: "#64748b", fontWeight: 600, fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 12 }}>
                Pontos Analisados
              </h3>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                {historico.map((p, i) => (
                  <li key={`${p.lat}-${p.lon}-${i}`} style={{ color: "#64748b", fontSize: "0.85rem" }}>
                    ({p.lat}, {p.lon}) →{" "}
                    <span style={{ color: probColor(p.prob), fontWeight: 600 }}>
                      {(p.prob * 100).toFixed(1)}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}
