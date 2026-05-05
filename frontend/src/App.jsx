import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  useMapEvents,
  Marker,
  Popup,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./styles/style.css";
import { analisar, simular } from "./services/api";
import RoverPath from "./components/RoverPath";

// Grade 180x360 (1 grau por pixel)
function coordParaGrid(lat, lng) {
  const gridLat = Math.max(0, Math.min(179, Math.round(lat + 90)));
  const gridLon = Math.max(0, Math.min(359, Math.round(lng + 180)));
  return { gridLat, gridLon };
}

function ClickHandler({ onClick }) {
  useMapEvents({ click(e) { onClick(e.latlng); } });
  return null;
}

export default function App() {
  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [loadingRL, setLoadingRL] = useState(false);
  const [ponto,     setPonto]     = useState(null);
  const [historico, setHistorico] = useState([]);
  const [erro,      setErro]      = useState(null);
  const [caminho,   setCaminho]   = useState(null);

  const handleAnalisar = async (lat, lng) => {
    setLoading(true);
    setErro(null);
    const { gridLat, gridLon } = coordParaGrid(lat, lng);
    try {
      const data = await analisar(gridLat, gridLon);
      setResult(data);
      setHistorico(prev => [
        ...prev,
        { lat: lat.toFixed(2), lon: lng.toFixed(2), prob: data.probabilidade_gelo },
      ]);
    } catch (err) {
      setErro(err.message ?? "Falha ao conectar com o backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleSimularRover = async () => {
    if (!ponto) return;
    setLoadingRL(true);
    setErro(null);
    const { gridLat, gridLon } = coordParaGrid(ponto.lat, ponto.lng);
    try {
      const data = await simular(gridLat, gridLon, 20);
      setCaminho(data.caminho);
    } catch (err) {
      setErro(err.message ?? "Falha ao simular rover.");
    } finally {
      setLoadingRL(false);
    }
  };

  const handleSelect = (coord) => {
    setPonto(coord);
    setCaminho(null);
    handleAnalisar(coord.lat, coord.lng);
  };

  const getClasseProb = (prob) => {
    if (prob > 0.8) return "prob-alta";
    if (prob > 0.5) return "prob-media";
    return "prob-baixa";
  };

  return (
    <div className="container">
      <h1>Lunar Ice Intelligence</h1>
      <p>Clique na superfície da Lua para analisar presença de gelo</p>

      <MapContainer center={[0, 0]} zoom={2} style={{ height: "clamp(280px, 50vh, 520px)" }}>
        <TileLayer
          url="https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg"
          attribution="NASA Trek / LRO WAC"
          minZoom={1}
          maxZoom={7}
        />
        <ClickHandler onClick={handleSelect} />
        {ponto && (
          <Marker position={ponto}>
            <Popup>
              Lat: {ponto.lat.toFixed(2)}°<br />
              Lon: {ponto.lng.toFixed(2)}°
            </Popup>
          </Marker>
        )}
        {caminho && <RoverPath caminho={caminho} />}
      </MapContainer>

      {loading    && <p className="loading">Analisando dados...</p>}
      {loadingRL  && <p className="loading">Simulando rover...</p>}
      {erro       && <p className="erro">{erro}</p>}

      {result && (
        <div className={result.probabilidade_gelo > 0.7 ? "card highlight" : "card"}>
          <h2>Resultado da Análise</h2>
          <p>
            Probabilidade de gelo:{" "}
            <strong className={getClasseProb(result.probabilidade_gelo)}>
              {(result.probabilidade_gelo * 100).toFixed(2)}%
            </strong>
          </p>
          {result.confianca != null && (
            <p>Confiança: <strong>{result.confianca}</strong>{result.variancia != null ? ` (var=${result.variancia.toFixed(4)})` : ""}</p>
          )}
          {result.temperatura != null && (
            <p>Temperatura superfície: {result.temperatura.toFixed(2)} K</p>
          )}
          {result.temperatura_subsolo != null && (
            <p>
              Temperatura subsolo:{" "}
              {result.temperatura_subsolo.map((t, i) =>
                `${["0.1m","0.5m","1.0m"][i]}=${t.toFixed(1)}K`
              ).join("  ")}
            </p>
          )}
          {result.insolacao != null && (
            <p>
              Insolação: {result.insolacao.toFixed(1)} W/m² (média anual)
              {result.insolacao_atual != null &&
                ` / ${result.insolacao_atual.toFixed(1)} W/m² (atual, fase=${result.fase_lunar?.toFixed(2)})`}
            </p>
          )}

          <button
            onClick={handleSimularRover}
            disabled={loadingRL}
            style={{ marginTop: 12 }}
          >
            {loadingRL ? "Simulando..." : "Simular Rover (20 passos)"}
          </button>
        </div>
      )}

      {caminho && (
        <div className="card">
          <h3>Trajetória do Rover</h3>
          <p>{caminho.length} passos executados</p>
          {(() => {
            const melhor = caminho.reduce((a, b) =>
              (b.probabilidade_gelo ?? 0) > (a.probabilidade_gelo ?? 0) ? b : a, caminho[0]
            );
            return melhor.probabilidade_gelo > 0 ? (
              <p>
                Melhor ponto:{" "}
                <strong className={getClasseProb(melhor.probabilidade_gelo)}>
                  {(melhor.probabilidade_gelo * 100).toFixed(1)}%
                </strong>{" "}
                em grid [{melhor.posicao[0]}, {melhor.posicao[1]}]
              </p>
            ) : null;
          })()}
        </div>
      )}

      {historico.length > 0 && (
        <div className="card">
          <h3>Pontos analisados</h3>
          <ul>
            {historico.map((p, i) => (
              <li key={i}>
                ({p.lat}, {p.lon}) → {(p.prob * 100).toFixed(1)}%
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
