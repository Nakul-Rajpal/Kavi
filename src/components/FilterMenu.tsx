"use client";

import { Filter, ChevronDown, Search, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Issue type definitions with emojis and colors
export const ISSUE_TYPES = [
  { id: "pothole", name: "Potholes", emoji: "🕳️", color: "text-red-400", bg: "bg-red-400/10" },
  { id: "damaged_light", name: "Street Lights", emoji: "💡", color: "text-yellow-400", bg: "bg-yellow-400/10" },
  { id: "fallen_tree", name: "Obstructions", emoji: "🌳", color: "text-green-400", bg: "bg-green-400/10" },
  { id: "faded_lines", name: "Faded Markings", emoji: "🛣️", color: "text-blue-400", bg: "bg-blue-400/10" },
] as const;

export type IssueTypeId = typeof ISSUE_TYPES[number]["id"];

interface FilterMenuProps {
  activeFilters: Set<IssueTypeId>;
  onFilterChange: (filters: Set<IssueTypeId>) => void;
}

export default function FilterMenu({ activeFilters, onFilterChange }: FilterMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleFilter = (typeId: IssueTypeId) => {
    const newFilters = new Set(activeFilters);
    if (newFilters.has(typeId)) {
      newFilters.delete(typeId);
    } else {
      newFilters.add(typeId);
    }
    onFilterChange(newFilters);
  };

  const resetFilters = () => {
    onFilterChange(new Set());
  };

  const activeCount = activeFilters.size;

  return (
    <div className="absolute bottom-16 right-16 z-[500] pointer-events-auto flex flex-col items-end gap-6">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ scale: 0.8, opacity: 0, y: 20, filter: "blur(10px)" }}
            animate={{ scale: 1, opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ scale: 0.8, opacity: 0, y: 20, filter: "blur(10px)" }}
            className="w-80 liquid-glass rounded-[40px] p-8 shadow-[0_40px_80px_rgba(0,0,0,0.6)] border border-white/20"
          >
            <div className="flex items-center justify-between mb-8">
              <div className="text-[10px] text-cyan-400 uppercase tracking-[0.3em] font-black">
                Data Filters {activeCount > 0 && `(${activeCount})`}
              </div>
              <SlidersHorizontal size={14} className="text-white/40" />
            </div>

            <div className="space-y-3">
              {ISSUE_TYPES.map((type) => {
                const isActive = activeFilters.has(type.id);
                return (
                  <button 
                    key={type.id}
                    onClick={() => toggleFilter(type.id)}
                    className={`w-full flex items-center justify-between p-4 rounded-3xl transition-all group border cursor-pointer ${
                      isActive 
                        ? "bg-white/10 border-cyan-400/50" 
                        : "hover:bg-white/5 border-transparent hover:border-white/10"
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-2xl ${type.bg} flex items-center justify-center transition-transform group-hover:scale-110`}>
                        <span className="text-xl">{type.emoji}</span>
                      </div>
                      <span className={`text-sm font-bold ${isActive ? "text-white" : "text-white/80 group-hover:text-white"}`}>
                        {type.name}
                      </span>
                    </div>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                      isActive ? "border-cyan-400 bg-cyan-400" : "border-white/10 group-hover:border-cyan-400/50"
                    }`}>
                      {isActive && (
                        <svg className="w-3 h-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mt-8 pt-8 border-t border-white/10 space-y-4">
              <button 
                onClick={resetFilters}
                className={`w-full py-4 rounded-2xl text-[10px] font-black tracking-widest transition-all uppercase ${
                  activeCount > 0 
                    ? "bg-red-500/20 text-red-400 hover:bg-red-500/30" 
                    : "bg-white/5 text-white/40 hover:text-white hover:bg-white/10"
                }`}
              >
                {activeCount > 0 ? `Clear ${activeCount} Filter${activeCount > 1 ? 's' : ''}` : "No Active Filters"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`w-20 h-20 rounded-[30px] flex items-center justify-center transition-all duration-500 shadow-2xl border border-white/20 group overflow-hidden relative ${
          isOpen 
            ? "bg-cyan-500 text-black shadow-[0_0_40px_rgba(0,243,255,0.6)] rotate-90" 
            : activeCount > 0
              ? "bg-cyan-500/20 text-cyan-400 border-cyan-400/50 hover:scale-110"
              : "liquid-glass text-white hover:scale-110 hover:shadow-[0_0_30px_rgba(0,243,255,0.2)]"
        }`}
      >
        {/* Active filter count badge */}
        {activeCount > 0 && !isOpen && (
          <div className="absolute -top-1 -right-1 w-6 h-6 bg-cyan-500 rounded-full flex items-center justify-center text-black text-xs font-black">
            {activeCount}
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-tr from-cyan-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div key="close" initial={{ rotate: -90 }} animate={{ rotate: 0 }} exit={{ rotate: 90 }}>
              <ChevronDown size={32} strokeWidth={3} />
            </motion.div>
          ) : (
            <motion.div key="filter" initial={{ rotate: 90 }} animate={{ rotate: 0 }} exit={{ rotate: -90 }}>
              <Filter size={32} strokeWidth={2.5} />
            </motion.div>
          )}
        </AnimatePresence>
      </button>
    </div>
  );
}
