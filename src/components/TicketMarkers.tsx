"use client";

import { useState, useCallback, useEffect } from "react";
import { Marker, Popup } from "react-map-gl/maplibre";

// Debug flag - set to false in production
const DEBUG = true;
const log = (...args: unknown[]) => DEBUG && console.log("[TicketMarkers]", ...args);

// Ticket data shape from Supabase
export type Ticket = {
  id: string;
  lat: number;
  long: number;
  image_url: string;
  created_at: string;
  status: string;
  severity: string;
  effort_minutes: number;
};

// Format minutes to hours
function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = minutes / 60;
  return hours === 1 ? "1 hour" : `${hours.toFixed(1)} hours`;
}

// Format timestamp
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Status badge color
function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    new: "#3b82f6",
    triaged: "#8b5cf6",
    assigned: "#f59e0b",
    in_progress: "#f97316",
    resolved: "#22c55e",
    rejected: "#6b7280",
  };
  return colors[status] || "#6b7280";
}

// Severity badge color
function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    low: "#22c55e",
    medium: "#f59e0b",
    high: "#ef4444",
  };
  return colors[severity] || "#6b7280";
}

// Styles
const styles = {
  card: {
    width: "220px",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: "13px",
    color: "#1f2937",
    background: "#ffffff",
    borderRadius: "12px",
    padding: "12px",
    boxShadow: "0 10px 40px rgba(0, 0, 0, 0.2)",
  } as React.CSSProperties,
  thumbnail: {
    width: "100%",
    height: "100px",
    objectFit: "cover",
    borderRadius: "6px",
    marginBottom: "10px",
    backgroundColor: "#e5e7eb",
  } as React.CSSProperties,
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "6px",
  } as React.CSSProperties,
  label: {
    color: "#6b7280",
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  } as React.CSSProperties,
  value: {
    fontWeight: 500,
    color: "#111827",
  } as React.CSSProperties,
  badge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: 600,
    textTransform: "uppercase",
  } as React.CSSProperties,
  timestamp: {
    fontSize: "11px",
    color: "#9ca3af",
    marginTop: "8px",
    borderTop: "1px solid #e5e7eb",
    paddingTop: "8px",
  } as React.CSSProperties,
  marker: {
    width: "44px",
    height: "44px",
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
  } as React.CSSProperties,
  markerGlow: {
    position: "absolute",
    inset: "-8px",
    borderRadius: "50%",
    opacity: 0.3,
    filter: "blur(12px)",
  } as React.CSSProperties,
  markerInner: {
    width: "44px",
    height: "44px",
    background: "rgba(0, 0, 0, 0.85)",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "20px",
    position: "relative",
    zIndex: 1,
  } as React.CSSProperties,
};

// Single ticket marker with hover popup
function TicketMarker({
  ticket,
  hoveredId,
  onHover,
  onLeave,
}: {
  ticket: Ticket;
  hoveredId: string | null;
  onHover: (id: string) => void;
  onLeave: () => void;
}) {
  const isHovered = hoveredId === ticket.id;
  const color = getSeverityColor(ticket.severity);

  log("Rendering marker:", ticket.id, "hovered:", isHovered, "at:", [ticket.lat, ticket.long]);

  return (
    <>
      <Marker
        longitude={ticket.long}
        latitude={ticket.lat}
        anchor="center"
      >
        <div
          style={styles.marker}
          onMouseEnter={() => {
            log("=== MOUSEENTER ===", ticket.id);
            onHover(ticket.id);
          }}
          onMouseLeave={() => {
            log("=== MOUSELEAVE ===", ticket.id);
            onLeave();
          }}
        >
          {/* Glow effect */}
          <div
            style={{
              ...styles.markerGlow,
              background: color,
            }}
          />
          {/* Main marker */}
          <div
            style={{
              ...styles.markerInner,
              border: `2px solid ${color}`,
              boxShadow: `0 0 25px ${color}80`,
              transform: isHovered ? "scale(1.15)" : "scale(1)",
              transition: "transform 0.15s ease",
            }}
          >
            📍
          </div>
        </div>
      </Marker>

      {/* Popup - shown when hovered */}
      {isHovered && (
        <Popup
          longitude={ticket.long}
          latitude={ticket.lat}
          anchor="bottom"
          closeButton={false}
          closeOnClick={false}
          offset={[0, -24] as [number, number]}
        >
          <div style={styles.card}>
            {/* Thumbnail */}
            <img
              src={ticket.image_url}
              alt="Issue"
              style={styles.thumbnail}
              onError={(e) => {
                (e.target as HTMLImageElement).src =
                  'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23e5e7eb" width="100" height="100"/><text x="50" y="55" text-anchor="middle" fill="%239ca3af" font-size="12">No image</text></svg>';
              }}
            />

            {/* Status */}
            <div style={styles.row}>
              <span style={styles.label}>Status</span>
              <span
                style={{
                  ...styles.badge,
                  backgroundColor: getStatusColor(ticket.status),
                  color: "#fff",
                }}
              >
                {ticket.status.replace("_", " ")}
              </span>
            </div>

            {/* Severity */}
            <div style={styles.row}>
              <span style={styles.label}>Severity</span>
              <span
                style={{
                  ...styles.badge,
                  backgroundColor: getSeverityColor(ticket.severity),
                  color: "#fff",
                }}
              >
                {ticket.severity}
              </span>
            </div>

            {/* Time to fix */}
            <div style={styles.row}>
              <span style={styles.label}>Time to Fix</span>
              <span style={styles.value}>{formatTime(ticket.effort_minutes)}</span>
            </div>

            {/* Timestamp */}
            <div style={styles.timestamp}>{formatDate(ticket.created_at)}</div>
          </div>
        </Popup>
      )}
    </>
  );
}

// Main component: renders all ticket markers
export default function TicketMarkers({ tickets }: { tickets: Ticket[] }) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const handleHover = useCallback((id: string) => {
    log("handleHover called:", id);
    setHoveredId(id);
  }, []);

  const handleLeave = useCallback(() => {
    log("handleLeave called");
    setHoveredId(null);
  }, []);

  useEffect(() => {
    log("Component rendered with", tickets.length, "tickets");
    log("Current hoveredId:", hoveredId);
  }, [tickets.length, hoveredId]);

  if (!tickets || tickets.length === 0) {
    log("WARNING: No tickets to render!");
    return null;
  }

  return (
    <>
      {tickets.map((ticket) => (
        <TicketMarker
          key={ticket.id}
          ticket={ticket}
          hoveredId={hoveredId}
          onHover={handleHover}
          onLeave={handleLeave}
        />
      ))}
    </>
  );
}
