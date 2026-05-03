import { MapContainer, TileLayer, useMapEvents } from "react-leaflet";
import { useState } from "react";

function ClickHandler({ onClick }) {
  useMapEvents({
    click(e) {
      onClick(e.latlng);
    }
  });
  return null;
}

export default function LunarMap({ onSelect, children }) {
  const [map, setMap] = useState(null);

  return (
    <MapContainer
      center={[0, 0]}
      zoom={2}
      style={{ height: 400 }}
      whenCreated={setMap}
    >
      <TileLayer
        url="https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_100m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg"
      />

      <ClickHandler onClick={onSelect} />

      {/* 🔥 permite overlays (rover, heatmap) */}
      {map && children && children(map)}
    </MapContainer>
  );
}