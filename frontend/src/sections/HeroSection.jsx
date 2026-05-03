import { motion } from "framer-motion";

const METRICS = [
  { label: "F1 Score", value: "0.997" },
  { label: "PSRs Validados", value: "6/6" },
  { label: "Val Loss", value: "0.0101" },
  { label: "Recall", value: "1.000" },
];

export default function HeroSection() {
  return (
    <section id="hero" style={{ scrollMarginTop: 70 }}>
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "88px clamp(16px, 4vw, 64px) 60px",
        background: "radial-gradient(ellipse at 50% 40%, rgba(56,189,248,0.07) 0%, transparent 65%)",
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "52px 52px",
          opacity: 0.12,
          pointerEvents: "none",
        }} />

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ position: "relative", zIndex: 1, maxWidth: 820 }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            style={{ marginBottom: 28 }}
          >
            <span style={{
              display: "inline-block",
              padding: "6px 18px",
              borderRadius: 100,
              background: "rgba(56,189,248,0.12)",
              border: "1px solid rgba(56,189,248,0.3)",
              color: "#38bdf8",
              fontSize: "0.83rem",
              fontWeight: 600,
              letterSpacing: 0.5,
            }}>
              CNN + Física Subsuperficial + Reinforcement Learning
            </span>
          </motion.div>

          <h1 style={{
            fontSize: "clamp(2.6rem, 7vw, 5.2rem)",
            fontWeight: 800,
            lineHeight: 1.08,
            marginBottom: 28,
            background: "linear-gradient(135deg, #e2e8f0 0%, #38bdf8 45%, #818cf8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>
            Lunar Ice<br />Intelligence
          </h1>

          <p style={{
            fontSize: "clamp(1rem, 2.2vw, 1.2rem)",
            color: "#94a3b8",
            maxWidth: 620,
            margin: "0 auto 44px",
            lineHeight: 1.75,
          }}>
            Detecção de gelo subsuperficial lunar via redes neurais com física integrada.
            LRO/NASA · Vasavada 2012 thermal model · DQN rover autonomy.
          </p>

          <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap" }}>
            <a
              href="#analise"
              style={{
                display: "inline-block",
                padding: "13px 32px",
                borderRadius: 12,
                background: "linear-gradient(135deg, #38bdf8, #818cf8)",
                color: "white",
                fontWeight: 600,
                fontSize: "0.97rem",
                textDecoration: "none",
                transition: "transform 0.2s, box-shadow 0.2s",
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 24px rgba(56,189,248,0.4)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}
            >
              Analisar Gelo
            </a>
            <a
              href="#ciencia"
              style={{
                display: "inline-block",
                padding: "13px 32px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.15)",
                color: "#e2e8f0",
                fontWeight: 600,
                fontSize: "0.97rem",
                textDecoration: "none",
                transition: "background 0.2s",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.1)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
            >
              Ver Ciência
            </a>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.6 }}
            style={{
              marginTop: 72,
              display: "flex",
              gap: 40,
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            {METRICS.map(m => (
              <div key={m.label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: "clamp(1.6rem, 3vw, 2rem)", fontWeight: 700, color: "#38bdf8" }}>
                  {m.value}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#64748b", marginTop: 5, fontWeight: 500 }}>
                  {m.label}
                </div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
