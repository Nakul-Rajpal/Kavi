"use client";

import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { X, Battery, Signal, Navigation, Cpu, Activity, Radio } from "lucide-react";
import Hls from "hls.js";

// Same-origin proxy; stream key must match RTMP URL (e.g. .../live/djidji → /live/djidji/index.m3u8)
const DEFAULT_STREAM_URL =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_LIVE_STREAM_URL
    ? process.env.NEXT_PUBLIC_LIVE_STREAM_URL
    : "/api/hls/live/djidji/index.m3u8";
const FALLBACK_STREAM_URL = "/api/hls/live/dji/index.m3u8";

interface GlassPanelProps {
  onClose: () => void;
  title: string;
  /** Override HLS stream URL (e.g. from API). If not set, uses NEXT_PUBLIC_LIVE_STREAM_URL or default. */
  streamUrl?: string | null;
  /** When true, panel expands to fill the main area (right of Live Detections sidebar, below header). */
  fullScreen?: boolean;
}

export default function GlassPanel({ onClose, title, streamUrl, fullScreen = false }: GlassPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const [streamStatus, setStreamStatus] = useState<"loading" | "live" | "error" | "idle">("loading");
  // When using default URLs, try fallback path if the first returns 404
  const [urlIndex, setUrlIndex] = useState(0);

  const urlsToTry =
    streamUrl != null
      ? [streamUrl]
      : [DEFAULT_STREAM_URL, FALLBACK_STREAM_URL];
  const url = urlsToTry[Math.min(urlIndex, urlsToTry.length - 1)];

  useEffect(() => {
    setUrlIndex(0);
  }, [streamUrl]);

  useEffect(() => {
    if (!url || !videoRef.current) {
      setStreamStatus(url ? "loading" : "idle");
      return;
    }

    const video = videoRef.current;

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      const onLive = () => setStreamStatus("live");
      const onError = () => setStreamStatus("error");
      video.src = url;
      video.addEventListener("loadeddata", onLive);
      video.addEventListener("error", onError);
      return () => {
        video.removeEventListener("loadeddata", onLive);
        video.removeEventListener("error", onError);
        video.src = "";
      };
    }

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      hlsRef.current = hls;
      hls.loadSource(url);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => setStreamStatus("live"));
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          if (urlIndex < urlsToTry.length - 1) {
            setUrlIndex((i) => i + 1);
            setStreamStatus("loading");
          } else {
            setStreamStatus("error");
          }
        }
      });
      return () => {
        hls.destroy();
        hlsRef.current = null;
        setStreamStatus("loading");
      };
    }

    setStreamStatus("error");
    return () => {};
  }, [url, urlIndex]);

  return (
    <motion.div
      initial={fullScreen ? { opacity: 0 } : { x: "100%", opacity: 0, scale: 0.95 }}
      animate={fullScreen ? { opacity: 1 } : { x: 0, opacity: 1, scale: 1 }}
      exit={fullScreen ? { opacity: 0 } : { x: "100%", opacity: 0, scale: 0.95 }}
      transition={{ type: "spring", damping: 30, stiffness: 300 }}
      className={
        fullScreen
          ? "absolute left-[23rem] top-40 right-8 bottom-8 z-[600] pointer-events-auto bg-black rounded-3xl overflow-hidden border border-white/10"
          : "absolute right-8 top-32 bottom-32 w-[450px] z-[600] pointer-events-auto"
      }
    >
      <div
        className={
          fullScreen
            ? "h-full w-full flex flex-col bg-black"
            : "liquid-glass h-full w-full rounded-[40px] p-8 flex flex-col gap-8 shadow-[0_0_100px_rgba(0,0,0,0.8)] border border-white/20"
        }
      >
        {/* Header — always visible; in fullScreen it's an overlay */}
        <div
          className={
            fullScreen
              ? "absolute top-0 left-0 right-0 z-20 flex items-center justify-between p-6 bg-gradient-to-b from-black/80 to-transparent pointer-events-none"
              : "flex items-center justify-between"
          }
        >
          <div className="flex items-center gap-3 pointer-events-auto">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_10px_#ef4444]" />
            <h2 className={`font-black text-white tracking-tighter uppercase ${fullScreen ? "text-2xl md:text-3xl" : "text-2xl"}`}>
              {title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className={`flex items-center justify-center rounded-full transition-all text-white/50 hover:text-white border border-white/10 pointer-events-auto ${
              fullScreen ? "w-12 h-12 bg-black/40 hover:bg-black/60" : "w-10 h-10 bg-white/5 hover:bg-white/10"
            }`}
          >
            <X size={fullScreen ? 24 : 20} />
          </button>
        </div>

        {/* Live Feed Container — real DJI HLS stream; full-screen fills viewport */}
        <div
          className={
            fullScreen
              ? "absolute inset-0 overflow-hidden"
              : "relative flex-[1.5] rounded-[32px] bg-black/60 overflow-hidden border border-white/10 group shadow-inner min-h-[200px]"
          }
        >
          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover"
            muted
            autoPlay
            playsInline
            controls={false}
          />
          {/* Placeholder when no stream or loading/error */}
          {streamStatus !== "live" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 gap-3">
              {streamStatus === "loading" && (
                <>
                  <div className="w-12 h-12 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin" />
                  <p className="text-sm text-white/70 font-medium">Connecting to DJI stream…</p>
                  <p className="text-[10px] text-white/50 max-w-[90%] text-center">
                    Start RTMP in DJI Fly and run <code className="bg-white/10 px-1 rounded">./run_dji_live_rtmp.sh</code> so HLS is available.
                  </p>
                </>
              )}
              {streamStatus === "error" && (
                <>
                  <Radio className="text-white/40" size={40} />
                  <p className="text-sm text-white/70 font-medium">No live feed</p>
                  <p className="text-[10px] text-white/50 text-center max-w-[90%]">
                    Start streaming in DJI Fly first (Transmission → RTMP → Start). The feed only appears while the stream is active. If it still fails, try opening http://localhost:8080/live/djidji/index.m3u8 in the browser while streaming (stream key in RTMP URL must match).
                  </p>
                </>
              )}
              {streamStatus === "idle" && (
                <p className="text-sm text-white/50">No stream URL configured.</p>
              )}
            </div>
          )}

          {/* Refraction Overlay */}
          <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/10 via-transparent to-purple-500/10 pointer-events-none" />

          {/* Overlay UI */}
          <div className="absolute inset-0 p-6 flex flex-col justify-between pointer-events-none font-mono">
            <div className="flex justify-between items-start">
              <div className="flex flex-col gap-1">
                <div className="px-3 py-1 bg-red-500 text-[10px] font-black text-white rounded-full self-start shadow-[0_0_15px_#ef4444]">
                  LIVE • 720p
                </div>
                <div className="text-[10px] text-white/60 mt-2">DJI Air 3S</div>
              </div>
              <div className="flex gap-4 items-center bg-black/40 backdrop-blur-md px-4 py-2 rounded-2xl border border-white/10">
                <div className="flex items-center gap-2">
                  <Battery size={14} className="text-green-400" />
                  <span className="text-[10px] text-white font-bold">—</span>
                </div>
                <div className="w-[1px] h-3 bg-white/20" />
                <div className="flex items-center gap-2">
                  <Signal size={14} className="text-cyan-400" />
                  <span className="text-[10px] text-white font-bold">HLS</span>
                </div>
              </div>
            </div>

            <div className="flex justify-between items-end">
              <div className="space-y-1">
                <div className="text-[10px] text-cyan-400 font-bold flex items-center gap-2">
                  <Navigation size={10} /> DJI RTMP → HLS
                </div>
                <div className="text-[10px] text-white/60">Live tab</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-white/60">
                  {streamStatus === "live" ? "STREAMING" : "WAITING"}
                </div>
              </div>
            </div>
          </div>

          {/* Scanning Line */}
          <div className="absolute inset-x-0 top-0 h-[2px] bg-cyan-400/50 shadow-[0_0_15px_#00F3FF] animate-[scan_4s_linear_infinite] z-10" />
        </div>

        {/* Telemetry Stats, AI, Button — only in side panel */}
        {!fullScreen && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 rounded-[28px] bg-white/5 border border-white/10 flex flex-col gap-2 group hover:bg-white/10 transition-colors">
                <div className="flex items-center gap-2 text-white/40">
                  <Activity size={14} />
                  <span className="text-[10px] uppercase tracking-widest font-black">Velocity</span>
                </div>
                <div className="text-3xl font-black text-cyan-400 group-hover:scale-105 transition-transform origin-left">
                  — <span className="text-sm font-bold opacity-50">km/h</span>
                </div>
              </div>
              <div className="p-6 rounded-[28px] bg-white/5 border border-white/10 flex flex-col gap-2 group hover:bg-white/10 transition-colors">
                <div className="flex items-center gap-2 text-white/40">
                  <Navigation size={14} />
                  <span className="text-[10px] uppercase tracking-widest font-black">Heading</span>
                </div>
                <div className="text-3xl font-black text-purple-400 group-hover:scale-105 transition-transform origin-left">
                  — <span className="text-sm font-bold opacity-50">°</span>
                </div>
              </div>
            </div>

            <div className="p-6 rounded-[28px] bg-cyan-400/5 border border-cyan-400/20 flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-cyan-400/20 flex items-center justify-center text-cyan-400">
                <Cpu size={24} />
              </div>
              <div>
                <div className="text-[10px] font-black text-cyan-400 uppercase tracking-widest">
                  AI Vision Status
                </div>
                <div className="text-sm text-white/80 font-medium">
                  {streamStatus === "live"
                    ? "Live feed — run Kavi with --live for detection"
                    : "Start stream to enable detection"}
                </div>
              </div>
            </div>

            <button className="w-full py-6 rounded-[28px] bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-black tracking-widest uppercase text-sm shadow-[0_20px_40px_rgba(0,243,255,0.2)] hover:shadow-[0_20px_40px_rgba(0,243,255,0.4)] transition-all active:scale-95 hover:-translate-y-1">
              MANUAL OVERRIDE
            </button>
          </>
        )}
      </div>

      <style jsx>{`
        @keyframes scan {
          0% { transform: translateY(0); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { transform: translateY(300px); opacity: 0; }
        }
      `}</style>
    </motion.div>
  );
}
