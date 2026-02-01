"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Map, { Marker, Popup, NavigationControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { getSupabase, Ping } from "@/lib/supabase";

// Debug logging
const DEBUG = true;
const log = (...args: unknown[]) => DEBUG && console.log("[Map]", ...args);

// Dark style with 3D buildings and visible labels
const MAP_STYLE = {
  version: 8 as const,
  name: "Dark 3D",
  sources: {
    osm: {
      type: "raster" as const,
      tiles: [
        "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    },
  },
  layers: [
    {
      id: "osm-tiles",
      type: "raster" as const,
      source: "osm",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

// Color mapping for severity
const severityColors: Record<string, string> = {
  high: "#FF3B30",
  medium: "#FFD60A",
  low: "#30D158",
  default: "#00F3FF",
};

// Custom marker component with hover support
function CustomMarker({ 
  ping, 
  isHovered,
  onMouseEnter,
  onMouseLeave,
}: { 
  ping: Ping;
  isHovered: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}) {
  const severity = ping.severity || "default";
  const color = severityColors[severity] || severityColors.default;
  const type = ping.type || "default";
  
  // Get icon based on type
  const getIcon = () => {
    switch (type) {
      case "pothole":
        return "⚠️";
      case "light":
        return "💡";
      case "flood":
        return "💧";
      case "debris":
        return "🗑️";
      case "sign":
        return "🚧";
      default:
        return "📍";
    }
  };

  return (
    <div
      style={{
        width: "44px",
        height: "44px",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
      }}
      onMouseEnter={() => {
        log("=== MOUSE ENTER ===", ping.id);
        onMouseEnter();
      }}
      onMouseLeave={() => {
        log("=== MOUSE LEAVE ===", ping.id);
        onMouseLeave();
      }}
    >
      {/* Glow effect */}
      <div
        style={{
          position: "absolute",
          inset: "-8px",
          background: color,
          borderRadius: "50%",
          opacity: isHovered ? 0.5 : 0.3,
          filter: "blur(12px)",
          transition: "opacity 0.15s ease",
        }}
      />
      {/* Main marker */}
      <div
        style={{
          width: "44px",
          height: "44px",
          background: "rgba(0, 0, 0, 0.85)",
          border: `2px solid ${color}`,
          borderRadius: "50%",
          boxShadow: `0 0 25px ${color}80`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "20px",
          position: "relative",
          zIndex: 1,
          transform: isHovered ? "scale(1.15)" : "scale(1)",
          transition: "transform 0.15s ease",
        }}
      >
        {getIcon()}
      </div>
    </div>
  );
}

// Format timestamp
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Format minutes to readable time
function formatTime(minutes?: number): string {
  if (!minutes) return "—";
  if (minutes < 60) return `${minutes} min`;
  const hours = minutes / 60;
  return hours === 1 ? "1 hour" : `${hours.toFixed(1)} hours`;
}

interface MapProps {
  isLive: boolean;
  currentTime: string;
  onPingsUpdate?: (data: { count: number; latest: Ping | null; pings: Ping[] }) => void;
}

export default function Map3D({ isLive, currentTime, onPingsUpdate }: MapProps) {
  const [pings, setPings] = useState<Ping[]>([]);
  const [latestPing, setLatestPing] = useState<Ping | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [hoveredPingId, setHoveredPingId] = useState<string | null>(null);
  const pingIdsRef = useRef(new Set<string>());
  const mapRef = useRef<any>(null);

  // Get the currently hovered ping
  const hoveredPing = hoveredPingId ? pings.find(p => p.id === hoveredPingId) : null;

  log("Render - hoveredPingId:", hoveredPingId, "hoveredPing:", hoveredPing?.id);

  // Providence, RI center
  const [viewState, setViewState] = useState({
    longitude: -71.4120,
    latitude: 41.8255,
    zoom: 15,
    pitch: 50,      // 3D tilt angle
    bearing: -15,   // Rotation
  });

  // Add a ping while avoiding duplicates
  const addPing = useCallback((newPing: Ping) => {
    if (pingIdsRef.current.has(newPing.id)) {
      return false;
    }
    pingIdsRef.current.add(newPing.id);
    setPings((prev) => [...prev, newPing]);
    return true;
  }, []);

  // Fly to a location
  const flyTo = useCallback((lat: number, lng: number) => {
    if (mapRef.current) {
      mapRef.current.flyTo({
        center: [lng, lat],
        zoom: 16,
        pitch: 55,
        duration: 2000,
      });
    }
  }, []);

  // Fetch initial pings from Supabase
  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;

    const fetchInitialPings = async () => {
      const client = getSupabase();
      if (!client) return;
      
      const { data, error } = await client
        .from("pings")
        .select("*")
        .order("created_at", { ascending: true });

      if (error) {
        console.error("Error fetching pings:", error);
        return;
      }

      if (data && data.length > 0) {
        data.forEach((ping: Ping) => pingIdsRef.current.add(ping.id));
        setPings(data);
        setLatestPing(data[data.length - 1]);
        setConnectionStatus("connected");
      }
    };

    fetchInitialPings();
  }, []);

  // Subscribe to realtime INSERT events
  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;

    const channel = supabase
      .channel("pings-realtime-3d")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "pings",
        },
        (payload) => {
          console.log("New ping received:", payload.new);
          const newPing = payload.new as Ping;
          const wasAdded = addPing(newPing);
          if (wasAdded) {
            setLatestPing(newPing);
            // Fly to the new ping
            flyTo(newPing.lat, newPing.lng);
          }
        }
      )
      .subscribe((status) => {
        console.log("Realtime subscription status:", status);
        if (status === "SUBSCRIBED") {
          setConnectionStatus("connected");
        } else if (status === "CLOSED" || status === "CHANNEL_ERROR") {
          setConnectionStatus("disconnected");
        }
      });

    return () => {
      console.log("Cleaning up realtime subscription");
      supabase.removeChannel(channel);
    };
  }, [addPing, flyTo]);

  // Notify parent of pings updates
  useEffect(() => {
    onPingsUpdate?.({ count: pings.length, latest: latestPing, pings });
  }, [pings, latestPing, onPingsUpdate]);

  return (
    <div className="w-full h-full relative" style={{ background: "#0d1117" }}>
      {/* Connection Status Indicator */}
      <div className="absolute top-4 right-4 z-[1000] flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/60 backdrop-blur-md border border-white/10">
        <div
          className={`w-2 h-2 rounded-full ${
            connectionStatus === "connected"
              ? "bg-green-500 animate-pulse shadow-[0_0_8px_#22c55e]"
              : connectionStatus === "connecting"
              ? "bg-yellow-500 animate-pulse"
              : "bg-red-500"
          }`}
        />
        <span className="text-[10px] font-bold uppercase tracking-wider text-white/70">
          {connectionStatus === "connected" ? "Live" : connectionStatus === "connecting" ? "Connecting..." : "Offline"}
        </span>
        <span className="text-[10px] text-white/40">{pings.length} pings</span>
      </div>

      <Map
        ref={mapRef}
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        maxPitch={85}
      >
        {/* Markers for each ping */}
        {pings.map((ping) => (
          <Marker
            key={ping.id}
            longitude={ping.lng}
            latitude={ping.lat}
            anchor="center"
          >
            <CustomMarker 
              ping={ping} 
              isHovered={hoveredPingId === ping.id}
              onMouseEnter={() => {
                log("Setting hoveredPingId to:", ping.id);
                setHoveredPingId(ping.id);
              }}
              onMouseLeave={() => {
                log("Clearing hoveredPingId");
                setHoveredPingId(null);
              }}
            />
          </Marker>
        ))}

        {/* Hover Popup - Ticket Card */}
        {hoveredPing && (
          <Popup
            longitude={hoveredPing.lng}
            latitude={hoveredPing.lat}
            anchor="bottom"
            closeButton={false}
            closeOnClick={false}
            offset={[0, -30] as [number, number]}
          >
            <div
              style={{
                background: "rgba(0, 0, 0, 0.92)",
                backdropFilter: "blur(16px)",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                borderRadius: "14px",
                width: "240px",
                overflow: "hidden",
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
              }}
            >
              {/* Image */}
              <div style={{ position: "relative" }}>
                <img
                  src={hoveredPing.image_url || ""}
                  alt="Detection"
                  style={{
                    width: "100%",
                    height: "120px",
                    objectFit: "cover",
                    backgroundColor: "#1a1a1a",
                    display: "block",
                  }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
                {!hoveredPing.image_url && (
                  <div style={{
                    width: "100%",
                    height: "120px",
                    background: "linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "rgba(255,255,255,0.3)",
                    fontSize: "32px",
                  }}>
                    📷
                  </div>
                )}
              </div>

              {/* Content */}
              <div style={{ padding: "14px 16px" }}>
                {/* Type */}
                <div style={{
                  fontSize: "15px",
                  fontWeight: 700,
                  color: "#fff",
                  marginBottom: "6px",
                  textTransform: "capitalize",
                }}>
                  {hoveredPing.type?.replace(/_/g, " ") || "Detection"}
                </div>

                {/* Street Name */}
                <div style={{
                  fontSize: "12px",
                  color: "rgba(255,255,255,0.6)",
                  marginBottom: "12px",
                }}>
                  📍 {hoveredPing.street_name || `${hoveredPing.lat.toFixed(4)}, ${hoveredPing.lng.toFixed(4)}`}
                </div>

                {/* Info Grid */}
                <div style={{ 
                  display: "grid", 
                  gridTemplateColumns: "1fr 1fr",
                  gap: "10px",
                  marginBottom: "12px",
                }}>
                  {/* Timestamp */}
                  <div>
                    <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "2px" }}>
                      Time
                    </div>
                    <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.8)" }}>
                      {formatDate(hoveredPing.created_at)}
                    </div>
                  </div>

                  {/* Severity */}
                  <div>
                    <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "2px" }}>
                      Severity
                    </div>
                    <div style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      padding: "3px 8px",
                      borderRadius: "6px",
                      display: "inline-block",
                      background: (severityColors[hoveredPing.severity || "default"] || "#666") + "25",
                      color: severityColors[hoveredPing.severity || "default"] || "#999",
                    }}>
                      {hoveredPing.severity || "—"}
                    </div>
                  </div>

                  {/* Time to Fix */}
                  <div>
                    <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "2px" }}>
                      Time to Fix
                    </div>
                    <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.8)", fontWeight: 500 }}>
                      {formatTime(hoveredPing.effort_minutes)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Popup>
        )}

        <NavigationControl position="bottom-left" showCompass={true} />
      </Map>

      {/* Vignette overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.5) 100%)",
          zIndex: 500,
        }}
      />
    </div>
  );
}
