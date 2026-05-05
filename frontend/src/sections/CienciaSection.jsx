import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { useT } from "../i18n";

const FORMULA_META = [
  { formula: "T = (S · (1−α) · cos(θ) / εσ)^0.25",      color: "#38bdf8" },
  { formula: "z_skin = √(κ · P / π)  =  0.62 m",         color: "#38bdf8" },
  { formula: "T(z) = T̄ + (Tsup − T̄) · exp(−z / z_skin)", color: "#818cf8" },
  { formula: "E(lat, t) = 1361 · max(0, cos(lat) · cos(2πt))   [W/m²]", color: "#818cf8" },
  { formula: "(μ, σ²) = f(x, N=30 passes)",               color: "#34d399" },
];

const METRIC_VALUES = [
  { value: "0.997",  color: "#38bdf8" },
  { value: "0.0101", color: "#818cf8" },
  { value: "1.000",  color: "#34d399" },
  { value: "6/6",    color: "#38bdf8" },
  { value: "58.624", color: "#818cf8" },
  { value: "14.656", color: "#34d399" },
  { value: "6",      color: "#38bdf8" },
  { value: "~165",   color: "#818cf8" },
];

export default function CienciaSection() {
  const { t } = useT();
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
              {t.ciencia.label}
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0" }}>
              {t.ciencia.title}
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 64 }}>
            {t.ciencia.formulas.map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                style={{
                  padding: "24px 28px",
                  borderRadius: 14,
                  background: "rgba(15,23,42,0.85)",
                  border: `1px solid ${FORMULA_META[i].color}28`,
                  display: "flex",
                  gap: 20,
                  alignItems: "flex-start",
                }}
              >
                <div style={{ width: 4, minHeight: 64, background: FORMULA_META[i].color, borderRadius: 2, flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <p style={{ color: FORMULA_META[i].color, fontWeight: 700, fontSize: "0.82rem", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
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
                    {FORMULA_META[i].formula}
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
              {t.ciencia.metricsLabel}
            </p>
            <div className="metrics-grid" style={{ gap: 14 }}>
              {t.ciencia.metrics.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={inView ? { opacity: 1, scale: 1 } : {}}
                  transition={{ duration: 0.4, delay: 0.5 + i * 0.07 }}
                  style={{
                    padding: "20px 16px",
                    borderRadius: 12,
                    background: `${METRIC_VALUES[i].color}0e`,
                    border: `1px solid ${METRIC_VALUES[i].color}28`,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "clamp(1.4rem, 3vw, 1.7rem)", fontWeight: 700, color: METRIC_VALUES[i].color, marginBottom: 6 }}>
                    {METRIC_VALUES[i].value}
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
