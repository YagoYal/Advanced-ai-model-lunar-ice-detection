import { useState, useEffect } from "react";
import { useT } from "../i18n";

export default function Navbar() {
  const { t, lang, toggleLang } = useT();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  const LINKS = [
    { href: "#sobre",       label: t.nav.sobre },
    { href: "#arquitetura", label: t.nav.arquitetura },
    { href: "#ciencia",     label: t.nav.ciencia },
    { href: "#dados",       label: t.nav.dados },
    { href: "#analise",     label: t.nav.analise },
    { href: "#rover",       label: t.nav.rover },
    { href: "#referencias", label: t.nav.referencias },
  ];

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 20);
      setOpen(false);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const close = () => setOpen(false);

  const LangToggle = ({ style }) => (
    <button
      type="button"
      onClick={toggleLang}
      style={{
        background: "none",
        border: "1px solid rgba(255,255,255,0.13)",
        borderRadius: 20,
        cursor: "pointer",
        padding: "4px 11px",
        display: "flex",
        alignItems: "center",
        gap: 4,
        fontSize: "0.76rem",
        fontWeight: 700,
        letterSpacing: 0.5,
        lineHeight: 1,
        ...style,
      }}
    >
      <span style={{ color: lang === "en" ? "#38bdf8" : "#475569" }}>EN</span>
      <span style={{ color: "#334155" }}>|</span>
      <span style={{ color: lang === "pt" ? "#38bdf8" : "#475569" }}>PT</span>
    </button>
  );

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
          <li>
            <LangToggle />
          </li>
        </ul>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            type="button"
            className="nav-hamburger"
            onClick={() => setOpen(o => !o)}
            aria-label={open ? t.nav.closeMenu : t.nav.openMenu}
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
          <div style={{ padding: "14px 24px", borderTop: "1px solid rgba(255,255,255,0.04)" }}>
            <LangToggle />
          </div>
        </div>
      )}
    </nav>
  );
}
