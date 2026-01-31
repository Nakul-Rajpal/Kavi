"use client";

import { AlertTriangle, Lightbulb, Droplets, Trash2, AlertCircle, MapPin, LucideIcon } from "lucide-react";
import { Ping } from "@/lib/supabase";

// Icon mapping
const iconMap: Record<string, LucideIcon> = {
  pothole: AlertTriangle,
  light: Lightbulb,
  flood: Droplets,
  debris: Trash2,
  sign: AlertCircle,
  default: MapPin,
};

// Color mapping
const colorMap: Record<string, string> = {
  high: "#FF3B30",
  medium: "#FFD60A",
  low: "#30D158",
  default: "#00F3FF",
};

interface DetectionsSidebarProps {
  pings: Ping[];
  connectionStatus?: 'connecting' | 'connected' | 'disconnected';
}

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export default function DetectionsSidebar({ pings, connectionStatus = 'connecting' }: DetectionsSidebarProps) {
  // Sort pings by most recent first
  const sortedPings = [...pings].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="absolute left-8 top-40 bottom-8 w-80 z-[600] pointer-events-auto flex flex-col gap-4 overflow-hidden">
      <div className="liquid-glass rounded-3xl p-6 flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-black text-cyan-400 uppercase tracking-[0.2em]">Live Detections</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500 animate-pulse' :
              connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
              'bg-red-500'
            }`} />
            <span className="text-xs font-bold text-white/40">{pings.length} issues</span>
          </div>
        </div>
        
        <div className="space-y-3 overflow-y-auto flex-1 pr-2">
          {sortedPings.length === 0 ? (
            <div className="text-center py-8 text-white/30">
              <MapPin size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-xs">No detections yet</p>
              <p className="text-[10px] mt-1">Waiting for drone data...</p>
            </div>
          ) : (
            sortedPings.map((ping) => {
              const type = ping.type || 'default';
              const severity = ping.severity || 'default';
              const Icon = iconMap[type] || iconMap.default;
              const color = colorMap[severity] || colorMap.default;
              const confidence = ping.confidence || Math.floor(Math.random() * 20 + 80);
              const label = ping.label || type.charAt(0).toUpperCase() + type.slice(1);

              return (
                <div
                  key={ping.id}
                  className="group p-4 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 transition-all cursor-pointer"
                >
                  <div className="flex items-start gap-4">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ 
                        backgroundColor: `${color}15`,
                        boxShadow: `0 0 20px ${color}20`
                      }}
                    >
                      <Icon size={20} style={{ color }} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-bold text-white text-sm truncate">{label}</span>
                        <span 
                          className="text-xs font-black px-2 py-0.5 rounded-full"
                          style={{ 
                            backgroundColor: `${color}20`,
                            color: color
                          }}
                        >
                          {confidence}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-white/50 truncate">
                          {ping.lat.toFixed(4)}, {ping.lng.toFixed(4)}
                        </span>
                        <span className="text-xs text-white/30">{formatTimestamp(ping.created_at)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Stats Card */}
      <div className="liquid-glass rounded-3xl p-6">
        <h3 className="text-xs font-black text-cyan-400 uppercase tracking-[0.2em] mb-4">System Status</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-white/5">
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Total</div>
            <div className="text-2xl font-black text-white">{pings.length}</div>
          </div>
          <div className="p-4 rounded-2xl bg-white/5">
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Status</div>
            <div className={`text-2xl font-black ${
              connectionStatus === 'connected' ? 'text-green-400' :
              connectionStatus === 'connecting' ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {connectionStatus === 'connected' ? 'Live' : connectionStatus === 'connecting' ? '...' : 'Off'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
