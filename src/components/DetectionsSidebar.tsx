"use client";

import { AlertTriangle, Lightbulb, Droplets, Trash2, AlertCircle } from "lucide-react";

const detections = [
  { id: 1, type: "pothole", label: "Pothole", location: "Kennedy Plaza", color: "#FF3B30", confidence: 94, time: "2h ago", icon: AlertTriangle },
  { id: 2, type: "light", label: "Broken Light", location: "Providence Place", color: "#FFD60A", confidence: 87, time: "5h ago", icon: Lightbulb },
  { id: 3, type: "flood", label: "Standing Water", location: "Waterplace Park", color: "#00F3FF", confidence: 91, time: "1h ago", icon: Droplets },
  { id: 4, type: "debris", label: "Road Debris", location: "Brown University", color: "#30D158", confidence: 78, time: "8h ago", icon: Trash2 },
  { id: 5, type: "sign", label: "Damaged Sign", location: "Federal Hill", color: "#FF9F0A", confidence: 85, time: "3h ago", icon: AlertCircle },
];

export default function DetectionsSidebar() {
  return (
    <div className="absolute left-8 top-40 bottom-8 w-80 z-[600] pointer-events-auto flex flex-col gap-4 overflow-y-auto pr-2">
      <div className="liquid-glass rounded-3xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-black text-cyan-400 uppercase tracking-[0.2em]">Active Detections</h3>
          <span className="text-xs font-bold text-white/40">{detections.length} issues</span>
        </div>
        
        <div className="space-y-3">
          {detections.map((d) => {
            const Icon = d.icon;
            return (
              <div
                key={d.id}
                className="group p-4 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 transition-all cursor-pointer"
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ 
                      backgroundColor: `${d.color}15`,
                      boxShadow: `0 0 20px ${d.color}20`
                    }}
                  >
                    <Icon size={20} style={{ color: d.color }} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-bold text-white text-sm truncate">{d.label}</span>
                      <span 
                        className="text-xs font-black px-2 py-0.5 rounded-full"
                        style={{ 
                          backgroundColor: `${d.color}20`,
                          color: d.color
                        }}
                      >
                        {d.confidence}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-white/50 truncate">{d.location}</span>
                      <span className="text-xs text-white/30">{d.time}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stats Card */}
      <div className="liquid-glass rounded-3xl p-6">
        <h3 className="text-xs font-black text-cyan-400 uppercase tracking-[0.2em] mb-4">Drone Status</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-white/5">
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Coverage</div>
            <div className="text-2xl font-black text-white">72<span className="text-sm opacity-50">%</span></div>
          </div>
          <div className="p-4 rounded-2xl bg-white/5">
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Battery</div>
            <div className="text-2xl font-black text-green-400">84<span className="text-sm opacity-50">%</span></div>
          </div>
          <div className="p-4 rounded-2xl bg-white/5">
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Speed</div>
            <div className="text-2xl font-black text-cyan-400">12<span className="text-sm opacity-50">km/h</span></div>
          </div>
          <div className="p-4 rounded-2xl bg-white/5">
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Altitude</div>
            <div className="text-2xl font-black text-purple-400">45<span className="text-sm opacity-50">m</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
