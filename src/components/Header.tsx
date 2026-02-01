"use client";

import { Clock, Radio, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";

interface HeaderProps {
  isLive: boolean;
  setIsLive: (val: boolean) => void;
  showTimeline: boolean;
  setShowTimeline: (val: boolean) => void;
}

export default function Header({ isLive, setIsLive, showTimeline, setShowTimeline }: HeaderProps) {
  return (
    <header className="absolute top-0 left-0 right-0 p-8 flex justify-between items-start pointer-events-none z-[700]">
      {/* Left: Branding */}
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="pointer-events-auto"
      >
        <div className="flex items-center gap-4 mb-3">
          <div className="w-12 h-12 liquid-glass rounded-2xl flex items-center justify-center border border-cyan-500/30">
            <ShieldCheck className="text-cyan-400" size={26} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight uppercase">KAVI</h1>
            <p className="text-[9px] text-cyan-400/80 font-bold tracking-[0.25em] uppercase">Autonomous Detection</p>
          </div>
        </div>
        
        <h2 className="text-4xl font-bold text-white tracking-tight">
          Your City, <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">Providence</span>
        </h2>
        <div className="flex items-center gap-2 mt-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_#22c55e]" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-white/50">System Online</span>
        </div>
      </motion.div>

      {/* Right: Controls */}
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex gap-3 pointer-events-auto"
      >
        <div className="flex liquid-glass p-1.5 rounded-2xl">
          {/* Time Travel Toggle */}
          <button 
            onClick={() => setShowTimeline(!showTimeline)}
            className={`px-5 py-2.5 rounded-xl transition-all duration-300 flex items-center gap-2 ${
              showTimeline 
                ? "bg-cyan-500 text-black shadow-[0_0_20px_rgba(0,243,255,0.4)]" 
                : "hover:bg-white/5 text-white/60 hover:text-white"
            }`}
          >
            <Clock size={18} />
            <span className="text-xs font-bold uppercase tracking-wider">History</span>
          </button>

          {/* Live Toggle */}
          <button 
            onClick={() => setIsLive(!isLive)}
            className={`px-5 py-2.5 rounded-xl transition-all duration-300 flex items-center gap-2 ${
              isLive 
                ? "bg-red-500 text-white shadow-[0_0_20px_rgba(239,68,68,0.4)]" 
                : "hover:bg-white/5 text-white/60 hover:text-white"
            }`}
          >
            <Radio size={18} className={isLive ? "animate-pulse" : ""} />
            <span className="text-xs font-bold uppercase tracking-wider">Live</span>
          </button>
        </div>
      </motion.div>
    </header>
  );
}
