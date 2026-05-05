import { createContext, useContext, useState } from "react";
import en from "./en";
import pt from "./pt";

const TRANSLATIONS = { en, pt };
const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("lang") || "en");

  const toggleLang = () => {
    const next = lang === "en" ? "pt" : "en";
    localStorage.setItem("lang", next);
    setLang(next);
  };

  return (
    <LanguageContext.Provider value={{ t: TRANSLATIONS[lang], lang, toggleLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useT() {
  const ctx = useContext(LanguageContext);
  if (!ctx) return { t: TRANSLATIONS.en, lang: "en", toggleLang: () => {} };
  return ctx;
}
