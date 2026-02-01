"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Source, Layer, Marker } from "react-map-gl/maplibre";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Pause, RotateCcw, Plane, MapPin, Clock, Route } from "lucide-react";

// Brown University area - Exact GPS coordinates flight path
// User-provided waypoints on actual roads
const FLIGHT_PATH: [number, number][] = [
  [-71.40411, 41.82528],  // Point 1
  [-71.40274, 41.82535],  // Point 2
  [-71.40269, 41.82461],  // Point 3
  [-71.40267, 41.82374],  // Point 4
  [-71.40181, 41.82375],  // Point 5
  [-71.40093, 41.82383],  // Point 6
  [-71.40013, 41.82390],  // Point 7
  [-71.40026, 41.82475],  // Point 8
  [-71.40033, 41.82552],  // Point 9
  [-71.40271, 41.82535],  // Point 10 (end)
];

// Street names along the route
const ROUTE_SEGMENTS = [
  { start: 0, end: 1, name: "George Street" },
  { start: 1, end: 3, name: "Brown Street" },
  { start: 3, end: 6, name: "Power Street" },
  { start: 6, end: 8, name: "Thayer Street" },
  { start: 8, end: 10, name: "George Street" },
];

interface DroneFlightPathProps {
  isVisible: boolean;
  onToggle: () => void;
}

// Calculate distance between two GPS points (Haversine formula)
function calculateDistance(p1: [number, number], p2: [number, number]): number {
  const R = 6371000; // Earth radius in meters
  const lat1 = (p1[1] * Math.PI) / 180;
  const lat2 = (p2[1] * Math.PI) / 180;
  const deltaLat = ((p2[1] - p1[1]) * Math.PI) / 180;
  const deltaLng = ((p2[0] - p1[0]) * Math.PI) / 180;

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

// Interpolate position along path
function interpolatePosition(path: [number, number][], progress: number): [number, number] {
  const totalSegments = path.length - 1;
  const scaledProgress = progress * totalSegments;
  const segmentIndex = Math.min(Math.floor(scaledProgress), totalSegments - 1);
  const segmentProgress = scaledProgress - segmentIndex;

  const p1 = path[segmentIndex];
  const p2 = path[segmentIndex + 1];

  return [
    p1[0] + (p2[0] - p1[0]) * segmentProgress,
    p1[1] + (p2[1] - p1[1]) * segmentProgress,
  ];
}

// Calculate bearing between two points
function calculateBearing(p1: [number, number], p2: [number, number]): number {
  const lng1 = (p1[0] * Math.PI) / 180;
  const lng2 = (p2[0] * Math.PI) / 180;
  const lat1 = (p1[1] * Math.PI) / 180;
  const lat2 = (p2[1] * Math.PI) / 180;

  const dLng = lng2 - lng1;
  const x = Math.sin(dLng) * Math.cos(lat2);
  const y = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);

  return ((Math.atan2(x, y) * 180) / Math.PI + 360) % 360;
}

// Get current street name based on progress
function getCurrentStreet(progress: number): string {
  const currentIndex = Math.floor(progress * (FLIGHT_PATH.length - 1));
  for (const segment of ROUTE_SEGMENTS) {
    if (currentIndex >= segment.start && currentIndex <= segment.end) {
      return segment.name;
    }
  }
  return "Brown Campus";
}

