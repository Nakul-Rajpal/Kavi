"use client";

import { motion } from "framer-motion";

interface TimelineProps {
  currentTime: string;
  setCurrentTime: (time: string) => void;
}

export default function Timeline({ currentTime, setCurrentTime }: TimelineProps) {
  const times = [
    "08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
    "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
  ];

  const currentIndex = times.indexOf(currentTime);

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 50, opacity: 0 }}
      className="absolute bottom-16 left-1/2 -translate-x-1/2 w-[800px] z-[500] pointer-events-auto"
    >
      <div className="liquid-glass rounded-[40px] p-10 flex flex-col gap-8 border border-white/20 shadow-[0_0_80px_rgba(0,0,0,0.6)]">
        <div className="flex justify-between items-end px-2">
          <div>
            <h3 className="text-[10px] font-black text-cyan-400 tracking-[0.3em] uppercase mb-1">Temporal Archive</h3>
            <p className="text-sm text-white/60 font-medium">Scrubbing through last 24h of telemetry data</p>
          </div>
          <div className="text-4xl font-black font-mono text-white tracking-tighter">
            {currentTime}
          </div>
        </div>

        <div className="relative h-20 flex items-center group">
          {/* Timeline Track */}
          <div className="absolute inset-x-0 h-2 bg-white/5 rounded-full overflow-hidden">
            <motion.div 
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500 to-blue-500"
              animate={{ width: `${(currentIndex / (times.length - 1)) * 100}%` }}
            />
          </div>
          
          {/* Timeline Marks */}
          <div className="absolute inset-x-0 flex justify-between px-1">
            {times.map((t, i) => (
              <div key={t} className="flex flex-col items-center gap-3">
                <div 
                  className={`w-[2px] h-4 rounded-full transition-all duration-500 ${
                    i <= currentIndex ? "bg-cyan-400" : "bg-white/10"
                  }`} 
                />
                <span className={`text-[8px] font-black font-mono transition-all duration-500 ${
                  i === currentIndex ? "text-cyan-400 scale-125" : "text-white/20"
                }`}>
                  {t.split(' ')[0]}
                </span>
              </div>
            ))}
          </div>

          {/* Slider Input */}
          <input
            type="range"
            min="0"
            max={times.length - 1}
            step="1"
            value={currentIndex}
            onChange={(e) => setCurrentTime(times[parseInt(e.target.value)])}
            className="absolute inset-x-0 w-full h-full opacity-0 cursor-pointer z-20"
          />

          {/* Custom Thumb (Visual) */}
          <motion.div 
            className="absolute w-10 h-10 bg-white rounded-2xl shadow-[0_0_30px_rgba(0,243,255,0.6)] border-4 border-cyan-400 pointer-events-none flex items-center justify-center overflow-hidden"
            animate={{ 
              left: `${(currentIndex / (times.length - 1)) * 100}%` 
            }}
            style={{ x: "-50%" }}
          >
            <div className="w-full h-full bg-gradient-to-br from-white to-cyan-100 flex items-center justify-center">
              <div className="w-1 h-4 bg-cyan-500/30 rounded-full" />
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
