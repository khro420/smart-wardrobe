"use client";

import React from "react";
import Link from "next/link";
import { UploadCloud } from "lucide-react";
import Layout from "@/components/Layout";

export default function ExtractLandingPage() {
  return (
    <Layout>
      <div className="w-full bg-white border-4 border-black p-6 md:p-8 space-y-8 shadow-[6px_6px_0px_0px_#000000] animate-in fade-in duration-300 antialiased">
        
        {/* Brutalist Section Header */}
        <div className="text-center border-b-4 border-black pb-4">
          <h2 className="text-2xl font-mono font-black tracking-tight text-black">Add an outfit</h2>
          <p className="text-[11px] font-mono font-bold text-zinc-400 tracking-wide mt-1">
            We’ll identify the clothing in your photo and add it to your wardrobe.
          </p>
        </div>

        {/* Link Dropzone Area with Inline Grid Matrix Background */}
        <Link 
          href="/extract/results" 
          className="border-4 border-dashed border-zinc-400 hover:border-black flex flex-col items-center justify-center gap-5 p-8 cursor-crosshair bg-zinc-50 text-center transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,0.05)] hover:shadow-[4px_4px_0px_0px_#000000] group relative overflow-hidden"
          style={{ 
            backgroundImage: 'radial-gradient(#e4e4e7 1.5px, transparent 1.5px)', 
            backgroundSize: '14px 14px' 
          }}
        >
          <div className="w-14 h-14 bg-white border-2 border-black flex items-center justify-center text-black shadow-[3px_3px_0px_0px_#000000] group-hover:-translate-x-0.5 group-hover:-translate-y-0.5 transition-transform z-10">
            <UploadCloud className="w-6 h-6 stroke-[2.5]" />
          </div>
          
          <div className="z-10">
            <p className="text-sm font-mono font-black tracking-wide text-black">Choose a photo</p>
            <p className="text-[10px] font-mono font-bold text-zinc-400 mt-1">
              Upload a photo to identify the items in it.
            </p>
          </div>
          
          {/* Rules Validation Inside Dropzone */}
          <div className="w-full max-w-xs bg-white border-2 border-black p-4 text-left space-y-2 z-10 shadow-[2px_2px_0px_0px_#000000]">
            <p className="text-[9px] font-mono font-black text-zinc-400 tracking-wide">For the best results</p>
            <ul className="text-[11px] font-mono font-black text-black space-y-1.5 list-none">
              <li>• Use clear, even lighting</li>
              <li>• Keep the outfit visible</li>
              <li>• Include one person per photo</li>
            </ul>
          </div>
        </Link>

        {/* Acceptance Profiles Grid Section */}
        <div className="space-y-3 pt-2">
          <h4 className="text-[10px] font-mono font-black text-zinc-400 tracking-wide">Photo guide</h4>
          <div className="grid grid-cols-3 gap-4">
            
            {/* Fail Condition Profile 1 */}
            <div 
              className="aspect-square bg-zinc-50 border-2 border-black relative flex flex-col items-center justify-center text-center p-2 shadow-[2px_2px_0px_0px_#000000]"
              style={{ backgroundImage: 'radial-gradient(#f4f4f5 1px, transparent 1px)', backgroundSize: '8px 8px' }}
            >
              <span className="mb-1 text-[10px] font-medium text-zinc-400">Photo</span>
              <span className="absolute top-2 left-2 w-5 h-5 bg-black text-white border border-white flex items-center justify-center text-[10px] font-mono font-black shadow-[1px_1px_0px_0px_#000000]">X</span>
              <p className="text-[9px] font-mono font-black text-zinc-400 mt-1 leading-none">Too blurry</p>
            </div>
            
            {/* Fail Condition Profile 2 */}
            <div 
              className="aspect-square bg-zinc-50 border-2 border-black relative flex flex-col items-center justify-center text-center p-2 shadow-[2px_2px_0px_0px_#000000]"
              style={{ backgroundImage: 'radial-gradient(#f4f4f5 1px, transparent 1px)', backgroundSize: '8px 8px' }}
            >
              <span className="mb-1 text-[10px] font-medium text-zinc-400">Photo</span>
              <span className="absolute top-2 left-2 w-5 h-5 bg-black text-white border border-white flex items-center justify-center text-[10px] font-mono font-black shadow-[1px_1px_0px_0px_#000000]">X</span>
              <p className="text-[9px] font-mono font-black text-zinc-400 mt-1 leading-none">Face covered</p>
            </div>
            
            {/* Pass Condition Profile 3 */}
            <div 
              className="aspect-square bg-white border-2 border-black relative flex flex-col items-center justify-center text-center p-2 shadow-[4px_4px_0px_0px_#000000]"
              style={{ backgroundImage: 'radial-gradient(#e4e4e7 1.5px, transparent 1.5px)', backgroundSize: '10px 10px' }}
            >
              <span className="mb-1 text-[10px] font-medium text-zinc-400">Photo</span>
              <span className="absolute top-2 left-2 w-5 h-5 bg-white text-black border border-black flex items-center justify-center text-[10px] font-mono font-black shadow-[1px_1px_0px_0px_#000000]">OK</span>
              <p className="text-[9px] font-mono font-black text-black mt-1 leading-none">Full outfit</p>
            </div>

          </div>
        </div>
      </div>
    </Layout>
  );
}
