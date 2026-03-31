import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import { apiGet } from "../../lib/api";

function HeatLayer({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return undefined;
    const layer = L.heatLayer(points, { radius: 28, blur: 22, maxZoom: 14, max: 1.2 }).addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, points]);
  return null;
}

export function CrimeMapLeaflet({ selectedState, blinkKey, refreshKey = 0 }) {
  const [incidents, setIncidents] = useState([]);
  const center = [20.5937, 78.9629];

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const data = await apiGet("/map/incidents", { state: selectedState, limit: 250 });
        if (!cancel) setIncidents(data);
      } catch {
        if (!cancel) setIncidents([]);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [selectedState, blinkKey, refreshKey]);

  const heatPoints = useMemo(
    () => incidents.map((i) => [i.latitude, i.longitude, i.is_panic ? 1 : 0.55]),
    [incidents]
  );

  return (
    <div
      className={`rounded-xl overflow-hidden border border-white/10 dark:border-white/10 border-slate-200 shadow-glow transition ${blinkKey ? "ring-2 ring-rose-400 ring-offset-2 ring-offset-slate-900 animate-pulse" : ""}`}
      style={{ height: 320 }}
    >
      <MapContainer center={center} zoom={5} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <HeatLayer points={heatPoints} />
        {incidents.map((i) => (
          <CircleMarker
            key={i.public_id}
            center={[i.latitude, i.longitude]}
            radius={i.public_id === blinkKey ? 14 : 7}
            pathOptions={{
              color: i.is_panic ? "#f43f5e" : "#38bdf8",
              fillColor: i.is_panic ? "#fb7185" : "#22d3ee",
              fillOpacity: 0.65
            }}
          >
            <Popup>
              <div className="text-xs space-y-1 min-w-[160px]">
                <div className="font-semibold">{i.crime_type}</div>
                <div>
                  {i.region}, {i.state}
                </div>
                <div className="opacity-70">{i.created_at}</div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
