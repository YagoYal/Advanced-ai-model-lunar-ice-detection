import { useState, useEffect } from "react";

const LINKS = [
  { href: "#sobre", label: "Sobre" },
  { href: "#arquitetura", label: "Arquitetura" },
  { href: "#ciencia", label: "Ciência" },
  { href: "#dados", label: "Dados" },
  { href: "#analise", label: "Análise" },
  { href: "#rover", label: "Rover RL" },
  { href: "#referencias", label: "Referências" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 20);
      setOpen(false);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const close = () => setOpen(false);

  return (
    <nav style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      zIndex: 1100,
      background: scrolled ? "rgba(10,15,30,0.97)" : "rgba(10,15,30,0.75)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      borderBottom: "1px solid rgba(255,255,255,0.07)",
      transition: "background 0.3s",
    }}>
      <div style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "0 24px",
        height: 64,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <a href="#hero" onClick={close} style={{ textDecoration: "none" }}>
          <span style={{
            fontSize: "1.05rem",
            fontWeight: 700,
            background: "linear-gradient(90deg, #38bdf8, #818cf8)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>
            Lunar Ice Intelligence
          </span>
        </a>

        <ul className="nav-desktop-links" style={{
          gap: 28,
          listStyle: "none",
          margin: 0,
          padding: 0,
          alignItems: "center",
        }}>
          {LINKS.map(l => (
            <li key={l.href}>
              <a
                href={l.href}
                style={{ color: "#94a3b8", textDecoration: "none", fontSize: "0.88rem", transition: "color 0.2s" }}
                onMouseEnter={e => (e.currentTarget.style.color = "#e2e8f0")}
                onMouseLeave={e => (e.currentTarget.style.color = "#94a3b8")}
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <button
          type="button"
          className="nav-hamburger"
          onClick={() => setOpen(o => !o)}
          aria-label={open ? "Fechar menu" : "Abrir menu"}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 8,
            color: "#94a3b8",
          }}
        >
          {open ? (
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          )}
        </button>
      </div>

      {open && (
        <div style={{
          background: "#0f172a",
          borderTop: "1px solid rgba(255,255,255,0.07)",
        }}>
          {LINKS.map(l => (
            <a
              key={l.href}
              href={l.href}
              onClick={close}
              style={{
                display: "flex",
                alignItems: "center",
                padding: "16px 24px",
                color: "#94a3b8",
                textDecoration: "none",
                fontSize: "16px",
                minHeight: 44,
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                transition: "color 0.2s, background 0.2s",
              }}
              onMouseEnter={e => { e.currentTarget.style.color = "#e2e8f0"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
              onMouseLeave={e => { e.currentTarget.style.color = "#94a3b8"; e.currentTarget.style.background = "transparent"; }}
            >
              {l.label}
            </a>
          ))}
        </div>
      )}
    </nav>
  );
}
