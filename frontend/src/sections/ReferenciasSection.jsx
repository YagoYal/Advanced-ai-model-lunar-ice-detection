import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { useT } from "../i18n";

const REFS = [
  { authors: "Paige et al.",         year: "2010", journal: "Science 330",    title: "Diviner Lunar Radiometer Observations of Cold Traps in the Moon's South Polar Region" },
  { authors: "Vasavada et al.",       year: "2012", journal: "JGR Planets",    title: "Lunar equatorial surface temperatures and regolith properties from the Diviner Lunar Radiometer Experiment" },
  { authors: "Mazarico et al.",       year: "2011", journal: "Icarus 211",     title: "Illumination conditions of the lunar polar regions using LOLA topography" },
  { authors: "Sato et al.",           year: "2014", journal: "JGR Planets",    title: "Resolved Hapke parameter maps of the Moon" },
  { authors: "Williams et al.",       year: "2019", journal: "Nature Geosci.", title: "Direct evidence of surface exposed water ice in the lunar polar regions" },
  { authors: "Colaprete et al.",      year: "2010", journal: "Science 330",    title: "Detection of Water in the LCROSS Ejecta Plume" },
  { authors: "Spudis et al.",         year: "2010", journal: "GRL",            title: "Initial results for the north pole of the Moon from Mini-RF, Chandrayaan-1 mission" },
  { authors: "Gal & Ghahramani",      year: "2016", journal: "ICML",           title: "Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning" },
];

export default function ReferenciasSection() {
  const { t } = useT();
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.15, once: true });

  return (
    <section id="referencias" ref={ref} style={{ scrollMarginTop: 70, padding: "100px 0 80px" }}>
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 clamp(16px, 4vw, 64px)" }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <p style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>
              {t.referencias.label}
            </p>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, color: "#e2e8f0" }}>
              {t.referencias.title}
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {REFS.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -12 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                style={{
                  padding: "18px 22px",
                  borderRadius: 12,
                  background: "rgba(15,23,42,0.85)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  display: "flex",
                  gap: 16,
                  alignItems: "flex-start",
                }}
              >
                <div style={{
                  minWidth: 30,
                  height: 30,
                  borderRadius: "50%",
                  background: "rgba(56,189,248,0.12)",
                  border: "1px solid rgba(56,189,248,0.28)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.72rem",
                  color: "#38bdf8",
                  fontWeight: 700,
                  flexShrink: 0,
                }}>
                  {i + 1}
                </div>
                <p style={{ color: "#94a3b8", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{r.authors}</span>{" "}
                  <span style={{ color: "#38bdf8" }}>({r.year})</span>{" "}
                  <span style={{ color: "#818cf8", fontStyle: "italic" }}>{r.journal}</span>
                  {" — "}{r.title}
                </p>
              </motion.div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 60, color: "#334155", fontSize: "0.78rem" }}>
            {t.referencias.footer} · {new Date().getFullYear()}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
