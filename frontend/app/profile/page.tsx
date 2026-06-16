"use client";

import React, { useState } from "react";
import { User, Cpu, Shield, HardDrive, Key, LogOut, Layers, Eye, RefreshCw } from "lucide-react";
import Layout from "@/components/Layout";

export default function ProfilePage() {
  // Mock State for user profile configuration matrices
  const [userData, setUserData] = useState({
    username: "ARCHIVE_HEAD_99",
    email: "user.node@identity.io",
    accountTier: "NEURAL_PREMIUM",
    joinedDate: "2026-02-11",
    syncStatus: "CONNECTED"
  });

  // Computer Vision Data Pipeline Statistics
  const pipelineStats = {
    totalScansProcessed: 142,
    successfulSegmentationRate: "98.4%",
    totalVectorEmbeddingsGenerated: 1136,
    storageUsedGb: 1.45,
    storageLimitGb: 10.00
  };

  const handleDisconnectNode = () => {
    alert("DISCONNECT_SEQUENCE_INITIALIZED // TERMINATING SESSION TOKEN.");
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300 antialiased">
        
        {/* ========================================================= */}
        {/* PROFILE HEADER BLOCK                                      */}
        {/* ========================================================= */}
        <div className="bg-white border-4 border-black p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-[4px_4px_0px_0px_#000000]">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-zinc-50 border-4 border-black flex items-center justify-center text-black shrink-0 shadow-[2px_2px_0px_0px_#000000]">
              <User className="w-8 h-8 stroke-[2.5]" />
            </div>
            <div>
              <span className="text-[9px] font-mono font-black bg-black text-white px-2 py-0.5 uppercase tracking-wider">
                {userData.accountTier} // USER_NODE
              </span>
              <h2 className="text-2xl font-sans font-black text-black tracking-tight mt-1">{userData.username}</h2>
              <p className="text-xs font-mono font-bold text-zinc-400 mt-0.5">// NETWORK_ID: {userData.email}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-zinc-50 border-2 border-black px-3 py-1.5 font-mono text-[10px] font-black">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            PIPELINE_STATUS: {userData.syncStatus}
          </div>
        </div>

        {/* ========================================================= */}
        {/* MAIN CONFIGURATION MATRIX LAYOUT                          */}
        {/* ========================================================= */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* LEFT/MID COLUMN: SYSTEM METRICS & AI PIPELINE ANALYTICS */}
          <div className="md:col-span-2 space-y-6">
            
            {/* AI COMPUTER VISION METRICS CONTAINER */}
            <div className="bg-white border-4 border-black p-6 space-y-4 shadow-[4px_4px_0px_0px_#000000]">
              <div className="flex items-center gap-2 border-b-2 border-black pb-2">
                <Cpu className="w-4 h-4 text-black stroke-[3]" />
                <h3 className="text-xs font-mono font-black uppercase tracking-widest text-black">
                  COMPUTER_VISION_PIPELINE_METRICS //
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-sans font-medium text-black">
                <div className="border-2 border-black bg-zinc-50 p-3">
                  <span className="block text-[9px] font-mono font-black text-zinc-400">// CAPTURED_SOURCE_IMAGES</span>
                  <span className="text-lg font-black font-mono">{pipelineStats.totalScansProcessed}</span>
                </div>
                <div className="border-2 border-black bg-zinc-50 p-3">
                  <span className="block text-[9px] font-mono font-black text-zinc-400">// BACKGROUND_REMOVAL_SUCCESS</span>
                  <span className="text-lg font-black font-mono text-emerald-600">{pipelineStats.successfulSegmentationRate}</span>
                </div>
                <div className="border-2 border-black bg-zinc-50 p-3">
                  <span className="block text-[9px] font-mono font-black text-zinc-400">// AI_VECTOR_EMBEDDING_TOKENS</span>
                  <span className="text-lg font-black font-mono">{pipelineStats.totalVectorEmbeddingsGenerated}</span>
                </div>
                <div className="border-2 border-black bg-zinc-50 p-3">
                  <span className="block text-[9px] font-mono font-black text-zinc-400">// MATRIX_ACTIVATION_DATE</span>
                  <span className="text-sm font-bold font-mono pt-1 block">{userData.joinedDate}</span>
                </div>
              </div>

              {/* CLOUD IMAGE RESOURCE STORAGE BLOCK */}
              <div className="border-2 border-black p-4 bg-zinc-50 space-y-2">
                <div className="flex justify-between items-center font-mono text-[10px] font-black">
                  <div className="flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 stroke-[2.5]" />
                    <span>SEGMENTED_PNG_STORAGE</span>
                  </div>
                  <span>{pipelineStats.storageUsedGb} GB / {pipelineStats.storageLimitGb} GB</span>
                </div>
                <div className="w-full bg-zinc-200 border border-black h-4 p-0.5">
                  <div 
                    className="bg-black h-full transition-all duration-500" 
                    style={{ width: `${(pipelineStats.storageUsedGb / pipelineStats.storageLimitGb) * 100}%` }}
                  />
                </div>
                <span className="block text-[9px] font-mono font-medium text-zinc-400">
                  * High-resolution alpha-channel clothing PNGs are cached globally for vector alignment scoring.
                </span>
              </div>
            </div>

            {/* CORE SECURITY / IDENTIFICATION SETTINGS */}
            <div className="bg-white border-4 border-black p-6 space-y-4 shadow-[4px_4px_0px_0px_#000000]">
              <div className="flex items-center gap-2 border-b-2 border-black pb-2">
                <Shield className="w-4 h-4 text-black stroke-[3]" />
                <h3 className="text-xs font-mono font-black uppercase tracking-widest text-black">
                  NODE_IDENTITY_CREDENTIALS //
                </h3>
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-zinc-200 pb-3">
                  <div>
                    <span className="block text-[9px] font-black text-zinc-400">// INSTANTIATED_NAME</span>
                    <span className="font-bold text-black">{userData.username}</span>
                  </div>
                  <button className="px-3 py-1 border-2 border-black text-[10px] font-black uppercase hover:bg-zinc-100 transition-colors shadow-[2px_2px_0px_0px_#000000]">
                    EDIT_ALIAS
                  </button>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-zinc-200 pb-3">
                  <div>
                    <span className="block text-[9px] font-black text-zinc-400">// ACCESS_KEY_PASSPHRASE</span>
                    <span className="font-bold text-black">••••••••••••••••</span>
                  </div>
                  <button className="px-3 py-1 border-2 border-black text-[10px] font-black uppercase hover:bg-zinc-100 transition-colors shadow-[2px_2px_0px_0px_#000000]">
                    MODIFY_KEY
                  </button>
                </div>
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN: RECOSYSTEM ACTIONS & CONTROLS */}
          <div className="space-y-6">
            
            {/* AI ENGINE RE-CALIBRATION UTILITY */}
            <div className="bg-white border-4 border-black p-6 space-y-4 shadow-[4px_4px_0px_0px_#000000]">
              <div className="flex items-center gap-2 border-b-2 border-black pb-2">
                <Layers className="w-4 h-4 text-black stroke-[3]" />
                <h3 className="text-xs font-mono font-black uppercase tracking-widest text-black">
                  MODEL_CONFIG //
                </h3>
              </div>
              
              <p className="text-xs font-sans font-medium text-zinc-700 leading-relaxed">
                Force your vector weightings to sync up if the AI optimizer is getting stuck suggesting the exact same look sequences.
              </p>

              <button className="w-full flex items-center justify-center gap-2 bg-black text-white border-2 border-black py-2 text-xs font-mono font-black uppercase tracking-wider shadow-[3px_3px_0px_0px_#52525b] hover:bg-zinc-800 transition-all">
                <RefreshCw className="w-3.5 h-3.5 stroke-[2.5]" />
                REINDEX_CLUSTER_GRAPHS
              </button>
            </div>

            {/* DESTRUCTIVE TERMINATION LOGOUT TRIGGER */}
            <div className="bg-white border-4 border-black p-6 space-y-4 shadow-[4px_4px_0px_0px_#000000]">
              <div className="flex items-center gap-2 border-b-2 border-black pb-2">
                <Key className="w-4 h-4 text-black stroke-[3]" />
                <h3 className="text-xs font-mono font-black uppercase tracking-widest text-black">
                  SESSION_CONTROLS //
                </h3>
              </div>

              <p className="text-xs font-sans font-medium text-zinc-500">
                Purges active encryption cookies from your secure web browser workspace container.
              </p>

              <button 
                onClick={handleDisconnectNode}
                className="w-full flex items-center justify-center gap-2 bg-white text-rose-600 border-2 border-rose-600 py-2 text-xs font-mono font-black uppercase tracking-wider hover:bg-rose-600 hover:text-white transition-colors"
              >
                <LogOut className="w-3.5 h-3.5 stroke-[2.5]" />
                DISCONNECT_SESSION_NODE
              </button>
            </div>

          </div>

        </div>

      </div>
    </Layout>
  );
}