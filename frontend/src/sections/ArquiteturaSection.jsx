import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const LAYERS = [
  { name: "NASA Data",  tech: "LROC WAC · Diviner EPF · Mini-RF CPR · LAMP UV",           color: "#38bdf8" },
  { name: "Pipeline",   tech: "NumPy · Rasterio · Astropy · dataset.py",                   color: "#38bdf8" },
  { name: "CNN+Physics",tech: "PyTorch · LunarCNN · Vasavada 2012 · MC Dropout",           color: "#818cf8" },
  { name: "Backend",    tech: "FastAPI · Uvicorn · Slowapi · Pydantic",                     color: "#818cf8" },
  { name: "Frontend",   tech: "React · Vite · Leaflet · Recharts · Framer Motion",         color: "#34d399" },
  { name: "Rover RL",   tech: "DQN · Double Q-learning · obs_dim=6 · reward~165",          color: "#34d399" },
];

export default function ArquiteturaSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });

  const BOX_W = 128;
  const BOX_H = 54;
  const GAP   = 22;
  const totalW = LAYERS.length * BOX_W + (LAYERS.length - 1) * GAP;

  return (
    <section id="arquitetura" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0", background: "rgba(15,23,42,0.45)" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <p style={{ color: "#818cf8", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              Sistema
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0" }}>
              Arquitetura
            </h2>
          </div>

          {/* Flow diagram */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={inView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
            style={{ overflowX: "auto", marginBottom: 48 }}
          >
            <svg
              viewBox={`0 0 ${totalW + 40} 80`}
              width="100%"
              style={{ minWidth: "min(520px, 100%)", display: "block" }}
              role="img"
              aria-label="Diagrama de fluxo da arquitetura"
            >
              <defs>
                <marker id="arr-arch" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                  <path d="M0,1 L6,3.5 L0,6" fill="none" stroke="#334155" strokeWidth="1.2" />
                </marker>
              </defs>
              {LAYERS.map((layer, i) => {
                const x = 20 + i * (BOX_W + GAP);
                const cy = 40;
                return (
                  <g key={layer.name}>
                    <rect
                      x={x} y={cy - BOX_H / 2}
                      width={BOX_W} height={BOX_H}
                      rx={9}
                      fill={`${layer.color}18`}
                      stroke={layer.color}
                      strokeWidth={1.4}
                    />
                    <text x={x + BOX_W / 2} y={cy - 5} textAnchor="middle" fill={layer.color} fontSize={11} fontWeight={600}>
                      {layer.name}
                    </text>
                    <text x={x + BOX_W / 2} y={cy + 12} textAnchor="middle" fill="#64748b" fontSize={8.5}>
                      {["Dados", "Pipeline", "Modelo", "API", "UI", "RL"][i]}
                    </text>
                    {i < LAYERS.length - 1 && (
                      <line
                        x1={x + BOX_W + 2} y1={cy}
                        x2={x + BOX_W + GAP - 2} y2={cy}
                        stroke="#334155" strokeWidth={1.4}
                        markerEnd="url(#arr-arch)"
                      />
                    )}
                  </g>
                );
              })}
            </svg>
          </motion.div>

          {/* Stack cards */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 16,
          }}>
            {LAYERS.map((layer, i) => (
              <motion.div
                key={layer.name}
                initial={{ opacity: 0, y: 20 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: 0.3 + i * 0.08 }}
                style={{
                  padding: 20,
                  borderRadius: 12,
                  background: "rgba(15,23,42,0.85)",
                  border: `1px solid ${layer.color}20`,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: layer.color, flexShrink: 0 }} />
                  <span style={{ color: layer.color, fontWeight: 600, fontSize: "0.88rem" }}>{layer.name}</span>
                </div>
                <p style={{ color: "#64748b", fontSize: "0.82rem", lineHeight: 1.6 }}>{layer.tech}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
