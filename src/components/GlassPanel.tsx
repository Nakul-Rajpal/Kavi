"use client";

import { motion } from "framer-motion";
import { X, Battery, Signal, Navigation, Cpu, Wifi, Activity } from "lucide-react";

interface GlassPanelProps {
  onClose: () => void;
  title: string;
}

export default function GlassPanel({ onClose, title }: GlassPanelProps) {
  return (
    <motion.div
      initial={{ x: "100%", opacity: 0, scale: 0.95 }}
      animate={{ x: 0, opacity: 1, scale: 1 }}
      exit={{ x: "100%", opacity: 0, scale: 0.95 }}
      transition={{ type: "spring", damping: 30, stiffness: 300 }}
      className="absolute right-8 top-32 bottom-32 w-[450px] z-[600] pointer-events-auto"
    >
      <div className="liquid-glass h-full w-full rounded-[40px] p-8 flex flex-col gap-8 shadow-[0_0_100px_rgba(0,0,0,0.8)] border border-white/20">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_10px_#ef4444]" />
            <h2 className="text-2xl font-black text-white tracking-tighter uppercase">{title}</h2>
          </div>
          <button 
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center bg-white/5 hover:bg-white/10 rounded-full transition-all text-white/50 hover:text-white border border-white/10"
          >
            <X size={20} />
          </button>
        </div>

        {/* Live Feed Container */}
        <div className="relative flex-[1.5] rounded-[32px] bg-black/60 overflow-hidden border border-white/10 group shadow-inner">
          {/* Simulated Video Feed */}
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1449824913935-59a10b8d2000?auto=format&fit=crop&w=1200&q=80')] bg-cover bg-center opacity-70 group-hover:scale-110 transition-transform duration-[20s] ease-out" />
          
          {/* Refraction Overlay */}
          <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/10 via-transparent to-purple-500/10 pointer-events-none" />
          
          {/* Overlay UI */}
          <div className="absolute inset-0 p-6 flex flex-col justify-between pointer-events-none font-mono">
            <div className="flex justify-between items-start">
              <div className="flex flex-col gap-1">
                <div className="px-3 py-1 bg-red-500 text-[10px] font-black text-white rounded-full self-start shadow-[0_0_15px_#ef4444]">
                  LIVE • 4K
                </div>
                <div className="text-[10px] text-white/60 mt-2">CAM_01_NORTH</div>
              </div>
              <div className="flex gap-4 items-center bg-black/40 backdrop-blur-md px-4 py-2 rounded-2xl border border-white/10">
                <div className="flex items-center gap-2">
                  <Battery size={14} className="text-green-400" />
                  <span className="text-[10px] text-white font-bold">84%</span>
                </div>
                <div className="w-[1px] h-3 bg-white/20" />
                <div className="flex items-center gap-2">
                  <Signal size={14} className="text-cyan-400" />
                  <span className="text-[10px] text-white font-bold">42ms</span>
                </div>
              </div>
            </div>
            
            <div className="flex justify-between items-end">
              <div className="space-y-1">
                <div className="text-[10px] text-cyan-400 font-bold flex items-center gap-2">
                  <Navigation size={10} /> 41.8240° N, 71.4128° W
                </div>
                <div className="text-[10px] text-white/60">ALTITUDE: 45.2m</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-white/60">FRAME_ID: 84291-X</div>
                <div className="text-[10px] text-white/60">SENSORS: NOMINAL</div>
              </div>
            </div>
          </div>

          {/* Scanning Line */}
          <div className="absolute inset-x-0 top-0 h-[2px] bg-cyan-400/50 shadow-[0_0_15px_#00F3FF] animate-[scan_4s_linear_infinite] z-10" />
        </div>

        {/* Telemetry Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-6 rounded-[28px] bg-white/5 border border-white/10 flex flex-col gap-2 group hover:bg-white/10 transition-colors">
            <div className="flex items-center gap-2 text-white/40">
              <Activity size={14} />
              <span className="text-[10px] uppercase tracking-widest font-black">Velocity</span>
            </div>
            <div className="text-3xl font-black text-cyan-400 group-hover:scale-105 transition-transform origin-left">
              12.4 <span className="text-sm font-bold opacity-50">km/h</span>
            </div>
          </div>
          <div className="p-6 rounded-[28px] bg-white/5 border border-white/10 flex flex-col gap-2 group hover:bg-white/10 transition-colors">
            <div className="flex items-center gap-2 text-white/40">
              <Navigation size={14} />
              <span className="text-[10px] uppercase tracking-widest font-black">Heading</span>
            </div>
            <div className="text-3xl font-black text-purple-400 group-hover:scale-105 transition-transform origin-left">
              284° <span className="text-sm font-bold opacity-50">NW</span>
            </div>
          </div>
        </div>

        {/* AI Analysis Info */}
        <div className="p-6 rounded-[28px] bg-cyan-400/5 border border-cyan-400/20 flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-cyan-400/20 flex items-center justify-center text-cyan-400">
            <Cpu size={24} />
          </div>
          <div>
            <div className="text-[10px] font-black text-cyan-400 uppercase tracking-widest">AI Vision Status</div>
            <div className="text-sm text-white/80 font-medium">Detecting: Pothole (92% Confidence)</div>
          </div>
        </div>

        {/* Action Button */}
        <button className="w-full py-6 rounded-[28px] bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-black tracking-widest uppercase text-sm shadow-[0_20px_40px_rgba(0,243,255,0.2)] hover:shadow-[0_20px_40px_rgba(0,243,255,0.4)] transition-all active:scale-95 hover:-translate-y-1">
          MANUAL OVERRIDE
        </button>
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
