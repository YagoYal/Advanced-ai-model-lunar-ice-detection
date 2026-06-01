import { useState, useEffect, useRef, useCallback } from "react";
import { motion, useInView } from "framer-motion";
import {
  MapContainer, TileLayer, useMapEvents, useMap, Marker, Popup,
} from "react-leaflet";
import { analisar, simular } from "../services/api";
import RoverPath from "../components/RoverPath";
import { useT } from "../i18n";

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
  const { t } = useT();
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });
  const [animDone, setAnimDone] = useState(false);

  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [loadingRL, setLoadingRL] = useState(false);
  const [ponto,     setPonto]     = useState(null);
  const [historico, setHistorico] = useState([]);
  const [erro,      setErro]      = useState(null);
  const [caminho,    setCaminho]    = useState(null);
  const [depthLayer, setDepthLayer] = useState(0); // 0=surface, 1=0.1m, 2=0.5m, 3=1.0m
  const [polares, setPolares] = useState(null);
  const [loadingPolares, setLoadingPolares] = useState(false);

  const abortRef = useRef(null);

  useEffect(() => {
    if (inView && !animDone) {
      const timer = setTimeout(() => setAnimDone(true), 800);
      return () => clearTimeout(timer);
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
      setErro(err.message ?? t.analise.errorBackend);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [t]);

  const handleSimularRover = async () => {
    if (!ponto) return;
    setLoadingRL(true);
    setErro(null);
    const { gridLat, gridLon } = coordParaGrid(ponto.lat, ponto.lng);
    try {
      const data = await simular(gridLat, gridLon, 20);
      setCaminho(data.caminho);
    } catch (err) {
      setErro(err.message ?? t.analise.errorRover);
    } finally {
      setLoadingRL(false);
    }
  };

  const handleCompararPolos = async () => {
    setLoadingPolares(true);
    setPolares(null);
    try {
      const [norte, sul] = await Promise.all([
        analisar(Math.round(88 + 90), Math.round(33 + 180)),
        analisar(Math.round(-90 + 90), Math.round(0 + 180)),
      ]);
      setPolares({ norte, sul });
    } catch (err) {
      setErro(err.message ?? t.analise.errorBackend);
    } finally {
      setLoadingPolares(false);
    }
  };

  const handleSelect = (coord) => {
    setPonto(coord);
    setCaminho(null);
    setDepthLayer(0);
    handleAnalisar(coord.lat, coord.lng);
  };

  return (
    <section id="analise" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          onAnimationComplete={() => setAnimDone(true)}
          style={{ isolation: "auto" }}
        >
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <p style={{ color: "#38bdf8", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              {t.analise.label}
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0", marginBottom: 14 }}>
              {t.analise.title}
            </h2>
            <p style={{ color: "#64748b", fontSize: "0.97rem" }}>
              {t.analise.instruction}
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
              touchZoom={true}
              dragging={true}
              tap={true}
              scrollWheelZoom={false}
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

          {(loading || loadingRL || erro) && (
            <div style={{ marginBottom: 20, textAlign: "center" }}>
              {loading && (
                <p style={{ color: "#7dd3fc", fontSize: "0.9rem", animation: "pulse 1.5s infinite" }}>
                  {t.analise.loadingAnalysis}
                </p>
              )}
              {loadingRL && (
                <p style={{ color: "#7dd3fc", fontSize: "0.9rem", animation: "pulse 1.5s infinite" }}>
                  {t.analise.loadingRover}
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
                {t.analise.resultTitle}
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 18 }}>
                <div>
                  <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>{t.analise.iceProb}</p>
                  <p style={{ fontSize: "2rem", fontWeight: 700, color: probColor(result.probabilidade_gelo), lineHeight: 1 }}>
                    {(result.probabilidade_gelo * 100).toFixed(2)}%
                  </p>
                </div>

                {result.confianca != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>{t.analise.confidence}</p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>
                      {t.analise.confiancaMap[result.confianca] ?? result.confianca}
                    </p>
                    {result.variancia != null && (
                      <p style={{ color: "#64748b", fontSize: "0.78rem" }}>var = {result.variancia.toFixed(4)}</p>
                    )}
                  </div>
                )}

                {result.temperatura != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>
                      {depthLayer === 0 ? t.analise.tempSurface : `${t.analise.depthLayerLabel} — ${["0.1", "0.5", "1.0"][depthLayer - 1]} ${t.analise.depthUnit}`}
                    </p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>
                      {depthLayer === 0
                        ? `${result.temperatura.toFixed(2)} K`
                        : result.temperatura_subsolo != null
                          ? `${result.temperatura_subsolo[depthLayer - 1].toFixed(2)} K`
                          : "—"}
                    </p>
                  </div>
                )}

                {result.insolacao != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>{t.analise.insolation}</p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>{result.insolacao.toFixed(1)} W/m²</p>
                    {result.insolacao_atual != null && (
                      <p style={{ color: "#64748b", fontSize: "0.78rem" }}>
                        {t.analise.insolCurrent}: {result.insolacao_atual.toFixed(1)} W/m²
                        {result.fase_lunar != null && ` · ${t.analise.phase}=${result.fase_lunar.toFixed(2)}`}
                      </p>
                    )}
                  </div>
                )}

                {result.altitude_m != null && (
                  <div>
                    <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>{t.analise.altitude}</p>
                    <p style={{ color: "#e2e8f0", fontWeight: 600 }}>
                      {result.altitude_m >= 0 ? "+" : ""}{result.altitude_m.toFixed(0)} m
                    </p>
                  </div>
                )}
              </div>

              {(result.temperatura != null || result.temperatura_subsolo != null) && (
                <div style={{ marginTop: 18, padding: "12px 16px", background: "rgba(0,0,0,0.22)", borderRadius: 10 }}>
                  <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 10 }}>
                    {t.analise.depthLayerLabel}
                  </p>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
                    {[
                      { label: t.analise.depthSurface, idx: 0 },
                      { label: `0.1 ${t.analise.depthUnit}`, idx: 1 },
                      { label: `0.5 ${t.analise.depthUnit}`, idx: 2 },
                      { label: `1.0 ${t.analise.depthUnit}`, idx: 3 },
                    ].map(({ label, idx }) => {
                      const disabled = idx > 0 && result.temperatura_subsolo == null;
                      const active = depthLayer === idx;
                      return (
                        <button
                          key={idx}
                          onClick={() => !disabled && setDepthLayer(idx)}
                          disabled={disabled}
                          style={{
                            padding: "5px 14px",
                            borderRadius: 8,
                            border: active
                              ? "1px solid rgba(125,211,252,0.7)"
                              : "1px solid rgba(255,255,255,0.12)",
                            background: active
                              ? "rgba(125,211,252,0.15)"
                              : "rgba(255,255,255,0.04)",
                            color: disabled ? "#334155" : active ? "#7dd3fc" : "#94a3b8",
                            fontSize: "0.82rem",
                            fontWeight: active ? 600 : 400,
                            cursor: disabled ? "not-allowed" : "pointer",
                            transition: "background 0.15s, border 0.15s, color 0.15s",
                          }}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                  {result.temperatura_subsolo != null && (
                    <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                      {result.temperatura_subsolo.map((temp, i) => (
                        <div
                          key={i}
                          style={{
                            padding: "6px 12px",
                            borderRadius: 8,
                            background: depthLayer === i + 1
                              ? "rgba(125,211,252,0.1)"
                              : "transparent",
                            border: depthLayer === i + 1
                              ? "1px solid rgba(125,211,252,0.3)"
                              : "1px solid transparent",
                            transition: "background 0.15s, border 0.15s",
                          }}
                        >
                          <span style={{ color: "#64748b", fontSize: "0.78rem" }}>
                            {["0.1", "0.5", "1.0"][i]} {t.analise.depthUnit}:{" "}
                          </span>
                          <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{temp.toFixed(1)} K</span>
                        </div>
                      ))}
                    </div>
                  )}
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
                {loadingRL ? t.analise.btnSimulating : t.analise.btnSimulate}
              </button>
            </div>
          )}

          {caminho && (
            <div style={{
              padding: 22,
              borderRadius: 14,
              background: "rgba(15,23,42,0.85)",
              border: "1px solid rgba(255,255,255,0.07)",
              marginBottom: 20,
            }}>
              <h3 style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.97rem", marginBottom: 10 }}>
                {t.analise.roverTitle}
              </h3>
              <p style={{ color: "#94a3b8", fontSize: "0.88rem", marginBottom: 8 }}>
                {caminho.length} {t.analise.stepsExecuted}
              </p>
              {(() => {
                const melhor = caminho.reduce((a, b) =>
                  (b.probabilidade_gelo ?? 0) > (a.probabilidade_gelo ?? 0) ? b : a, caminho[0]);
                return melhor.probabilidade_gelo > 0 ? (
                  <p style={{ color: "#64748b", fontSize: "0.88rem" }}>
                    {t.analise.bestPoint}{" "}
                    <strong style={{ color: probColor(melhor.probabilidade_gelo) }}>
                      {(melhor.probabilidade_gelo * 100).toFixed(1)}%
                    </strong>{" "}
                    {t.analise.inGrid} [{melhor.posicao[0]}, {melhor.posicao[1]}]
                  </p>
                ) : null;
              })()}
            </div>
          )}

          {historico.length > 0 && (
            <div style={{
              padding: "18px 22px",
              borderRadius: 14,
              background: "rgba(15,23,42,0.8)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}>
              <h3 style={{ color: "#64748b", fontWeight: 600, fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 12 }}>
                {t.analise.pointsTitle}
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
          <div style={{ marginTop: 32, padding: "24px 28px", borderRadius: 16, background: "rgba(15,23,42,0.85)", border: "1px solid rgba(255,255,255,0.07)" }}>
            <p style={{ color: "#38bdf8", fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 8 }}>
              {t.analise.compareLabel}
            </p>
            <h3 style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "1rem", marginBottom: 6 }}>
              {t.analise.compareTitle}
            </h3>
            <p style={{ color: "#64748b", fontSize: "0.82rem", marginBottom: 18 }}>
              {t.analise.compareSubtitle}
            </p>

            <button
              onClick={handleCompararPolos}
              disabled={loadingPolares}
              style={{
                padding: "9px 20px",
                borderRadius: 10,
                border: "1px solid rgba(56,189,248,0.35)",
                cursor: loadingPolares ? "not-allowed" : "pointer",
                background: "rgba(56,189,248,0.08)",
                color: "#38bdf8",
                fontWeight: 500,
                fontSize: "0.88rem",
                opacity: loadingPolares ? 0.6 : 1,
                transition: "opacity 0.2s, transform 0.2s",
                marginBottom: polares ? 24 : 0,
              }}
              onMouseEnter={e => { if (!loadingPolares) e.currentTarget.style.transform = "translateY(-2px)"; }}
              onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
            >
              {loadingPolares ? t.analise.compareBtnLoading : t.analise.compareBtn}
            </button>

            {polares && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
                {[
                  { label: t.analise.compareNorth, data: polares.norte, color: "#818cf8", loc: "Peary (88.6°N, 33°E)" },
                  { label: t.analise.compareSouth, data: polares.sul,   color: "#34d399", loc: "Shackleton (90°S, 0°)" },
                ].map(({ label, data, color, loc }) => (
                  <div key={label} style={{
                    padding: "18px 20px",
                    borderRadius: 12,
                    background: "rgba(0,0,0,0.25)",
                    border: `1px solid ${color}33`,
                  }}>
                    <p style={{ color, fontWeight: 700, fontSize: "0.88rem", marginBottom: 4 }}>{label}</p>
                    <p style={{ color: "#475569", fontSize: "0.75rem", marginBottom: 14 }}>{loc}</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      <div>
                        <p style={{ color: "#64748b", fontSize: "0.75rem", marginBottom: 3 }}>{t.analise.iceProb}</p>
                        <p style={{ fontSize: "1.6rem", fontWeight: 700, color: probColor(data.probabilidade_gelo), lineHeight: 1 }}>
                          {(data.probabilidade_gelo * 100).toFixed(1)}%
                        </p>
                      </div>
                      {data.temperatura != null && (
                        <div>
                          <p style={{ color: "#64748b", fontSize: "0.75rem", marginBottom: 3 }}>{t.analise.tempSurface}</p>
                          <p style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.92rem" }}>{data.temperatura.toFixed(1)} K</p>
                        </div>
                      )}
                      {data.insolacao != null && (
                        <div>
                          <p style={{ color: "#64748b", fontSize: "0.75rem", marginBottom: 3 }}>{t.analise.insolation}</p>
                          <p style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.92rem" }}>{data.insolacao.toFixed(1)} W/m²</p>
                        </div>
                      )}
                      {data.confianca != null && (
                        <div>
                          <p style={{ color: "#64748b", fontSize: "0.75rem", marginBottom: 3 }}>{t.analise.confidence}</p>
                          <p style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.92rem" }}>
                            {t.analise.confiancaMap[data.confianca] ?? data.confianca}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
