import { Polyline, Marker, Popup } from "react-leaflet";
import { useT } from "../i18n";

// Converte índice de grade (0-179, 0-359) para graus Leaflet (-90..+90, -180..+180)
function gridParaLatLon(pos) {
  return [pos[0] - 90, pos[1] - 180];
}

export default function RoverPath({ caminho }) {
  const { t } = useT();
  if (!caminho || caminho.length === 0) return null;

  const positions = caminho.map(p => gridParaLatLon(p.posicao));
  const ultima    = positions[positions.length - 1];
  const melhor    = caminho.reduce((acc, p) =>
    (p.probabilidade_gelo ?? 0) > (acc.probabilidade_gelo ?? 0) ? p : acc, caminho[0]
  );

  return (
    <>
      <Polyline
        positions={positions}
        pathOptions={{ color: "#7dd3fc", weight: 2, opacity: 0.8, dashArray: "4 4" }}
      />
      <Marker position={ultima}>
        <Popup>
          {t.roverPath.finalPosition}<br />
          Lat: {ultima[0].toFixed(1)}°  Lon: {ultima[1].toFixed(1)}°
        </Popup>
      </Marker>
      {melhor.probabilidade_gelo > 0.5 && (
        <Marker position={gridParaLatLon(melhor.posicao)}>
          <Popup>
            {t.roverPath.bestPSR}<br />
            Prob: {(melhor.probabilidade_gelo * 100).toFixed(1)}%
          </Popup>
        </Marker>
      )}
    </>
  );
}
