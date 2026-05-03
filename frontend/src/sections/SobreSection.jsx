import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const CARDS = [
  {
    stage: "01",
    title: "Protótipo",
    desc: "CNN + physics encoder treinada em dados sintéticos LRO. Validação em 6 PSRs conhecidos. Baseline científico estabelecido.",
    color: "#38bdf8",
  },
  {
    stage: "02",
    title: "Científico",
    desc: "Integração Diviner EPF (549k medições), Mini-RF CPR, LAMP UV. MC Dropout para incerteza epistêmica. DQN rover autônomo.",
    color: "#818cf8",
  },
  {
    stage: "03",
    title: "Missão Real",
    desc: "Pipeline de planejamento de trajetória para rover lunar. Inferência em tempo real. Interface de controle de missão.",
    color: "#34d399",
  },
];

const CONTEXT = [
  { label: "LRO / NASA", color: "#38bdf8", desc: "Lunar Reconnaissance Orbiter · Operacional desde 2009 · LROC WAC 303ppd · Diviner radiômetro termal" },
  { label: "PSRs Confirmados", color: "#818cf8", desc: "11 regiões confirmadas por múltiplos instrumentos (LCROSS, LAMP, Diviner, Mini-RF) · Gelo estável <110K" },
  { label: "Base Científica", color: "#34d399", desc: "Paige 2010 · Vasavada 2012 · Mazarico 2011 · z_skin = 0.62m · Grade 180×360 (1°/px)" },
];

export default function SobreSection() {
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
              Missão
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0", marginBottom: 16 }}>
              Sobre o Projeto
            </h2>
            <p style={{ color: "#64748b", maxWidth: 600, margin: "0 auto", lineHeight: 1.75, fontSize: "0.97rem" }}>
              Desenvolvido para detectar e mapear depósitos de gelo em regiões permanentemente sombreadas (PSRs) lunares,
              combinando instrumentos LRO da NASA com modelos físicos de condução térmica subsuperficial.
            </p>
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
            marginBottom: 40,
          }}>
            {CARDS.map((card, i) => (
              <motion.div
                key={card.stage}
                initial={{ opacity: 0, y: 30 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                style={{
                  padding: 32,
                  borderRadius: 16,
                  background: "rgba(15,23,42,0.85)",
                  border: `1px solid ${card.color}30`,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <div style={{
                  position: "absolute", top: 0, left: 0, right: 0, height: 3,
                  background: `linear-gradient(90deg, ${card.color}, transparent)`,
                }} />
                <div style={{
                  fontSize: "2.5rem", fontWeight: 800, color: card.color,
                  opacity: 0.25, lineHeight: 1, marginBottom: 14,
                }}>
                  {card.stage}
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
            {CONTEXT.map(c => (
              <div key={c.label} style={{ flex: "1 1 200px" }}>
                <p style={{ color: c.color, fontWeight: 600, marginBottom: 8, fontSize: "0.9rem" }}>{c.label}</p>
                <p style={{ color: "#64748b", fontSize: "0.85rem", lineHeight: 1.65 }}>{c.desc}</p>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
