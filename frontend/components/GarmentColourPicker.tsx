"use client";

import { useState } from "react";
import ProtectedImage from "@/components/ProtectedImage";

declare global {
  interface Window {
    EyeDropper?: new () => { open: () => Promise<{ sRGBHex: string }> };
  }
}

type Props = {
  label: string;
  value: string;
  mediaId?: string | null;
  disabled?: boolean;
  onChange: (value: string) => void;
};

const isHex = (value: string) => /^#[0-9a-f]{6}$/i.test(value.trim());

export function GarmentColourPreview({ label, value }: { label: string; value: string }) {
  const colour = value.trim();
  return <div className="flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1.5 text-xs">
    <span aria-hidden="true" className="h-6 w-6 shrink-0 rounded-full border border-slate-300" style={{ background: isHex(colour) ? colour : "repeating-conic-gradient(#e5e7eb 0 25%, white 0 50%) 50% / 8px 8px" }} />
    <span className="text-slate-600">{label}: <span className="font-mono font-semibold text-slate-900">{colour || "Not selected"}</span></span>
  </div>;
}

export default function GarmentColourPicker({ label, value, mediaId, disabled = false, onChange }: Props) {
  const [picking, setPicking] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const colour = value.trim();

  const pick = async () => {
    if (!window.EyeDropper) {
      setNotice("Your browser does not support the eyedropper. Use a browser with the native colour picker enabled.");
      return;
    }
    setPicking(true);
    setNotice("Select a pixel from the garment image.");
    try {
      const result = await new window.EyeDropper().open();
      onChange(result.sRGBHex.toLowerCase());
      setNotice("Colour selected from the image.");
    } catch {
      setNotice(""); // The user cancelled the native picker.
    } finally {
      setPicking(false);
    }
  };

  return <div className="space-y-2">
    <GarmentColourPreview label={`Selected ${label.toLowerCase()}`} value={colour} />
    <button type="button" disabled={disabled || picking || !mediaId} onClick={() => setPreviewOpen(true)} className="min-h-11 w-full rounded-lg border border-[#6d335b] px-3 text-sm font-semibold text-[#6d335b] disabled:opacity-50">
      Pick from garment image
    </button>
    <p className="text-xs text-slate-500">Open the garment preview to sample an exact colour. The change is saved only when you save this review.</p>
    {notice && <p className="text-xs text-slate-600" role="status">{notice}</p>}
    {previewOpen && <div className="fixed inset-0 z-50 flex items-end justify-end bg-slate-950/35 p-3 sm:p-6" role="dialog" aria-modal="true" aria-label={`Pick ${label.toLowerCase()} from garment image`}>
      <button type="button" aria-label="Close garment image preview" onClick={() => setPreviewOpen(false)} className="absolute inset-0 cursor-default" />
      <section className="relative z-10 flex max-h-full w-full max-w-md flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 p-4"><div><h3 className="font-semibold">Pick {label.toLowerCase()}</h3><p className="mt-1 text-sm text-slate-600">Use the eyedropper on this garment image.</p></div><button type="button" onClick={() => setPreviewOpen(false)} className="min-h-11 rounded-lg px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100">Close</button></header>
        <div className="min-h-0 flex-1 bg-slate-100 p-4"><ProtectedImage mediaId={mediaId!} alt="Garment colour reference" className="max-h-[60vh] w-full object-contain" /></div>
        <footer className="border-t border-slate-200 p-4"><button type="button" disabled={picking} onClick={() => void pick()} className="min-h-11 w-full rounded-lg bg-[#6d335b] px-3 text-sm font-semibold text-white disabled:opacity-50">{picking ? "Choose a pixel from the garment image…" : "Use eyedropper on this image"}</button></footer>
      </section>
    </div>}
  </div>;
}
