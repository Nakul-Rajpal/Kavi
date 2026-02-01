"use client";

import { motion } from "framer-motion";
import { Clock, Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

interface TimelineProps {
  timeRange: string;
  onTimeRangeChange: (range: string) => void;
}

// Time range options - exported for use in Map filtering
export const TIME_RANGES = [
  { label: "Last Hour", value: "1h", hours: 1 },
  { label: "Last 6 Hours", value: "6h", hours: 6 },
  { label: "Last 12 Hours", value: "12h", hours: 12 },
  { label: "Last 24 Hours", value: "24h", hours: 24 },
  { label: "Last 7 Days", value: "7d", hours: 168 },
  { label: "All Time", value: "all", hours: -1 },
];

export default function Timeline({ timeRange, onTimeRangeChange }: TimelineProps) {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  const handleRangeSelect = (value: string) => {
    onTimeRangeChange(value);
  };

  const formatDisplayDate = () => {
    const date = new Date(selectedDate);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const changeDate = (delta: number) => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() + delta);
    if (date <= new Date()) {
      setSelectedDate(date.toISOString().split('T')[0]);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className="absolute top-20 right-8 z-[800] pointer-events-auto"
    >
      <div className="liquid-glass rounded-3xl p-6 w-72 border border-white/20 shadow-[0_20px_60px_rgba(0,0,0,0.5)]">
        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
            <Clock size={20} className="text-cyan-400" />
          </div>
          <div>
            <h3 className="text-xs font-black text-cyan-400 uppercase tracking-wider">Time Filter</h3>
            <p className="text-[10px] text-white/40">View historical data</p>
          </div>
        </div>

        {/* Date Selector */}
        <div className="mb-4 p-3 rounded-2xl bg-white/5 border border-white/10">
          <div className="flex items-center justify-between">
            <button 
              onClick={() => changeDate(-1)}
              className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors"
            >
              <ChevronLeft size={18} />
            </button>
            <div className="flex items-center gap-2">
              <Calendar size={14} className="text-cyan-400" />
              <span className="text-sm font-bold text-white">{formatDisplayDate()}</span>
            </div>
            <button 
              onClick={() => changeDate(1)}
              disabled={new Date(selectedDate).toDateString() === new Date().toDateString()}
              className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>

        {/* Time Range Options */}
        <div className="space-y-2">
          {TIME_RANGES.map((range) => (
            <button
              key={range.value}
              onClick={() => handleRangeSelect(range.value)}
              className={`w-full p-3 rounded-xl text-left transition-all flex items-center justify-between group ${
                timeRange === range.value
                  ? "bg-cyan-500/20 border border-cyan-500/50"
                  : "bg-white/5 border border-transparent hover:bg-white/10 hover:border-white/10"
              }`}
            >
              <span className={`text-sm font-semibold ${
                timeRange === range.value ? "text-cyan-400" : "text-white/70 group-hover:text-white"
              }`}>
                {range.label}
              </span>
              {timeRange === range.value && (
                <div className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00f3ff]" />
              )}
            </button>
          ))}
        </div>

        {/* Current Selection Display */}
        <div className="mt-5 pt-5 border-t border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-white/40 uppercase tracking-wider">Showing</span>
            <span className="text-sm font-bold text-white">
              {TIME_RANGES.find(r => r.value === timeRange)?.label || "All Data"}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
