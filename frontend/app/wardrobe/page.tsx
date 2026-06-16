"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Search, Filter, Heart, Plus, X, Trash2, Cpu, ShieldAlert } from "lucide-react";
import Layout from "@/components/Layout";

// Realistic taxonomy model based exclusively on Computer Vision / Image Segmentation outputs
const INITIAL_GARMENTS = [
  { 
    id: 1, 
    name: "Cashmere Crew", 
    category: "Tops", 
    favorite: true, 
    img: "🧥",
    specs: {
      detectedOn: "2026-03-14",
      visualCategory: "Outerwear // Knitwear",
      inferredFit: "Oversized Silhouette",
      dominantPattern: "Solid Color // Matte Finish",
    },
    // Computer Vision Extracted Feature Vectors for AI Recommender Pairing Matrix
    aiTags: {
      primaryColorHex: "#1C1C1C",
      secondaryColorHex: "NONE_DETECTED",
      detectedSubGenres: ["MINIMALIST", "STREETWEAR_VOLUME", "ARCHIVE"],
      inferredSeasonality: ["AUTUMN", "WINTER"],
      layeringPriorityIndex: "MID_TO_OUTER", // Inferred from structural thickness
      estimatedTextureDensity: "HEAVYWEIGHT",
      vibeSignature: "RELAXED_DROP_SHOULDER"
    }
  },
  { 
    id: 2, 
    name: "White Tee", 
    category: "Tops", 
    favorite: true, 
    img: "👕",
    specs: {
      detectedOn: "2026-01-22",
      visualCategory: "T-Shirts // Base Layers",
      inferredFit: "Regular / Straight Fit",
      dominantPattern: "Plain Solid",
    },
    aiTags: {
      primaryColorHex: "#FFFFFF",
      secondaryColorHex: "NONE_DETECTED",
      detectedSubGenres: ["CORE_ESSENTIALS", "MINIMALIST"],
      inferredSeasonality: ["SPRING", "SUMMER"],
      layeringPriorityIndex: "BASE_LAYER",
      estimatedTextureDensity: "LIGHTWEIGHT",
      vibeSignature: "BOX_STANDARD"
    }
  },
  { 
    id: 3, 
    name: "67 Tee", 
    category: "Tops", 
    favorite: false, 
    img: "🎽",
    specs: {
      detectedOn: "2025-11-05",
      visualCategory: "Graphic Tops",
      inferredFit: "Cropped // Wide",
      dominantPattern: "Distressed Screenprint Front Graphic",
    },
    aiTags: {
      primaryColorHex: "#4B5366",
      secondaryColorHex: "#EAEAEA",
      detectedSubGenres: ["VINTAGE_STREETWEAR", "GRAPHIC_HYPE"],
      inferredSeasonality: ["SPRING", "SUMMER"],
      layeringPriorityIndex: "BASE_LAYER",
      estimatedTextureDensity: "MIDWEIGHT",
      vibeSignature: "CROPPED_SQUARE"
    }
  },
  { 
    id: 4, 
    name: "Doggy Tee", 
    category: "Tops", 
    favorite: false, 
    img: "🦮",
    specs: {
      detectedOn: "2026-05-19",
      visualCategory: "Graphic Tops",
      inferredFit: "Relaxed Boxy Fit",
      dominantPattern: "Centered Illustration Print",
    },
    aiTags: {
      primaryColorHex: "#FFFDD0",
      secondaryColorHex: "#8B4513",
      detectedSubGenres: ["STREETWEAR", "HYPEBEAST"],
      inferredSeasonality: ["SPRING", "SUMMER"],
      layeringPriorityIndex: "BASE_LAYER",
      estimatedTextureDensity: "MIDWEIGHT",
      vibeSignature: "OVERSIZED_STREET_DROP"
    }
  },
];

type GarmentType = typeof INITIAL_GARMENTS[0];

