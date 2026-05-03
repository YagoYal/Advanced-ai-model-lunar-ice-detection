import Navbar from "./components/Navbar";
import ScrollToTop from "./components/ScrollToTop";
import HeroSection from "./sections/HeroSection";
import SobreSection from "./sections/SobreSection";
import ArquiteturaSection from "./sections/ArquiteturaSection";
import CienciaSection from "./sections/CienciaSection";
import DadosSection from "./sections/DadosSection";
import AnaliseSection from "./sections/AnaliseSection";
import RoverSection from "./sections/RoverSection";
import ReferenciasSection from "./sections/ReferenciasSection";

export default function LandingPage() {
  return (
    <div style={{ background: "#0a0f1e", minHeight: "100vh", color: "#e2e8f0" }}>
      <Navbar />
      <main>
        <HeroSection />
        <SobreSection />
        <ArquiteturaSection />
        <CienciaSection />
        <DadosSection />
        <AnaliseSection />
        <RoverSection />
        <ReferenciasSection />
      </main>
      <ScrollToTop />
    </div>
  );
}
