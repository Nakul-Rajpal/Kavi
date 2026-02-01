"use client";

import dynamic from "next/dynamic";
import { useState, useCallback, useEffect } from "react";
import Header from "@/components/Header";
import GlassPanel from "@/components/GlassPanel";
import Timeline from "@/components/Timeline";
import FilterMenu, { IssueTypeId } from "@/components/FilterMenu";
import DetectionsSidebar from "@/components/DetectionsSidebar";
import { AnimatePresence } from "framer-motion";
import { Ping } from "@/lib/supabase";

// Dynamically import map to avoid SSR issues with Leaflet
const Map = dynamic(() => import("@/components/Map"), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#0d1117] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <p className="text-cyan-500/70 font-bold tracking-widest text-xs uppercase">Connecting to Database...</p>
      </div>
    </div>
  )
});

export default function Dashboard() {
  const [isLive, setIsLive] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [timeRange, setTimeRange] = useState("all"); // Time range filter: 1h, 6h, 12h, 24h, 7d, all
  const [pings, setPings] = useState<Ping[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [liveStreamUrl, setLiveStreamUrl] = useState<string | null>(null);

  // Fetch live stream URL when Live tab is opened (from API or env)
  useEffect(() => {
    if (!isLive) return;
    fetch("/api/stream")
      .then((res) => res.json())
      .then((data) => setLiveStreamUrl(data.streamUrl ?? null))
      .catch(() => setLiveStreamUrl(null));
  }, [isLive]);
  const [activeFilters, setActiveFilters] = useState<Set<IssueTypeId>>(new Set());

  const handlePingsUpdate = useCallback((data: { count: number; latest: Ping | null; pings: Ping[] }) => {
    setPings(data.pings);
    if (data.pings.length > 0) {
      setConnectionStatus('connected');
    }
  }, []);

  const handleFilterChange = useCallback((filters: Set<IssueTypeId>) => {
    setActiveFilters(filters);
  }, []);

  const handleTimeRangeChange = useCallback((range: string) => {
    setTimeRange(range);
  }, []);

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#0d1117]">
      {/* Map Layer */}
      <div className="absolute inset-0 z-0">
        <Map 
          isLive={isLive} 
          timeRange={timeRange}
          onPingsUpdate={handlePingsUpdate}
          activeFilters={activeFilters}
        />
      </div>

      {/* UI Overlays */}
      <div className="relative z-10 h-full w-full pointer-events-none">
        <Header 
          isLive={isLive} 
          setIsLive={setIsLive} 
          showTimeline={showTimeline}
          setShowTimeline={setShowTimeline}
        />

        {/* Detections Sidebar - now with real data */}
        <DetectionsSidebar pings={pings} connectionStatus={connectionStatus} />

        <AnimatePresence>
          {isLive && (
            <GlassPanel 
              onClose={() => setIsLive(false)} 
              title="Live Drone Feed"
              streamUrl={liveStreamUrl}
              fullScreen
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {showTimeline && (
            <Timeline 
              timeRange={timeRange}
              onTimeRangeChange={handleTimeRangeChange}
            />
          )}
        </AnimatePresence>

        <FilterMenu 
          activeFilters={activeFilters}
          onFilterChange={handleFilterChange}
        />
      </div>
    </main>
  );
}
