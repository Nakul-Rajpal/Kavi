"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Header from "@/components/Header";
import GlassPanel from "@/components/GlassPanel";
import Timeline from "@/components/Timeline";
import FilterMenu from "@/components/FilterMenu";
import DetectionsSidebar from "@/components/DetectionsSidebar";
import { AnimatePresence } from "framer-motion";

// Dynamically import map to avoid SSR issues with Leaflet
const Map = dynamic(() => import("@/components/Map"), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#0d1117] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <p className="text-cyan-500/70 font-bold tracking-widest text-xs uppercase">Loading Map...</p>
      </div>
    </div>
  )
});

export default function Dashboard() {
  const [isLive, setIsLive] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [currentTime, setCurrentTime] = useState("12:00 PM");

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#0d1117]">
      {/* Map Layer */}
      <div className="absolute inset-0 z-0">
        <Map isLive={isLive} currentTime={currentTime} />
      </div>

      {/* UI Overlays */}
      <div className="relative z-10 h-full w-full pointer-events-none">
        <Header 
          isLive={isLive} 
          setIsLive={setIsLive} 
          showTimeline={showTimeline}
          setShowTimeline={setShowTimeline}
        />

        {/* Detections Sidebar */}
        <DetectionsSidebar />

        <AnimatePresence>
          {isLive && (
            <GlassPanel 
              onClose={() => setIsLive(false)} 
              title="Live Drone Feed"
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {showTimeline && (
            <Timeline 
              currentTime={currentTime} 
              setCurrentTime={setCurrentTime} 
            />
          )}
        </AnimatePresence>

        <FilterMenu />
      </div>
    </main>
  );
}
