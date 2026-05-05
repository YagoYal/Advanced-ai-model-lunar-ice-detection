import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
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
      </div>
    </section>
  );
}
