import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const FORMULAS = [
  {
    title: "Stefan-Boltzmann",
    formula: "T = (S · (1−α) · cos(θ) / εσ)^0.25",
    desc: "Temperatura radiativa de equilíbrio. S = 1361 W/m², α = 0.12, ε = 0.95, σ = 5.67×10⁻⁸ W/m²K⁴. cos(θ) = cos(lat)·cos(2πt) = projeção solar (ângulo de incidência). PSRs: cos(θ) ≈ 0 → T ≈ 35K.",
    color: "#38bdf8",
  },
  {
    title: "Comprimento de Pele Térmico — Vasavada 2012",
    formula: "z_skin = √(κ · P / π)  =  0.62 m",
    desc: "Profundidade característica de penetração da onda de calor lunar. κ = 4.7×10⁻⁷ m²/s (difusividade do regolito), P = 2.551×10⁶ s (período lunar ~29.5 dias).",
    color: "#38bdf8",
  },
  {
    title: "Difusão Térmica Subsuperficial — Vasavada 2012",
    formula: "T(z) = T̄ + (Tsup − T̄) · exp(−z / z_skin)",
    desc: "Solução analítica da difusão periódica. T̄ = max(Tsup × 0.8, 3K). Gelo estável quando T(z) < 110K (Paige 2010). z ∈ [0, 2m], 20 camadas discretas.",
    color: "#818cf8",
  },
  {
    title: "Insolação Dinâmica",
    formula: "E(lat, t) = 1361 · max(0, cos(lat) · cos(2πt))   [W/m²]",
    desc: "Irradiância instantânea em função da latitude e fase lunar t ∈ [0, 1]. PSRs recebem E ≈ 0 W/m² de forma permanente — condição necessária para preservação de gelo.",
    color: "#818cf8",
  },
  {
    title: "Monte Carlo Dropout — Gal & Ghahramani 2016",
    formula: "(μ, σ²) = f(x, N=30 passes)",
    desc: "Incerteza epistêmica via N passes com dropout ativo em inferência. μ = média das predições (probabilidade reportada), σ² = variância (campo variancia na API).",
    color: "#34d399",
  },
];

const METRICS = [
  { label: "F1 Score",       value: "0.997",  color: "#38bdf8" },
  { label: "Val Loss",       value: "0.0101", color: "#818cf8" },
  { label: "Recall",         value: "1.000",  color: "#34d399" },
  { label: "PSRs Validados", value: "6/6",    color: "#38bdf8" },
  { label: "Exemplos",       value: "58.624", color: "#818cf8" },
  { label: "Positivos",      value: "14.656", color: "#34d399" },
  { label: "obs_dim",        value: "6",      color: "#38bdf8" },
  { label: "Reward RL",      value: "~165",   color: "#818cf8" },
];

export default function CienciaSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });

  return (
    <section id="ciencia" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <p style={{ color: "#34d399", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              Física & IA
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0" }}>
              Base Científica
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 64 }}>
            {FORMULAS.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, x: -20 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                style={{
                  padding: "24px 28px",
                  borderRadius: 14,
                  background: "rgba(15,23,42,0.85)",
                  border: `1px solid ${f.color}28`,
                  display: "flex",
                  gap: 20,
                  alignItems: "flex-start",
                }}
              >
                <div style={{ width: 4, minHeight: 64, background: f.color, borderRadius: 2, flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <p style={{ color: f.color, fontWeight: 700, fontSize: "0.82rem", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
                    {f.title}
                  </p>
                  <code style={{
                    display: "block",
                    fontSize: "clamp(0.95rem, 2vw, 1.2rem)",
                    color: "#e2e8f0",
                    fontFamily: "'Courier New', monospace",
                    background: "rgba(0,0,0,0.35)",
                    padding: "10px 16px",
                    borderRadius: 8,
                    marginBottom: 12,
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}>
                    {f.formula}
                  </code>
                  <p style={{ color: "#64748b", fontSize: "0.87rem", lineHeight: 1.65 }}>{f.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <p style={{ color: "#64748b", fontSize: "0.8rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 20, textAlign: "center" }}>
              Métricas do Modelo
            </p>
            <div className="metrics-grid" style={{ gap: 14 }}>
              {METRICS.map((m, i) => (
                <motion.div
                  key={m.label}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={inView ? { opacity: 1, scale: 1 } : {}}
                  transition={{ duration: 0.4, delay: 0.5 + i * 0.07 }}
                  style={{
                    padding: "20px 16px",
                    borderRadius: 12,
                    background: `${m.color}0e`,
                    border: `1px solid ${m.color}28`,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "clamp(1.4rem, 3vw, 1.7rem)", fontWeight: 700, color: m.color, marginBottom: 6 }}>
                    {m.value}
                  </div>
                  <div style={{ fontSize: "0.76rem", color: "#64748b", fontWeight: 500 }}>
                    {m.label}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
