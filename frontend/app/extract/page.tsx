"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud } from "lucide-react";
import Layout from "@/components/Layout";
import { submitWardrobeImage } from "@/lib/api";

export default function ExtractLandingPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [message, setMessage] = useState("Choose a JPEG or PNG wardrobe image (maximum 10 MB).");
  const [submitting, setSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const upload = async (file?: File) => {
    if (!file || submitting) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) { setMessage("Choose a JPEG or PNG image."); return; }
    if (file.size > 10 * 1024 * 1024) { setMessage("Choose an image smaller than 10 MB."); return; }
    setSubmitting(true); setMessage("Validating and preparing your image…");
    try { const job = await submitWardrobeImage(file); router.push(`/extract/results?job=${job.id}`); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Upload failed. Please try another image."); setSubmitting(false); }
  };
  return <Layout><div className="w-full space-y-8 border-4 border-black bg-white p-6 shadow-[6px_6px_0_#000] md:p-8">
    <div className="border-b-4 border-black pb-4 text-center"><h1 className="text-2xl font-mono font-black">Add garments from an image</h1><p className="mt-2 text-xs font-mono text-zinc-500">Images are private and candidates stay reviewable until you save them.</p></div>
    <button type="button" disabled={submitting} aria-busy={submitting} onClick={() => inputRef.current?.click()} onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }} onDragOver={(event) => { event.preventDefault(); setDragActive(true); }} onDragLeave={() => setDragActive(false)} onDrop={(event) => { event.preventDefault(); setDragActive(false); void upload(event.dataTransfer.files?.[0]); }} className={`w-full border-4 border-dashed bg-zinc-50 p-10 text-center transition sm:p-12 ${dragActive ? "border-[#6d335b] bg-[#f5eaf1]" : "border-zinc-400 hover:border-black"} disabled:cursor-wait disabled:opacity-70`}><UploadCloud className={`mx-auto h-10 w-10 ${submitting ? "animate-pulse" : ""}`} aria-hidden="true" /><p className="mt-4 font-mono text-sm font-black">{submitting ? "Processing upload…" : dragActive ? "Drop the photo here" : "Choose or drop a photo"}</p><p className="mt-2 text-xs text-zinc-500">JPEG or PNG · maximum 10 MB</p></button>
    <input ref={inputRef} aria-label="Wardrobe image" onChange={(event) => { void upload(event.target.files?.[0]); event.target.value = ""; }} type="file" accept="image/jpeg,image/png" className="hidden" />
    <p role="status" aria-live="polite" className="rounded-xl bg-zinc-50 px-4 py-3 text-sm text-slate-600">{message}</p>
    <div className="grid gap-3 text-xs text-zinc-600 sm:grid-cols-3"><p><strong className="block text-zinc-800">Use clear lighting</strong>Avoid heavy shadows.</p><p><strong className="block text-zinc-800">Keep garments visible</strong>Reduce overlap where possible.</p><p><strong className="block text-zinc-800">One person per photo</strong>Use a front-facing image.</p></div>
  </div></Layout>;
}
