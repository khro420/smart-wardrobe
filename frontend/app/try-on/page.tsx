"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles } from "lucide-react";
import Layout from "@/components/Layout";

export default function TryOnPosePage() {
  const [selectedPose, setSelectedPose] = useState(0);

  const poses = [
    { id: 0, label: "CASUAL // STD", icon: "🧍", desc: "STANDARD STANDING POSE" },
    { id: 1, label: "ACTIVE // DYN", icon: "🏃", desc: "DYNAMIC ACTION FRAME" },
    { id: 2, label: "ZEN // ISO", icon: "🧘", desc: "RELAXED MEDITATIVE STATE" }
  ];

  return (
    <Layout>
      <div className="bg-white border-4 border-black p-6 max-w-xl mx-auto space-y-6 shadow-[6px_6px_0px_0px_#000000] animate-in fade-in duration-300 antialiased">
        
        {/* Back Navigation Link */}
        <Link href="/" className="inline-flex items-center gap-1.5 text-xs font-mono font-black uppercase text-zinc-400 hover:text-black transition-colors group">
          <ArrowLeft className="w-4 h-4 stroke-[3] group-hover:-translate-x-0.5 transition-transform" /> [ BACK_TO_SUGGESTIONS ]
        </Link>

        {/* Header Node */}
        <div className="text-center border-b-4 border-black pb-4">
          <span className="text-2xl filter drop-shadow-[2px_2px_0px_rgba(0,0,0,1)]">👕</span>
          <h2 className="text-2xl font-mono font-black uppercase tracking-tight text-black mt-1">SELECT_TRY-ON_POSE //</h2>
        </div>

        {/* Matrix Canvas Interface Container */}
        <div 
          className="w-full aspect-square bg-zinc-50 border-2 border-black flex flex-col items-center justify-center p-6 relative overflow-hidden"
          style={{ 
            backgroundImage: 'radial-gradient(#e4e4e7 1.5px, transparent 1.5px)', 
            backgroundSize: '14px 14px' 
          }}
        >
          {/* Active Preview Status Matrix */}
          <div className="text-center space-y-4">
            <div className="text-7xl select-none filter drop-shadow-[3px_3px_0px_rgba(0,0,0,1)] animate-pulse duration-1000">
              {poses[selectedPose].icon}
            </div>
            <p className="text-[10px] font-mono font-black bg-black text-white px-3 py-1 border border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,1)] uppercase tracking-widest">
              {poses[selectedPose].desc}
            </p>
          </div>

          {/* Core Brutalist Button */}
          <button 
            onClick={() => {
              alert("Generating virtual model dressing render output...");
            }}
            className="absolute bottom-6 bg-black text-white border-2 border-black font-mono text-xs font-black tracking-widest uppercase px-6 py-3 flex items-center gap-2 shadow-[4px_4px_0px_0px_#27272a] hover:shadow-[2px_2px_0px_0px_#27272a] hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1 transition-all"
          >
            <Sparkles className="w-4 h-4 text-white stroke-[2.5]" /> INITIALIZE_RENDER
          </button>
        </div>

        {/* Profile Selector Stack */}
        <div className="space-y-3 pt-2">
          <p className="text-[10px] font-mono font-black text-zinc-400 uppercase tracking-widest">// AVAILABLE_PROFILES</p>
          <div className="grid grid-cols-3 gap-4">
            {poses.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPose(p.id)}
                className={`p-4 border-2 border-black text-center flex flex-col items-center justify-center gap-2 transition-all cursor-crosshair ${
                  selectedPose === p.id 
                    ? "bg-black text-white shadow-[4px_4px_0px_0px_#27272a] translate-x-0.5 translate-y-0.5" 
                    : "bg-white text-black hover:bg-zinc-100 shadow-[3px_3px_0px_0px_#000000] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
                }`}
              >
                <span className="text-2xl filter drop-shadow-[1px_1px_0px_rgba(0,0,0,0.5)]">{p.icon}</span>
                <span className="text-[9px] font-mono font-black uppercase tracking-tight block leading-none">{p.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  );
}