export default function WardrobePage() {
  const [garments, setGarments] = useState<GarmentType[]>(INITIAL_GARMENTS);
  const [activeTab, setActiveTab] = useState<"Outfits" | "Garments">("Garments");
  const [filter, setFilter] = useState("All Items");
  const [search, setSearch] = useState("");
  
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

  const selectedItem = garments.find(item => item.id === selectedItemId) || null;

  const displayItems = garments.filter(g => {
    const matchCat = filter === "All Items" || g.category === filter;
    const matchSearch = g.name.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  const handleDeleteItem = (id: number) => {
    setGarments(prev => prev.filter(item => item.id !== id));
    setSelectedItemId(null);
    setIsDeleteConfirmOpen(false);
  };

  return (
    <Layout>
      <div className="space-y-6 animate-in fade-in duration-300 antialiased">
        
        {/* Switcher Tabs */}
        <div className="flex bg-white border-4 border-black p-1 w-full max-w-xs mx-auto shadow-[4px_4px_0px_0px_#000000]">
          {(["Outfits", "Garments"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 text-center py-2 text-xs font-mono font-black uppercase transition-all ${
                activeTab === tab ? "bg-black text-white" : "text-zinc-400 hover:text-black"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Search Strip */}
        <div className="flex flex-col sm:flex-row gap-3 bg-white p-4 border-4 border-black shadow-[4px_4px_0px_0px_#000000]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-black absolute left-3.5 top-1/2 -translate-y-1/2 stroke-[3]" />
            <input 
              type="text" 
              placeholder="SEARCH_YOUR_ARCHIVE..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-zinc-50 border-2 border-black font-mono text-xs font-bold uppercase pl-10 pr-4 py-2.5 placeholder-zinc-400 focus:outline-hidden"
            />
          </div>
          <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
            {["All Items", "Tops", "Bottoms"].map((cat) => (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`px-4 py-2 border-2 border-black text-xs font-mono font-black uppercase whitespace-nowrap transition-all shadow-[2px_2px_0px_0px_#000000] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none ${
                  filter === cat ? "bg-black text-white" : "bg-white text-black hover:bg-zinc-100"
                }`}
              >
                {cat}
              </button>
            ))}
            <button className="p-2 bg-white border-2 border-black text-black hover:bg-black hover:text-white transition-colors shadow-[2px_2px_0px_0px_#000000]">
              <Filter className="w-4 h-4 stroke-[3]" />
            </button>
          </div>
        </div>

        {/* Wardrobe Grid */}
        {activeTab === "Garments" ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
            {displayItems.map((g) => (
              <div 
                key={g.id} 
                onClick={() => { setSelectedItemId(g.id); setIsDeleteConfirmOpen(false); }}
                className="bg-white border-4 border-black p-4 flex flex-col justify-between h-64 relative cursor-crosshair shadow-[4px_4px_0px_0px_#000000] hover:shadow-[6px_6px_0px_0px_#000000] hover:-translate-x-0.5 hover:-translate-y-0.5 transition-all duration-150 group"
              >
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setGarments(prev => prev.map(item => item.id === g.id ? { ...item, favorite: !item.favorite } : item));
                  }} 
                  className="absolute top-3 right-3 w-8 h-8 bg-white border-2 border-black flex items-center justify-center text-black z-10 shadow-[2px_2px_0px_0px_#000000] hover:bg-zinc-100"
                >
                  <Heart className={`w-4 h-4 stroke-[2.5] ${g.favorite ? "fill-black text-black" : "text-black"}`} />
                </button>

                <div className="w-full h-32 bg-zinc-50 border-2 border-black mt-6 flex items-center justify-center text-4xl relative overflow-hidden">
                  <span className="group-hover:scale-110 group-hover:rotate-3 transition-transform duration-200 filter drop-shadow-[2px_2px_0px_rgba(0,0,0,0.15)]">
                    {g.img}
                  </span>
                </div>

                <div className="mt-3 pt-2 border-t-2 border-black">
                  <p className="text-xs font-sans font-bold text-black tracking-tight line-clamp-1">{g.name}</p>
                  <p className="text-[10px] font-mono font-bold text-zinc-400 uppercase mt-0.5">// {g.category}</p>
                </div>
              </div>
            ))}
            
            <Link 
              href="/extract" 
              className="border-4 border-dashed border-zinc-400 bg-zinc-50 text-zinc-400 hover:border-black hover:text-black flex flex-col items-center justify-center text-center gap-3 h-64 transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,0.05)] hover:shadow-[4px_4px_0px_0px_#000000] group"
            >
              <div className="w-9 h-9 bg-white border-2 border-zinc-400 group-hover:border-black flex items-center justify-center text-zinc-400 group-hover:text-black transition-colors">
                <Plus className="w-5 h-5 stroke-[3]" />
              </div>
              <p className="text-xs font-mono font-black uppercase tracking-widest">ADD_ITEM //</p>
            </Link>
          </div>
        ) : (
          <div className="text-center py-16 border-4 border-dashed border-zinc-300 bg-zinc-100/50 font-mono text-zinc-400 text-xs font-black uppercase tracking-wider">
            [ ERR: NO_CUSTOM_OUTFIT_SETS_FOUND ]
          </div>
        )}
      </div>

      {/* ========================================================= */}
      {/* GARMENT DETAILED INSPECTION MODAL PANEL (STARK WHITE PANEL) */}
      {/* ========================================================= */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto backdrop-blur-xs animate-in fade-in duration-150">
          <div 
            className="bg-white border-4 border-black w-full max-w-xl p-6 relative shadow-[8px_8px_0px_0px_#000000] space-y-6 my-8"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close */}
            <button 
              onClick={() => setSelectedItemId(null)}
              className="absolute top-4 right-4 p-1.5 border-2 border-black bg-white text-black hover:bg-black hover:text-white transition-colors z-10"
            >
              <X className="w-4 h-4 stroke-[3]" />
            </button>

            {/* Header Display */}
            <div className="flex items-center gap-4 pt-2 border-b-4 border-black pb-4">
              <div className="w-16 h-16 bg-zinc-50 border-2 border-black flex items-center justify-center text-4xl shrink-0 shadow-[2px_2px_0px_0px_#000000]">
                {selectedItem.img}
              </div>
              <div className="space-y-0.5">
                <span className="text-[9px] font-mono font-black bg-black text-white px-2 py-0.5 uppercase tracking-wider">
                  {selectedItem.category} // CV_SCAN_NODE_{selectedItem.id}
                </span>
                <h3 className="text-xl font-sans font-black text-black tracking-tight">{selectedItem.name}</h3>
              </div>
            </div>

            {!isDeleteConfirmOpen ? (
              <div className="space-y-6">
                
                {/* Section 1: Standard Extracted Image Meta */}
                <div className="space-y-2">
                  <p className="text-[10px] font-mono font-black text-zinc-400 uppercase tracking-widest">// DETECTED_IMAGE_PARAMETERS</p>
                  <div className="grid grid-cols-2 gap-2 text-xs font-sans font-medium text-black">
                    <div className="border-2 border-black bg-zinc-50 p-2.5">
                      <span className="block text-[9px] font-mono font-black text-zinc-400">// FILE_PROCESSED_DATE</span>
                      <span className="font-bold">{selectedItem.specs?.detectedOn || "N/A"}</span>
                    </div>
                    <div className="border-2 border-black bg-zinc-50 p-2.5">
                      <span className="block text-[9px] font-mono font-black text-zinc-400">// CLASSIFIED_FIT_MASK</span>
                      <span className="font-bold">{selectedItem.specs?.inferredFit || "N/A"}</span>
                    </div>
                    <div className="border-2 border-black bg-zinc-50 p-2.5 col-span-2">
                      <span className="block text-[9px] font-mono font-black text-zinc-400">// STRUCTURAL_VISUAL_CATEGORY</span>
                      <span className="font-bold">{selectedItem.specs?.visualCategory || "N/A"}</span>
                    </div>
                    <div className="border-2 border-black bg-zinc-50 p-2.5 col-span-2">
                      <span className="block text-[9px] font-mono font-black text-zinc-400">// SURFACE_PATTERN_DETECTION</span>
                      <span className="font-bold text-zinc-800">{selectedItem.specs?.dominantPattern || "N/A"}</span>
                    </div>
                  </div>
                </div>

                {/* Section 2: AI Recommender Feature Vector Parameters (Flipped to White Layout) */}
                <div className="border-4 border-black bg-white text-black p-4 space-y-4 shadow-[4px_4px_0px_0px_#000000]">
                  <div className="flex items-center gap-2 border-b-2 border-black pb-2">
                    <Cpu className="w-4 h-4 text-black stroke-[3]" />
                    <p className="text-[10px] font-mono font-black uppercase tracking-widest text-black">
                      AI_RECOMMENDER_EXTRACTED_VECTORS //
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-[11px]">
                    
                    {/* Embedded Pixel Color Quantization */}
                    <div className="space-y-1">
                      <span className="block text-[9px] font-black text-zinc-400">// QUANTIZED_PRIMARY_HEX</span>
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-4 h-4 border-2 border-black" 
                          style={{ backgroundColor: selectedItem.aiTags?.primaryColorHex || "#000" }}
                        />
                        <span className="font-black text-black">{selectedItem.aiTags?.primaryColorHex || "#000000"}</span>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="block text-[9px] font-black text-zinc-400">// QUANTIZED_SECONDARY_HEX</span>
                      <div className="flex items-center gap-2">
                        {selectedItem.aiTags?.secondaryColorHex && selectedItem.aiTags.secondaryColorHex !== "NONE_DETECTED" ? (
                          <>
                            <div 
                              className="w-4 h-4 border-2 border-black" 
                              style={{ backgroundColor: selectedItem.aiTags.secondaryColorHex }}
                            />
                            <span className="font-black text-black">{selectedItem.aiTags.secondaryColorHex}</span>
                          </>
                        ) : (
                          <span className="font-bold text-zinc-400">NONE_DETECTED</span>
                        )}
                      </div>
                    </div>

                    {/* Layering Graph Node Weights */}
                    <div className="space-y-1 border-t border-zinc-200 pt-2">
                      <span className="block text-[9px] font-black text-zinc-400">// OUTFIT_LAYERING_INDEX</span>
                      <span className="font-black text-black">{selectedItem.aiTags?.layeringPriorityIndex || "UNSET"}</span>
                    </div>

                    {/* Extracted Silhouette Vibe */}
                    <div className="space-y-1 border-t border-zinc-200 pt-2">
                      <span className="block text-[9px] font-black text-zinc-400">// SILHOUETTE_OUTPUT_TAG</span>
                      <span className="font-black text-black">{selectedItem.aiTags?.vibeSignature || "STANDARD"}</span>
                    </div>

                    {/* Sub Genre Classifiers for Compatibility Parsing */}
                    <div className="space-y-1 col-span-1 sm:col-span-2 border-t border-zinc-200 pt-2">
                      <span className="block text-[9px] font-black text-zinc-400">// MATCHING_STYLE_GENRES</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {selectedItem.aiTags?.detectedSubGenres?.map((genre, i) => (
                          <span key={i} className="bg-zinc-100 text-black border-2 border-black px-1.5 py-0.5 text-[9px] font-black">
                            {genre}
                          </span>
                        )) || <span className="text-zinc-400">NONE</span>}
                      </div>
                    </div>

                    <div className="space-y-1 col-span-1 sm:col-span-2 border-t border-zinc-200 pt-2">
                      <span className="block text-[9px] font-black text-zinc-400">// SEASONAL_PAIRING_RESTRICTIONS</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {selectedItem.aiTags?.inferredSeasonality?.map((season, i) => (
                          <span key={i} className="bg-zinc-100 text-black border-2 border-black px-1.5 py-0.5 text-[9px] font-black">
                            {season}
                          </span>
                        )) || <span className="text-zinc-400">ALL_SEASON</span>}
                      </div>
                    </div>

                    {/* Texture/Weight Matrix */}
                    <div className="space-y-1 col-span-1 sm:col-span-2 border-t border-zinc-200 pt-2">
                      <span className="block text-[9px] font-black text-zinc-400">// INFERRED_FABRIC_WEIGHT_CLASS</span>
                      <span className="font-black text-black">{selectedItem.aiTags?.estimatedTextureDensity || "UNKNOWN"}</span>
                    </div>

                  </div>
                </div>

                {/* Base Panel Controls */}
                <div className="pt-2 flex justify-between gap-3">
                  <button 
                    onClick={() => setSelectedItemId(null)}
                    className="flex-1 bg-black text-white border-2 border-black text-center py-2.5 text-xs font-mono font-black uppercase tracking-widest shadow-[3px_3px_0px_0px_#27272a] hover:bg-zinc-800 transition-all"
                  >
                    DISMISS_DATATRACK //
                  </button>
                  <button 
                    onClick={() => setIsDeleteConfirmOpen(true)}
                    className="px-4 bg-white text-rose-600 border-2 border-rose-600 hover:bg-rose-600 hover:text-white text-center py-2.5 text-xs font-mono font-black uppercase tracking-widest transition-colors shadow-[2px_2px_0px_0px_rgba(225,29,72,0.2)]"
                  >
                    <Trash2 className="w-4 h-4 stroke-[2.5]" />
                  </button>
                </div>
              </div>
            ) : (
              /* Destructive Confirmation Node */
              <div className="bg-rose-50 border-4 border-rose-600 p-4 space-y-4 animate-in zoom-in-95 duration-150">
                <div className="flex items-start gap-2.5 text-rose-700">
                  <ShieldAlert className="w-5 h-5 shrink-0 stroke-[2.5] mt-0.5" />
                  <div>
                    <h4 className="text-xs font-mono font-black uppercase tracking-tight">DATA_PURGE_WARNING //</h4>
                    <p className="text-xs font-sans font-medium mt-1">
                      Deleting this component breaks active token graph associations. The AI recommender will lose reference parameters for <strong className="font-bold text-rose-950">{selectedItem.name}</strong>.
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button 
                    onClick={() => handleDeleteItem(selectedItem.id)}
                    className="flex-1 bg-rose-600 text-white border-2 border-rose-700 text-center py-2 font-mono text-xs font-black uppercase tracking-wider hover:bg-rose-700 transition-colors"
                  >
                    WIPE_FROM_RECOMMENDER_MODELS
                  </button>
                  <button 
                    onClick={() => setIsDeleteConfirmOpen(false)}
                    className="px-4 bg-white text-black border-2 border-black text-center py-2 font-mono text-xs font-black uppercase tracking-wider hover:bg-zinc-100 transition-colors"
                  >
                    ABORT
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>
      )}
    </Layout>
  );
}