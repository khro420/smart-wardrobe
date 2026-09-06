"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Plus, Sparkles } from "lucide-react";

import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import {
  createVisualisation, getPersonImages, prepareVisualisation, uploadPersonImage,
  type PersonImage, type VisualisationPreparation, type VisualisationSource,
} from "@/lib/api";

function OutfitVisualisationContent() {
  const searchParams = useSearchParams();
  const outfitId = searchParams.get("outfit");
  const recommendationId = searchParams.get("recommendation");
  const invalidSource = Boolean(outfitId && recommendationId);
  const source = useMemo<VisualisationSource | null>(() => {
    if (invalidSource) return null;
    if (outfitId) return { outfitId };
    if (recommendationId) return { recommendationId };
    return null;
  }, [invalidSource, outfitId, recommendationId]);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [images, setImages] = useState<PersonImage[]>([]);
  const [preparation, setPreparation] = useState<VisualisationPreparation>();
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [loadingImages, setLoadingImages] = useState(true);
  const [uploading, setUploading] = useState(false);
  const preparedForSource = Boolean(source && preparation && (
    ("outfitId" in source && preparation.source_id === source.outfitId) ||
    ("recommendationId" in source && preparation.source_id === source.recommendationId)
  ));
  const preparing = Boolean(source && !preparedForSource);

  useEffect(() => {
    let active = true;
    getPersonImages().then((next) => {
      if (active) {
        setImages(next);
        setSelectedId((current) => current || next[0]?.id || "");
      }
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not load personal images.");
    }).finally(() => { if (active) setLoadingImages(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!source) {
      return;
    }
    let active = true;
    prepareVisualisation(source).then((next) => {
      if (active) setPreparation(next);
    }).catch((cause: unknown) => {
      if (active) {
        setPreparation(undefined);
        setError(cause instanceof Error ? cause.message : "This source cannot be prepared for try-on.");
      }
    });
    return () => { active = false; };
  }, [source]);

  const upload = async (file?: File) => {
    if (!file || uploading) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) { setError("Choose a JPEG or PNG personal image."); return; }
    if (file.size > 10 * 1024 * 1024) { setError("Choose a personal image smaller than 10 MB."); return; }
    setUploading(true);
    setError("");
    try {
      const added = await uploadPersonImage(file);
      setImages((current) => [added, ...current]);
      setSelectedId(added.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not upload the personal image.");
    } finally { setUploading(false); }
  };

  const visualise = async () => {
    if (!source || !preparation || !selectedId) return;
    setCreating(true);
    setError("");
    try {
      const visualisation = await createVisualisation(source, selectedId);
      router.push(`/try-on/result?id=${visualisation.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start visualisation.");
      setCreating(false);
    }
  };

  const missingSourceMessage = invalidSource
    ? "Choose exactly one source. The URL contains both an outfit and a recommendation."
    : "Choose Visualise from a saved wardrobe outfit or recommendation first.";

  return <Layout><div className="space-y-7">
    <Link href="/wardrobe" className="inline-flex min-h-10 items-center text-sm underline">Back to wardrobe</Link>
    <div className="border-2 border-black bg-white p-6"><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">OUTFIT VISUALISATION</p><h1 className="mt-2 text-3xl font-black">Choose a private base image</h1><p className="mt-2 max-w-2xl text-sm text-zinc-600">The source and its confirmed garment are checked before a request can be submitted.</p></div>
    {!source && <p role="alert" className="border-2 border-amber-600 bg-amber-50 p-3 text-sm text-amber-800">{missingSourceMessage}</p>}
    {error && <p role="alert" className="border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    {preparing && <div role="status" className="ui-skeleton h-36 rounded-xl" aria-label="Validating try-on source" />}
    {preparedForSource && preparation && <section className="border-2 border-black bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">VALIDATED SOURCE</p><h2 className="text-xl font-black">{preparation.category} garment</h2><p className="mt-1 text-sm text-zinc-600">{preparation.capture_guidance}</p></div><span className="bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900">Ready</span></div><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{preparation.items.map((item) => <article key={item.garment_id} className="flex gap-3 border-2 border-zinc-200 p-3"><ProtectedImage mediaId={item.source_media_id} alt={item.name} className="h-24 w-20 object-contain" /><div><h3 className="font-bold">{item.name}</h3><p className="mt-1 text-xs text-zinc-500">{item.category.replaceAll("_", " ")}</p><p className="mt-1 text-xs text-zinc-500">Role: {item.role}</p></div></article>)}</div></section>}
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]"><section aria-busy={loadingImages || uploading}><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-bold">Available personal images</h2><p className="text-xs text-zinc-500">JPEG or PNG · maximum 10 MB</p></div><button type="button" disabled={uploading} onClick={() => inputRef.current?.click()} className="inline-flex min-h-11 items-center gap-1 border-2 border-black px-3 py-2 text-xs font-bold disabled:opacity-50"><Plus className="h-4 w-4" aria-hidden="true" /> {uploading ? "Uploading…" : "Upload image"}</button></div><input ref={inputRef} aria-label="Upload a private JPEG or PNG base image" type="file" accept="image/jpeg,image/png" onChange={(event) => { void upload(event.target.files?.[0]); event.target.value = ""; }} className="hidden" /><div className="grid gap-3 sm:grid-cols-2">{loadingImages ? [0, 1].map((item) => <div key={item} className="ui-skeleton aspect-[3/4] rounded-xl" role="status" aria-label="Loading personal images" />) : images.map((image) => <button type="button" key={image.id} onClick={() => setSelectedId(image.id)} aria-pressed={selectedId === image.id} className={`relative overflow-hidden border-2 p-2 text-left transition ${selectedId === image.id ? "border-black ring-2 ring-zinc-400" : "border-zinc-300 hover:border-zinc-500"}`}><ProtectedImage mediaId={image.media_id} alt={image.display_name} className="aspect-[3/4] w-full object-cover" /><p className="mt-2 text-sm font-bold">{image.display_name}</p>{selectedId === image.id && <span className="absolute right-3 top-3 rounded-full bg-black p-1.5 text-white"><Check className="h-4 w-4" aria-label="Selected" /></span>}</button>)}{!loadingImages && !images.length && <p className="border-2 border-dashed border-zinc-400 p-8 text-center text-sm text-zinc-500 sm:col-span-2">Upload a clear JPEG or PNG photo of yourself.</p>}</div></section><aside className="h-fit border-2 border-black bg-zinc-50 p-5 lg:sticky lg:top-24"><h2 className="font-bold">Generation contract</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-zinc-600"><li>One person and one supported garment.</li><li>Output is 768 × 1024 PNG.</li><li>Results are visual previews, not physical-fit measurements.</li></ul><button disabled={!source || !preparedForSource || !selectedId || creating || loadingImages || preparing} onClick={() => void visualise()} aria-busy={creating} className="mt-6 flex min-h-11 w-full items-center justify-center gap-2 bg-black px-4 py-3 text-sm font-bold text-white disabled:opacity-40"><Sparkles className="h-4 w-4" aria-hidden="true" />{creating ? "Creating request…" : "Create visualisation"}</button></aside></div>
  </div></Layout>;
}

export default function OutfitVisualisationPage() {
  return <Suspense fallback={<Layout><div className="p-8 text-sm">Loading visualisation...</div></Layout>}><OutfitVisualisationContent /></Suspense>;
}
