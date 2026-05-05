import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { useT } from "../i18n";

const CARD_META = [
  { stage: "01", color: "#38bdf8" },
  { stage: "02", color: "#818cf8" },
  { stage: "03", color: "#34d399" },
];

const CONTEXT_COLORS = ["#38bdf8", "#818cf8", "#34d399"];

export default function SobreSection() {
  const { t } = useT();
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });

  return (
    <section id="sobre" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <p style={{ color: "#38bdf8", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              {t.sobre.label}
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0", marginBottom: 16 }}>
              {t.sobre.title}
            </h2>
            <p style={{ color: "#64748b", maxWidth: 600, margin: "0 auto", lineHeight: 1.75, fontSize: "0.97rem" }}>
              {t.sobre.desc}
            </p>
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
            marginBottom: 40,
          }}>
            {t.sobre.cards.map((card, i) => (
              <motion.div
                key={CARD_META[i].stage}
                initial={{ opacity: 0, y: 30 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                style={{
                  padding: 32,
                  borderRadius: 16,
                  background: "rgba(15,23,42,0.85)",
                  border: `1px solid ${CARD_META[i].color}30`,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <div style={{
                  position: "absolute", top: 0, left: 0, right: 0, height: 3,
                  background: `linear-gradient(90deg, ${CARD_META[i].color}, transparent)`,
                }} />
                <div style={{
                  fontSize: "2.5rem", fontWeight: 800, color: CARD_META[i].color,
                  opacity: 0.25, lineHeight: 1, marginBottom: 14,
                }}>
                  {CARD_META[i].stage}
                </div>
                <h3 style={{ color: "#e2e8f0", fontSize: "1.15rem", fontWeight: 600, marginBottom: 12 }}>
                  {card.title}
                </h3>
                <p style={{ color: "#64748b", lineHeight: 1.65, fontSize: "0.88rem" }}>
                  {card.desc}
                </p>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.5 }}
            style={{
              padding: "28px 32px",
              borderRadius: 16,
              background: "rgba(56,189,248,0.04)",
              border: "1px solid rgba(56,189,248,0.13)",
              display: "flex",
              gap: 32,
              flexWrap: "wrap",
            }}
          >
            {t.sobre.context.map((c, i) => (
              <div key={c.label} style={{ flex: "1 1 200px" }}>
                <p style={{ color: CONTEXT_COLORS[i], fontWeight: 600, marginBottom: 8, fontSize: "0.9rem" }}>{c.label}</p>
                <p style={{ color: "#64748b", fontSize: "0.85rem", lineHeight: 1.65 }}>{c.desc}</p>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
