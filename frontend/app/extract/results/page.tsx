"use client";

import React from "react";
import Link from "next/link";
import { CheckCircle, Image as ImageIcon, Plus, RefreshCcw } from "lucide-react";
import Layout from "@/components/Layout";

export default function ExtractionResultsPage() {
  const extracted = [
    { type: "Top", name: "Graphic shirt", icon: "Item" },
    { type: "Bottom", name: "Lounge pants", icon: "Item" },
    { type: "Accessory", name: "Knit socks", icon: "Item" }
  ];

  return (
    <Layout>
      <div className="w-full bg-white border-4 border-black p-6 space-y-6 shadow-[6px_6px_0px_0px_#000000] animate-in fade-in duration-300 antialiased">
        
        {/* Completion Header */}
        <div className="flex items-center gap-3 border-b-4 border-black pb-4">
          <div className="w-9 h-9 bg-black text-white border-2 border-black flex items-center justify-center shrink-0 shadow-[2px_2px_0px_0px_rgba(0,0,0,0.2)]">
            <CheckCircle className="w-5 h-5 stroke-[3]" />
          </div>
          <div>
            <h2 className="text-xl font-mono font-black tracking-tight text-black">Your items are ready</h2>
            <p className="text-[10px] font-mono font-bold text-zinc-400 tracking-wide mt-0.5">
              We found three items in your photo.
            </p>
          </div>
        </div>

        {/* Fragment List */}
        <div className="space-y-3">
          {extracted.map((item, idx) => (
            <div 
              key={idx} 
              className="flex items-center justify-between p-3 border-2 border-black bg-white shadow-[3px_3px_0px_0px_#000000] hover:bg-zinc-50 hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0px_0px_#000000] transition-all duration-150"
            >
              <div className="flex items-center gap-3">
                {/* Halftone Frame for Icon */}
                <div 
                  className="w-14 h-14 bg-zinc-100 border-2 border-black flex items-center justify-center text-[10px] font-medium text-zinc-400 relative overflow-hidden shrink-0"
                  style={{ 
                    backgroundImage: 'radial-gradient(#e4e4e7 1.5px, transparent 1.5px)', 
                    backgroundSize: '8px 8px' 
                  }}
                >
                  {item.icon}
                </div>
                <div>
                  <p className="text-xs font-mono font-black text-black uppercase tracking-tight line-clamp-1">{item.name}</p>
                  <p className="text-[9px] font-mono font-black text-zinc-400 mt-0.5">{item.type}</p>
                </div>
              </div>

              {/* Fragment Specific Action Nodes */}
              <div className="flex items-center gap-2">
                <button className="p-2 border-2 border-transparent text-zinc-400 hover:text-black hover:border-black hover:bg-white transition-all">
                  <ImageIcon className="w-4 h-4 stroke-[2.5]" />
                </button>
                <button 
                  onClick={() => alert("Added to your wardrobe!")}
                  className="px-3 py-2 bg-black text-white border-2 border-black text-xs font-mono font-black uppercase tracking-wider flex items-center gap-1 shadow-[2px_2px_0px_0px_#27272a] hover:bg-zinc-800 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all"
                >
                  <Plus className="w-3.5 h-3.5 stroke-[3]" /> Add
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Interactive Step Blocks */}
        <div className="grid grid-cols-2 gap-4 pt-2">
          <Link 
            href="/wardrobe" 
            className="bg-black text-white border-2 border-black text-center py-3.5 text-xs font-mono font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_#27272a] hover:bg-zinc-800 hover:shadow-[2px_2px_0px_0px_#27272a] hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1 transition-all"
          >
            Save all items
          </Link>
          <Link 
            href="/extract" 
            className="bg-white text-black border-2 border-black text-center py-3.5 text-xs font-mono font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-[4px_4px_0px_0px_#000000] hover:bg-zinc-50 hover:shadow-[2px_2px_0px_0px_#000000] hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1 transition-all"
          >
            <RefreshCcw className="w-4 h-4 stroke-[3]" /> Choose another photo
          </Link>
        </div>
      </div>
    </Layout>
  );
}
