"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, ArrowUpRight, Sparkles, Bookmark } from "lucide-react";
import Layout from "@/components/Layout";

const SUGGESTIONS = [
  { id: "s1", category: "SYS.01 // TREND", prompt: "FEELIN SPORTY?", tag: "AIA GYM CORE", icon: "⚡" },
  { id: "s2", category: "SYS.02 // WEATHER", prompt: "CHILLY MORNINGS", tag: "COZY KNIT HEAVY", icon: "☁️" },
  { id: "s3", category: "SYS.03 // EDITORIAL", prompt: "NIGHT OUT BLING", tag: "GLAM LUXE METALLIC", icon: "✨" },
];

const RECENT_OUTFITS = [
  { id: "r1", date: "23.06.26", items: ["SHIRT", "SHORTS", "CAP"], label: "STRIPED RESORT SET", icons: "👔🩳" },
  { id: "r2", date: "24.06.26", items: ["BLAZER", "TROUSERS"], label: "LINEN COMBO RAW", icons: "🧥👖" },
];

export default function HomePage() {
  return (
    <Layout>
      <div className="space-y-14 animate-in fade-in duration-300 antialiased">
        
        {/* Distressed Brutalist Header Section */}
        <div className="border-4 border-black p-6 bg-black text-white relative overflow-hidden">
          {/* Decorative background glitch artifacts */}
          <div className="absolute top-0 right-4 text-[70px] opacity-[0.03] font-mono select-none font-black pointer-events-none">
            AURA_v1.0
          </div>
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.4em] font-mono">[ CURATED_INTELLIGENCE ]</p>
          <h1 className="text-4xl font-black tracking-tighter uppercase mt-1 font-sans italic">
            DAILY_BLUEPRINT.EXE
          </h1>
        </div>

        {/* Suggestions Section */}
        <div>
          <div className="flex items-center justify-between mb-6 border-b-2 border-dashed border-zinc-400 pb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-black animate-pulse" />
              <h2 className="text-sm font-black text-black uppercase tracking-[0.25em] font-mono">GEN_LOOKBOOKS //</h2>
            </div>
            <span className="text-[10px] font-mono font-bold bg-zinc-200 px-2 py-0.5 text-zinc-700">3_LOADED</span>
          </div>

          <div className="flex gap-6 overflow-x-auto pb-6 no-scrollbar snap-x">
            {SUGGESTIONS.map((s) => (
              <div 
                key={s.id} 
                className="min-w-[290px] sm:min-w-[340px] snap-start bg-white border-4 border-black p-6 h-[410px] flex flex-col justify-between relative shadow-[4px_4px_0px_0px_#000000] hover:shadow-[8px_8px_0px_0px_#000000] hover:-translate-x-0.5 hover:-translate-y-0.5 transition-all duration-200 group cursor-crosshair"
              >
                {/* Harsh Header Label */}
                <div className="flex items-center justify-between w-full border-b-2 border-black pb-3">
                  <span className="text-[11px] font-mono font-black tracking-widest text-black">
                    {s.category}
                  </span>
                  <span className="text-xs font-mono font-bold text-zinc-400 group-hover:text-black transition-colors">#{s.id}</span>
                </div>
                
                {/* Stark High Contrast Asset Canvas with Inline Grid Matrix */}
                <div 
                  className="w-full h-36 border-2 border-black mt-4 flex flex-col items-center justify-center relative overflow-hidden bg-zinc-100" 
                  style={{ 
                    backgroundImage: 'radial-gradient(#e4e4e7 1.5px, transparent 1.5px)', 
                    backgroundSize: '12px 12px' 
                  }}
                >
                  <span className="text-5xl group-hover:scale-110 group-hover:rotate-3 transition-transform duration-200 ease-out z-10 filter drop-shadow-[2px_2px_0px_rgba(0,0,0,1)]">
                    {s.icon}
                  </span>
                  <p className="text-[9px] font-mono font-black tracking-widest uppercase mt-4 bg-black text-white px-3 py-1 border border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,1)] z-10">
                    {s.tag}
                  </p>
                </div>

                {/* Bottom Action Stack */}
                <div className="space-y-4 pt-3">
                  <h3 className="text-xl font-black text-black tracking-tight uppercase font-mono">
                    {s.prompt}
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <Link 
                      href="/try-on" 
                      className="bg-black text-white border-2 border-black hover:bg-zinc-800 text-center py-2.5 text-xs font-mono font-black tracking-widest uppercase transition-all flex items-center justify-center gap-1 shadow-[2px_2px_0px_0px_rgba(0,0,0,0.2)] hover:shadow-[4px_4px_0px_0px_#000000] hover:-translate-y-0.5"
                    >
                      TRY_ON <ArrowUpRight className="w-4 h-4 stroke-[3]" />
                    </Link>
                    <button 
                      onClick={() => alert("Saved Lookbook to Wardrobe!")} 
                      className="bg-white border-2 border-black text-black hover:bg-black hover:text-white py-2.5 text-xs font-mono font-black tracking-widest uppercase transition-all flex items-center justify-center gap-1"
                    >
                      <Bookmark className="w-4 h-4 stroke-[3]" /> SAVE
                    </button>
                  </div>
                </div>
              </div>
            ))}
            
            {/* View More Punk Placeholder Node */}
            <div className="min-w-[130px] bg-zinc-100 border-4 border-dashed border-zinc-400 hover:border-black flex flex-col items-center justify-center text-zinc-400 hover:text-black transition-all gap-2 cursor-pointer group shadow-[4px_4px_0px_0px_rgba(0,0,0,0.05)] hover:shadow-[4px_4px_0px_0px_#000000]">
              <div className="p-2 border-2 border-zinc-400 group-hover:border-black bg-white transition-colors">
                <ChevronRight className="w-5 h-5 stroke-[3]" />
              </div>
              <span className="text-[10px] font-black uppercase tracking-widest font-mono">MORE_ARCH</span>
            </div>
          </div>
        </div>

        {/* Recent Outfits Section */}
        <div>
          <div className="flex justify-between items-center mb-6 border-b-2 border-dashed border-zinc-400 pb-2">
            <h2 className="text-sm font-black text-black uppercase tracking-[0.25em] font-mono">RECENT_ITERATIONS //</h2>
            <Link href="/wardrobe" className="text-xs font-black text-zinc-500 hover:text-black flex items-center gap-1 tracking-widest font-mono transition-colors">
              [VIEW_ALL] <ChevronRight className="w-4 h-4 stroke-[3]" />
            </Link>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {RECENT_OUTFITS.map((r) => (
              <div 
                key={r.id} 
                className="bg-white border-4 border-black p-5 flex items-center justify-between h-36 transition-all duration-200 shadow-[4px_4px_0px_0px_#000000] hover:shadow-[6px_6px_0px_0px_#000000] hover:-translate-x-0.5 hover:-translate-y-0.5 group cursor-pointer"
              >
                <div className="flex flex-col justify-between h-full space-y-3">
                  <div>
                    <span className="text-[10px] font-mono font-bold text-zinc-400 tracking-wider block">// RELEASE_{r.date}</span>
                    <p className="text-base font-black text-black uppercase tracking-tight font-mono">
                      {r.label}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {r.items.map((i, index) => (
                      <span key={index} className="text-[9px] bg-black text-white border border-black px-2 py-0.5 font-mono font-black uppercase tracking-wider">
                        {i}
                      </span>
                    ))}
                  </div>
                </div>
                
                {/* Brutalist Avatar Square */}
                <div className="w-20 h-20 bg-zinc-100 border-2 border-black flex items-center justify-center text-4xl shrink-0 group-hover:bg-zinc-200 transition-colors shadow-[2px_2px_0px_0px_#000000]">
                  {r.icons}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </Layout>
  );
}