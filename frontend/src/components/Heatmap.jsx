import { useEffect } from "react";
import L from "leaflet";
import "leaflet.heat";

export default function Heatmap({ map, pontos }) {
  useEffect(() => {
    if (!map || !pontos) return;

    const heatLayer = L.heatLayer(
      pontos.map(p => [p.lat, p.lon, p.intensidade]),
      { radius: 25 }
    );

    heatLayer.addTo(map);

    return () => {
      map.removeLayer(heatLayer);
    };
  }, [map, pontos]);

  return null;
}