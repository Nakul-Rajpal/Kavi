"use client";

import { Filter, ChevronDown, AlertTriangle, Lightbulb, Trash2, Search, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function FilterMenu() {
  const [isOpen, setIsOpen] = useState(false);

  const categories = [
    { name: "Potholes", icon: AlertTriangle, color: "text-red-400", bg: "bg-red-400/10" },
    { name: "Streetlights", icon: Lightbulb, color: "text-yellow-400", bg: "bg-yellow-400/10" },
    { name: "Debris", icon: Trash2, color: "text-green-400", bg: "bg-green-400/10" },
  ];

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
              <div className="text-[10px] text-cyan-400 uppercase tracking-[0.3em] font-black">Data Filters</div>
              <SlidersHorizontal size={14} className="text-white/40" />
            </div>

            <div className="space-y-3">
              {categories.map((cat) => (
                <button 
                  key={cat.name}
                  className="w-full flex items-center justify-between p-4 rounded-3xl hover:bg-white/5 transition-all group border border-transparent hover:border-white/10"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-2xl ${cat.bg} flex items-center justify-center transition-transform group-hover:scale-110`}>
                      <cat.icon size={20} className={cat.color} />
                    </div>
                    <span className="text-sm font-bold text-white/80 group-hover:text-white">{cat.name}</span>
                  </div>
                  <div className="w-5 h-5 rounded-full border-2 border-white/10 flex items-center justify-center group-hover:border-cyan-400/50 transition-colors">
                    <div className="w-2 h-2 rounded-full bg-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-8 pt-8 border-t border-white/10 space-y-4">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20" size={16} />
                <input 
                  type="text" 
                  placeholder="Search tickets..." 
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-cyan-400/50 transition-colors"
                />
              </div>
              <button className="w-full py-4 rounded-2xl bg-white/5 text-[10px] font-black tracking-widest text-white/40 hover:text-white hover:bg-white/10 transition-all uppercase">
                Reset All Filters
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
            : "liquid-glass text-white hover:scale-110 hover:shadow-[0_0_30px_rgba(0,243,255,0.2)]"
        }`}
      >
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
