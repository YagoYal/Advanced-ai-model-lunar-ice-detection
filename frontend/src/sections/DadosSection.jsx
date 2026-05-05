import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { useT } from "../i18n";

const SOURCES_META = [
  { name: "LROC WAC",    icon: "📸", color: "#38bdf8" },
  { name: "Diviner EPF", icon: "🌡️", color: "#818cf8" },
  { name: "Mini-RF CPR", icon: "📡", color: "#34d399" },
  { name: "LAMP UV",     icon: "☀️", color: "#fbbf24" },
];

const LABEL_DATA = [
  { name: "PSR", value: 43, color: "#38bdf8" },
  { name: "EPF", value: 34, color: "#818cf8" },
  { name: "CPR", value: 23, color: "#34d399" },
];

const PIPELINE_COLORS = ["#38bdf8", "#38bdf8", "#818cf8", "#818cf8", "#34d399"];

function DarkTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ backgroundColor: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", padding: "8px 12px", borderRadius: 8, fontSize: "0.85rem" }}>
      <p>{payload[0].name}: {payload[0].value}%</p>
    </div>
  );
}

export default function DadosSection() {
  const { t } = useT();
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });

  return (
    <section id="dados" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0", background: "rgba(15,23,42,0.45)" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <p style={{ color: "#fbbf24", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              {t.dados.label}
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0" }}>
              {t.dados.title}
            </h2>
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 18,
            marginBottom: 56,
          }}>
            {SOURCES_META.map((src, i) => (
              <motion.div
                key={src.name}
                initial={{ opacity: 0, y: 20 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                style={{
                  padding: 24,
                  borderRadius: 14,
                  background: "rgba(15,23,42,0.9)",
                  border: `1px solid ${src.color}28`,
                }}
              >
                <div style={{ fontSize: "1.8rem", marginBottom: 12 }}>{src.icon}</div>
                <h3 style={{ color: src.color, fontWeight: 600, fontSize: "0.95rem", marginBottom: 10 }}>{src.name}</h3>
                <p style={{ color: "#64748b", fontSize: "0.83rem", lineHeight: 1.65 }}>{t.dados.sources[i].desc}</p>
              </motion.div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 28 }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.4 }}
              style={{ padding: 24, borderRadius: 14, background: "rgba(15,23,42,0.85)", border: "1px solid #1e293b" }}
            >
              <p style={{ color: "#94a3b8", fontWeight: 600, marginBottom: 20, fontSize: "0.88rem" }}>
                {t.dados.labelChartTitle}
              </p>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={LABEL_DATA} margin={{ top: 8, right: 12, left: -12, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip content={<DarkTooltip />} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]} name={t.dados.labelChartName}>
                      {LABEL_DATA.map(d => <Cell key={d.name} fill={d.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.5 }}
              style={{ padding: 24, borderRadius: 14, background: "rgba(15,23,42,0.85)", border: "1px solid #1e293b" }}
            >
              <p style={{ color: "#94a3b8", fontWeight: 600, marginBottom: 20, fontSize: "0.88rem" }}>
                {t.dados.pipelineTitle}
              </p>
              <svg viewBox="0 0 300 290" width="100%" role="img" aria-label={t.dados.pipelineAriaLabel}>
                <defs>
                  <marker id="arr-dados" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                    <path d="M0,1 L6,3.5 L0,6" fill="none" stroke="#334155" strokeWidth="1.2" />
                  </marker>
                </defs>
                {t.dados.pipeline.map((label, i) => {
                  const y = 28 + i * 58;
                  return (
                    <g key={i}>
                      <rect x={16} y={y - 18} width={268} height={36} rx={8}
                        fill={`${PIPELINE_COLORS[i]}16`} stroke={PIPELINE_COLORS[i]} strokeWidth={1.2} />
                      <text x={150} y={y + 5} textAnchor="middle" fill={PIPELINE_COLORS[i]} fontSize={11} fontWeight={500}>
                        {label}
                      </text>
                      {i < t.dados.pipeline.length - 1 && (
                        <line x1={150} y1={y + 18} x2={150} y2={y + 40}
                          stroke="#334155" strokeWidth={1.4} markerEnd="url(#arr-dados)" />
                      )}
                    </g>
                  );
                })}
              </svg>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
