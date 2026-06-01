import { useRef, useState, useCallback, useEffect } from "react";
import { motion, useInView } from "framer-motion";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  MapContainer, TileLayer, useMapEvents, Marker, Popup,
} from "react-leaflet";
import { wsSimular, simular } from "../services/api";
import RoverPath from "../components/RoverPath";
import { useT } from "../i18n";

const CONVERGENCE = [
  { episode: 100, reward: 136, ice_max: 0.720 },
  { episode: 200, reward: 151, ice_max: 0.890 },
  { episode: 300, reward: 161, ice_max: 1.000 },
  { episode: 400, reward: 163, ice_max: 1.000 },
  { episode: 500, reward: 165, ice_max: 1.000 },
];

function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ backgroundColor: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", padding: "10px 14px", borderRadius: 8, fontSize: "0.84rem" }}>
      <p style={{ color: "#94a3b8", marginBottom: 6 }}>Ep. {label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.dataKey === "ice_max" ? Number(p.value).toFixed(3) : p.value}
        </p>
      ))}
    </div>
  );
}

// Converte graus Leaflet para índice de grade (mesmo critério de AnaliseSection)
function coordParaGrid(lat, lng) {
  const gridLat = Math.max(0, Math.min(179, Math.round(lat + 90)));
  const gridLon = Math.max(0, Math.min(359, Math.round(lng + 180)));
  return { gridLat, gridLon };
}

function probColor(prob) {
  if (prob > 0.8) return "#4ade80";
  if (prob > 0.5) return "#facc15";
  return "#f87171";
}

// Deve ser filho direto de MapContainer (regra crítica)
function ClickHandler({ onClick }) {
  useMapEvents({ click(e) { onClick(e.latlng); } });
  return null;
}

