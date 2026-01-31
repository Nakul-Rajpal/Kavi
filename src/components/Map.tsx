"use client";

import { MapContainer, TileLayer, Marker, ZoomControl } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// SVG icons as strings for Leaflet markers
const iconsSvg = {
  pothole: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
  light: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>`,
  flood: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/></svg>`,
  debris: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>`,
  sign: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>`,
};

// Create custom marker with glow effect
const createMarkerIcon = (color: string, iconSvg: string) => {
  return L.divIcon({
    className: "custom-marker-icon",
    html: `
      <div style="
        width: 40px;
        height: 40px;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          position: absolute;
          inset: -8px;
          background: ${color};
          border-radius: 50%;
          opacity: 0.3;
          filter: blur(12px);
        "></div>
        <div style="
          width: 40px;
          height: 40px;
          background: rgba(0, 0, 0, 0.8);
          border: 2px solid ${color};
          border-radius: 50%;
          box-shadow: 0 0 25px ${color}80;
          display: flex;
          align-items: center;
          justify-content: center;
          color: ${color};
          position: relative;
          z-index: 1;
        ">
          ${iconSvg}
        </div>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
};


// Detection data with real Providence, RI locations
const detections = [
  { id: 1, position: [41.8245, -71.4111] as [number, number], type: "pothole", label: "Pothole", location: "Kennedy Plaza", color: "#FF3B30", confidence: 94 },
  { id: 2, position: [41.8307, -71.4150] as [number, number], type: "light", label: "Broken Light", location: "Providence Place", color: "#FFD60A", confidence: 87 },
  { id: 3, position: [41.8280, -71.4140] as [number, number], type: "flood", label: "Standing Water", location: "Waterplace Park", color: "#00F3FF", confidence: 91 },
  { id: 4, position: [41.8268, -71.4025] as [number, number], type: "debris", label: "Road Debris", location: "Brown University", color: "#30D158", confidence: 78 },
  { id: 5, position: [41.8210, -71.4220] as [number, number], type: "sign", label: "Damaged Sign", location: "Federal Hill", color: "#FF9F0A", confidence: 85 },
];


interface MapProps {
  isLive: boolean;
  currentTime: string;
}

export default function Map({ isLive, currentTime }: MapProps) {
  const center: [number, number] = [41.8255, -71.4120];

  return (
    <div className="w-full h-full relative" style={{ background: "#0d1117" }}>
      <MapContainer
        center={center}
        zoom={14}
        zoomControl={false}
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%", background: "#0d1117" }}
      >
        {/* Dark Map Tiles */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; CARTO'
        />

        {/* Detection Markers */}
        {detections.map((d) => (
          <Marker
            key={d.id}
            position={d.position}
            icon={createMarkerIcon(d.color, iconsSvg[d.type as keyof typeof iconsSvg])}
          />
        ))}

        <ZoomControl position="bottomleft" />
      </MapContainer>

      {/* Subtle Vignette - not too dark */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.4) 100%)",
          zIndex: 500,
        }}
      />
    </div>
  );
}
