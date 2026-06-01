import React from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./styles/style.css";
import "./leafletFix";
import LandingPage from "./LandingPage";
import { LanguageProvider } from "./i18n";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(console.warn);
  });
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <LanguageProvider>
      <LandingPage />
    </LanguageProvider>
  </React.StrictMode>
);