export default function DroneFlightPath({ isVisible, onToggle }: DroneFlightPathProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showControls, setShowControls] = useState(true);

  // Animation loop - 30 seconds for full path
  const FLIGHT_DURATION = 30000;

  useEffect(() => {
    if (!isPlaying || !isVisible) return;

    const startTime = Date.now() - progress * FLIGHT_DURATION;
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min(elapsed / FLIGHT_DURATION, 1);
      setProgress(newProgress);

      if (newProgress >= 1) {
        setIsPlaying(false);
      }
    };

    const interval = setInterval(animate, 50);
    return () => clearInterval(interval);
  }, [isPlaying, isVisible, progress]);

  // Current drone position
  const dronePosition = useMemo(() => interpolatePosition(FLIGHT_PATH, progress), [progress]);

  // Calculate bearing for drone rotation
  const bearing = useMemo(() => {
    if (progress >= 0.99) return 0;
    const nextProgress = Math.min(progress + 0.01, 1);
    const nextPos = interpolatePosition(FLIGHT_PATH, nextProgress);
    return calculateBearing(dronePosition, nextPos);
  }, [dronePosition, progress]);

  // Total distance
  const totalDistance = useMemo(() => {
    let distance = 0;
    for (let i = 0; i < FLIGHT_PATH.length - 1; i++) {
      distance += calculateDistance(FLIGHT_PATH[i], FLIGHT_PATH[i + 1]);
    }
    return distance;
  }, []);

  // Traveled path for the gradient effect
  const traveledPath = useMemo(() => {
    const currentIndex = Math.floor(progress * (FLIGHT_PATH.length - 1));
    const points = FLIGHT_PATH.slice(0, currentIndex + 1);
    if (points.length > 0) {
      points.push(dronePosition);
    }
    return points;
  }, [progress, dronePosition]);

  const handlePlayPause = useCallback(() => {
    if (progress >= 1) {
      setProgress(0);
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying, progress]);

  const handleReset = useCallback(() => {
    setProgress(0);
    setIsPlaying(false);
  }, []);

  const currentStreet = getCurrentStreet(progress);
  const distanceCovered = (totalDistance * progress / 1000).toFixed(2);
  const elapsedTime = Math.floor(progress * 30); // 30 seconds total duration

  if (!isVisible) return null;

  return (
    <>
      {/* Full path - dimmed background path */}
      <Source
        id="flight-path-full"
        type="geojson"
        data={{
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: FLIGHT_PATH,
          },
        }}
      >
        <Layer
          id="flight-path-full-outline"
          type="line"
          paint={{
            "line-color": "#00F3FF",
            "line-width": 6,
            "line-opacity": 0.15,
            "line-blur": 4,
          }}
        />
        <Layer
          id="flight-path-full-line"
          type="line"
          paint={{
            "line-color": "#00F3FF",
            "line-width": 3,
            "line-opacity": 0.2,
            "line-dasharray": [2, 4],
          }}
        />
      </Source>

      {/* Traveled path - glowing effect */}
      {traveledPath.length > 1 && (
        <Source
          id="flight-path-traveled"
          type="geojson"
          data={{
            type: "Feature",
            properties: {},
            geometry: {
              type: "LineString",
              coordinates: traveledPath,
            },
          }}
        >
          {/* Outer glow */}
          <Layer
            id="flight-path-traveled-glow"
            type="line"
            paint={{
              "line-color": "#00F3FF",
              "line-width": 16,
              "line-opacity": 0.3,
              "line-blur": 12,
            }}
          />
          {/* Middle glow */}
          <Layer
            id="flight-path-traveled-mid"
            type="line"
            paint={{
              "line-color": "#00F3FF",
              "line-width": 6,
              "line-opacity": 0.6,
              "line-blur": 2,
            }}
          />
          {/* Core line */}
          <Layer
            id="flight-path-traveled-core"
            type="line"
            paint={{
              "line-color": "#ffffff",
              "line-width": 2,
              "line-opacity": 0.9,
            }}
          />
        </Source>
      )}

      {/* Waypoint markers */}
      {FLIGHT_PATH.map((point, index) => (
        <Marker
          key={`waypoint-${index}`}
          longitude={point[0]}
          latitude={point[1]}
          anchor="center"
        >
          <div
            style={{
              width: index === 0 || index === FLIGHT_PATH.length - 1 ? "12px" : "6px",
              height: index === 0 || index === FLIGHT_PATH.length - 1 ? "12px" : "6px",
              borderRadius: "50%",
              background: index === 0 ? "#30D158" : index === FLIGHT_PATH.length - 1 ? "#FF3B30" : "rgba(0, 243, 255, 0.5)",
              border: index === 0 || index === FLIGHT_PATH.length - 1 ? "2px solid white" : "none",
              boxShadow: index === 0 ? "0 0 15px #30D158" : index === FLIGHT_PATH.length - 1 ? "0 0 15px #FF3B30" : "none",
              opacity: progress * (FLIGHT_PATH.length - 1) > index ? 1 : 0.4,
              transition: "opacity 0.3s ease",
            }}
          />
        </Marker>
      ))}

      {/* Drone marker */}
      <Marker
        longitude={dronePosition[0]}
        latitude={dronePosition[1]}
        anchor="center"
      >
        <div
          style={{
            transform: `rotate(${bearing}deg)`,
            transition: "transform 0.1s linear",
          }}
        >
          {/* Pulse ring */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "60px",
              height: "60px",
              borderRadius: "50%",
              border: "2px solid rgba(0, 243, 255, 0.4)",
              animation: isPlaying ? "drone-pulse 1.5s ease-out infinite" : "none",
            }}
          />
          {/* Drone icon container */}
          <div
            style={{
              width: "40px",
              height: "40px",
              background: "linear-gradient(135deg, #0d1117 0%, #1a1f2e 100%)",
              border: "2px solid #00F3FF",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 30px rgba(0, 243, 255, 0.6), inset 0 0 15px rgba(0, 243, 255, 0.2)",
              position: "relative",
            }}
          >
            <Plane
              size={20}
              style={{
                color: "#00F3FF",
                filter: "drop-shadow(0 0 5px #00F3FF)",
                transform: "rotate(0deg)",
              }}
            />
          </div>
        </div>
      </Marker>

      {/* Control Panel Overlay */}
      <AnimatePresence>
        {showControls && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[550] pointer-events-auto"
          >
            <div
              style={{
                background: "rgba(0, 0, 0, 0.85)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(0, 243, 255, 0.2)",
                borderRadius: "24px",
                padding: "20px 28px",
                minWidth: "420px",
                boxShadow: "0 20px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(0, 243, 255, 0.1)",
              }}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: "linear-gradient(135deg, rgba(0, 243, 255, 0.2) 0%, rgba(188, 0, 255, 0.2) 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Route size={18} style={{ color: "#00F3FF" }} />
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">
                      Drone Flight Path
                    </div>
                    <div className="text-sm text-white font-semibold">
                      Brown University Scan
                    </div>
                  </div>
                </div>
                <button
                  onClick={onToggle}
                  className="text-white/40 hover:text-white transition-colors text-xs font-medium px-3 py-1 rounded-full border border-white/10 hover:border-white/30"
                >
                  Hide Path
                </button>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div
                  style={{
                    height: "6px",
                    background: "rgba(255, 255, 255, 0.1)",
                    borderRadius: "3px",
                    overflow: "hidden",
                    position: "relative",
                  }}
                >
                  <motion.div
                    style={{
                      height: "100%",
                      background: "linear-gradient(90deg, #00F3FF 0%, #BC00FF 100%)",
                      borderRadius: "3px",
                      boxShadow: "0 0 20px rgba(0, 243, 255, 0.5)",
                    }}
                    initial={{ width: "0%" }}
                    animate={{ width: `${progress * 100}%` }}
                    transition={{ duration: 0.05 }}
                  />
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-[9px] text-white/40 uppercase tracking-wider mb-1">Current Street</div>
                  <div className="text-sm text-white font-semibold flex items-center justify-center gap-1">
                    <MapPin size={12} className="text-cyan-400" />
                    {currentStreet}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] text-white/40 uppercase tracking-wider mb-1">Distance</div>
                  <div className="text-sm text-cyan-400 font-bold">
                    {distanceCovered} km
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] text-white/40 uppercase tracking-wider mb-1">Elapsed</div>
                  <div className="text-sm text-white font-semibold flex items-center justify-center gap-1">
                    <Clock size={12} className="text-purple-400" />
                    {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, "0")}
                  </div>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={handleReset}
                  className="w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/60 hover:text-white hover:bg-white/10 hover:border-white/20 transition-all"
                >
                  <RotateCcw size={16} />
                </button>
                <button
                  onClick={handlePlayPause}
                  style={{
                    width: "56px",
                    height: "56px",
                    borderRadius: "50%",
                    background: isPlaying
                      ? "linear-gradient(135deg, #FF3B30 0%, #FF6B5B 100%)"
                      : "linear-gradient(135deg, #00F3FF 0%, #00B4D8 100%)",
                    border: "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    boxShadow: isPlaying
                      ? "0 0 30px rgba(255, 59, 48, 0.4)"
                      : "0 0 30px rgba(0, 243, 255, 0.4)",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "scale(1.1)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "scale(1)";
                  }}
                >
                  {isPlaying ? (
                    <Pause size={24} color="white" />
                  ) : (
                    <Play size={24} color="white" style={{ marginLeft: "3px" }} />
                  )}
                </button>
                <div className="w-10 h-10" /> {/* Spacer for symmetry */}
              </div>

              {/* Legend */}
              <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-center gap-6 text-[10px]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#30D158] shadow-[0_0_8px_#30D158]" />
                  <span className="text-white/50">Start</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#FF3B30] shadow-[0_0_8px_#FF3B30]" />
                  <span className="text-white/50">End</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-[3px] rounded-full bg-gradient-to-r from-cyan-400 to-purple-400" />
                  <span className="text-white/50">Flight Path</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style jsx global>{`
        @keyframes drone-pulse {
          0% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 0.6;
          }
          100% {
            transform: translate(-50%, -50%) scale(2);
            opacity: 0;
          }
        }
      `}</style>
    </>
  );
}

