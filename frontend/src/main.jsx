import React from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./styles/style.css";
import "./leafletFix";
import LandingPage from "./LandingPage";
import { LanguageProvider } from "./i18n";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <LanguageProvider>
      <LandingPage />
    </LanguageProvider>
  </React.StrictMode>
);