// Painel de animação WebSocket — componente separado para evitar re-renders do mapa
function RoverSimPanel() {
  const { t } = useT();

  const [ponto,      setPonto]      = useState(null);   // { lat, lng } em graus Leaflet
  const [caminho,    setCaminho]    = useState([]);      // passos acumulados
  const [simAtiva,   setSimAtiva]   = useState(false);  // WebSocket em curso
  const [passoAtual, setPassoAtual] = useState(0);
  const [totalPassos, setTotalPassos] = useState(null);
  const [erro,       setErro]       = useState(null);
  const [concluida,  setConcluida]  = useState(false);

  const cleanupRef = useRef(null);

  // Cancela WebSocket ao desmontar
  useEffect(() => () => { cleanupRef.current?.(); }, []);

  const handleSelect = useCallback((latlng) => {
    // Ignora cliques durante simulação ativa
    if (simAtiva) return;
    setPonto(latlng);
    setCaminho([]);
    setConcluida(false);
    setErro(null);
    setPassoAtual(0);
    setTotalPassos(null);
  }, [simAtiva]);

  const iniciarSimulacao = useCallback(() => {
    if (!ponto || simAtiva) return;

    const { gridLat, gridLon } = coordParaGrid(ponto.lat, ponto.lng);
    const PASSOS = 20;

    setCaminho([]);
    setErro(null);
    setConcluida(false);
    setPassoAtual(0);
    setTotalPassos(PASSOS);
    setSimAtiva(true);

    const onStep = (step) => {
      setCaminho(prev => [...prev, step]);
      setPassoAtual(prev => prev + 1);
    };

    const onDone = (total) => {
      setSimAtiva(false);
      setConcluida(true);
      setPassoAtual(total);
      cleanupRef.current = null;
    };

    const onError = async (err) => {
      console.warn("[wsSimular] erro, tentando fallback POST:", err.message);
      cleanupRef.current = null;

      // Fallback para POST /simular
      try {
        const data = await simular(gridLat, gridLon, PASSOS);
        setCaminho(data.caminho ?? []);
        setPassoAtual(data.caminho?.length ?? 0);
        setConcluida(true);
      } catch (fallbackErr) {
        setErro(fallbackErr.message ?? "Erro ao simular rover.");
      } finally {
        setSimAtiva(false);
      }
    };

    cleanupRef.current = wsSimular(gridLat, gridLon, PASSOS, onStep, onDone, onError);
  }, [ponto, simAtiva]);

  const cancelar = useCallback(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    setSimAtiva(false);
  }, []);

  const melhor = caminho.length > 0
    ? caminho.reduce((a, b) => (b.probabilidade_gelo ?? 0) > (a.probabilidade_gelo ?? 0) ? b : a, caminho[0])
    : null;

  return (
    <div style={{ marginTop: 52 }}>
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <p style={{ color: "#818cf8", fontSize: "0.8rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 8 }}>
          {t.rover.simPanel.liveDemo}
        </p>
        <h3 style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "clamp(1.1rem, 2.5vw, 1.5rem)", marginBottom: 10 }}>
          {t.rover.simPanel.title}
        </h3>
        <p style={{ color: "#64748b", fontSize: "0.87rem" }}>
          {simAtiva ? t.rover.simPanel.statusActive : t.rover.simPanel.statusIdle}
        </p>
      </div>

      {/* Plain div parent of MapContainer — regra crítica: NÃO motion.div */}
      <div style={{
        borderRadius: 16,
        overflow: "hidden",
        border: "1px solid rgba(129,140,248,0.2)",
        boxShadow: "0 0 0 1px rgba(255,255,255,0.03), 0 12px 32px rgba(0,0,0,0.6)",
        marginBottom: 20,
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
          {/* ClickHandler DEVE ser filho direto de MapContainer */}
          <ClickHandler onClick={handleSelect} />
          {ponto && (
            <Marker position={ponto}>
              <Popup>
                {t.rover.simPanel.startPopup}: {ponto.lat.toFixed(2)}° / {ponto.lng.toFixed(2)}°
              </Popup>
            </Marker>
          )}
          {caminho.length > 0 && <RoverPath caminho={caminho} />}
        </MapContainer>
      </div>

      {/* Controles */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 16 }}>
        <button
          onClick={iniciarSimulacao}
          disabled={!ponto || simAtiva}
          style={{
            padding: "10px 22px",
            borderRadius: 10,
            border: "none",
            cursor: (!ponto || simAtiva) ? "not-allowed" : "pointer",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            color: "white",
            fontWeight: 500,
            fontSize: "0.9rem",
            opacity: (!ponto || simAtiva) ? 0.55 : 1,
            transition: "opacity 0.2s, transform 0.2s",
          }}
          onMouseEnter={e => { if (ponto && !simAtiva) e.currentTarget.style.transform = "translateY(-2px)"; }}
          onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
        >
          {simAtiva ? t.rover.simPanel.btnSimulating : t.rover.simPanel.btnSimulate}
        </button>

        {simAtiva && (
          <button
            onClick={cancelar}
            style={{
              padding: "10px 18px",
              borderRadius: 10,
              border: "1px solid rgba(248,113,113,0.4)",
              cursor: "pointer",
              background: "rgba(248,113,113,0.08)",
              color: "#f87171",
              fontWeight: 500,
              fontSize: "0.9rem",
              transition: "opacity 0.2s",
            }}
          >
            {t.rover.simPanel.cancel}
          </button>
        )}

        {(simAtiva || concluida) && totalPassos !== null && (
          <span style={{ color: "#94a3b8", fontSize: "0.88rem" }}>
            {t.rover.simPanel.step} {passoAtual} / {totalPassos}
            {concluida && (
              <span style={{ color: "#34d399", marginLeft: 8 }}>— {t.rover.simPanel.complete}</span>
            )}
          </span>
        )}
      </div>

      {/* Barra de progresso */}
      {(simAtiva || concluida) && totalPassos !== null && (
        <div style={{
          height: 4,
          borderRadius: 2,
          background: "rgba(255,255,255,0.06)",
          marginBottom: 16,
          overflow: "hidden",
        }}>
          <div style={{
            height: "100%",
            width: `${Math.round((passoAtual / totalPassos) * 100)}%`,
            background: concluida ? "#34d399" : "linear-gradient(90deg, #6366f1, #818cf8)",
            transition: "width 0.3s ease",
          }} />
        </div>
      )}

      {erro && (
        <p style={{
          color: "#f87171",
          padding: "10px 16px",
          background: "rgba(248,113,113,0.08)",
          borderRadius: 10,
          border: "1px solid rgba(248,113,113,0.25)",
          fontSize: "0.87rem",
          marginBottom: 16,
        }}>
          {erro}
        </p>
      )}

      {concluida && caminho.length > 0 && (
        <div style={{
          padding: 22,
          borderRadius: 14,
          background: "rgba(15,23,42,0.85)",
          border: "1px solid rgba(255,255,255,0.07)",
        }}>
          <h4 style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.95rem", marginBottom: 10 }}>
            {t.analise.roverTitle}
          </h4>
          <p style={{ color: "#94a3b8", fontSize: "0.88rem", marginBottom: 8 }}>
            {caminho.length} {t.analise.stepsExecuted}
          </p>
          {melhor && melhor.probabilidade_gelo > 0 && (
            <p style={{ color: "#64748b", fontSize: "0.88rem" }}>
              {t.analise.bestPoint}{" "}
              <strong style={{ color: probColor(melhor.probabilidade_gelo) }}>
                {(melhor.probabilidade_gelo * 100).toFixed(1)}%
              </strong>{" "}
              {t.analise.inGrid} [{melhor.posicao[0]}, {melhor.posicao[1]}]
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function RoverSection() {
  const { t } = useT();
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });

  return (
    <section id="rover" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0", background: "rgba(15,23,42,0.45)" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <p style={{ color: "#818cf8", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              {t.rover.label}
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0" }}>
              {t.rover.title}
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 28, alignItems: "stretch" }}>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 }}
              style={{ display: "flex", flexDirection: "column", gap: 20 }}
            >
              <div style={{
                padding: 28,
                borderRadius: 14,
                background: "rgba(15,23,42,0.85)",
                border: "1px solid rgba(129,140,248,0.2)",
              }}>
                <h3 style={{ color: "#818cf8", fontWeight: 600, fontSize: "0.95rem", marginBottom: 18 }}>
                  {t.rover.mdpTitle}
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {t.rover.mdpItems.map(item => (
                    <div key={item.label} style={{ padding: "12px 14px", background: "rgba(0,0,0,0.2)", borderRadius: 8 }}>
                      <p style={{ color: "#94a3b8", fontWeight: 600, fontSize: "0.83rem", marginBottom: 4 }}>{item.label}</p>
                      <p style={{ color: "#64748b", fontSize: "0.8rem" }}>{item.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{
                padding: 24,
                borderRadius: 14,
                background: "rgba(15,23,42,0.85)",
                border: "1px solid rgba(56,189,248,0.18)",
              }}>
                <h3 style={{ color: "#38bdf8", fontWeight: 600, fontSize: "0.88rem", marginBottom: 12 }}>
                  {t.rover.dqnTitle}
                </h3>
                <p style={{ color: "#64748b", fontSize: "0.83rem", lineHeight: 1.7 }}>
                  {t.rover.dqnDesc}
                </p>
              </div>

              <div style={{
                padding: 24,
                borderRadius: 14,
                background: "rgba(15,23,42,0.85)",
                border: "1px solid rgba(52,211,153,0.18)",
              }}>
                <h3 style={{ color: "#34d399", fontWeight: 600, fontSize: "0.88rem", marginBottom: 16 }}>
                  {t.rover.rewardTitle}
                </h3>
                <code style={{
                  display: "block",
                  fontSize: "0.8rem",
                  color: "#e2e8f0",
                  fontFamily: "'Courier New', monospace",
                  background: "rgba(0,0,0,0.3)",
                  padding: "12px 14px",
                  borderRadius: 8,
                  marginBottom: 14,
                  lineHeight: 1.8,
                  overflowX: "auto",
                  whiteSpace: "pre",
                }}>
                  {t.rover.rewardCode}
                </code>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {t.rover.rewardTerms.map(({ term, def }) => (
                    <div key={term} style={{ display: "flex", gap: 8, fontSize: "0.78rem" }}>
                      <span style={{ color: "#34d399", fontFamily: "monospace", flexShrink: 0, minWidth: "min(130px, 30%)" }}>{term}</span>
                      <span style={{ color: "#64748b" }}>{def}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.3 }}
              style={{
                padding: 24,
                borderRadius: 14,
                background: "rgba(15,23,42,0.85)",
                border: "1px solid #1e293b",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <p style={{ color: "#94a3b8", fontWeight: 600, marginBottom: 20, fontSize: "0.88rem" }}>
                {t.rover.convergenceTitle}
              </p>
              <div style={{ flex: 1, minHeight: "clamp(220px, 40vh, 300px)" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={CONVERGENCE} margin={{ top: 8, right: 16, left: -10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="episode"
                      tick={{ fill: "#94a3b8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      label={{ value: t.rover.episodeLabel, position: "insideBottom", offset: -8, fill: "#64748b", fontSize: 11 }}
                    />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip content={<DarkTooltip />} />
                    <Legend wrapperStyle={{ color: "#94a3b8", fontSize: "0.82rem", paddingTop: 12 }} />
                    <Line
                      type="monotone"
                      dataKey="reward"
                      stroke="#38bdf8"
                      strokeWidth={2.5}
                      dot={{ fill: "#38bdf8", r: 4 }}
                      name={t.rover.rewardAvgLabel}
                    />
                    <Line
                      type="monotone"
                      dataKey="ice_max"
                      stroke="#34d399"
                      strokeWidth={2.5}
                      dot={{ fill: "#34d399", r: 4 }}
                      name="ice_max"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* Painel de simulação WebSocket — fora do motion.div para respeitar a regra do MapContainer */}
        <RoverSimPanel />
      </div>
    </section>
  );
}
