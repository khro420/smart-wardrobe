"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, RefreshCw, X } from "lucide-react";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import {
  cancelVisualisation, createVisualisation, downloadProtectedMedia, getVisualisation,
  type Visualisation, type VisualisationSource,
} from "@/lib/api";

function ResultContent() {
  const id = useSearchParams().get("id");
  const router = useRouter();
  const [visualisation, setVisualisation] = useState<Visualisation>();
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [action, setAction] = useState<"download" | "cancel" | "retry" | "">("");

  useEffect(() => {
    if (!id) return;
    let active = true;
    let timer: number | undefined;
    const load = async () => {
      try {
        const next = await getVisualisation(id);
        if (!active) return;
        setVisualisation(next);
        setError("");
        if (["queued", "processing"].includes(next.status)) timer = window.setTimeout(load, 1000);
      } catch (exception) {
        if (active) setError(exception instanceof Error ? exception.message : "Could not load visualisation.");
      }
    };
    void load();
    return () => { active = false; if (timer) window.clearTimeout(timer); };
  }, [id, reload]);

  const pending = Boolean(id) && (!visualisation || ["queued", "processing"].includes(visualisation.status));
  const download = async () => {
    if (!visualisation?.output_media_id) return;
    setAction("download"); setError("");
    try { await downloadProtectedMedia(visualisation.output_media_id, "smart-wardrobe-visualisation.png"); }
    catch (exception) { setError(exception instanceof Error ? exception.message : "Could not download output."); }
    finally { setAction(""); }
  };
  const cancel = async () => {
    if (!id) return;
    setAction("cancel"); setError("");
    try { await cancelVisualisation(id); setReload((value) => value + 1); }
    catch (exception) { setError(exception instanceof Error ? exception.message : "Could not cancel visualisation."); }
    finally { setAction(""); }
  };
  const retry = async () => {
    if (!visualisation) return;
    const source: VisualisationSource | null = visualisation.source_type === "outfit" && visualisation.outfit_id
      ? { outfitId: visualisation.outfit_id }
      : visualisation.source_type === "recommendation" && visualisation.recommendation_id
        ? { recommendationId: visualisation.recommendation_id }
        : null;
    if (!source) { setError("The original source is no longer available."); return; }
    setAction("retry"); setError("");
    try {
      const next = await createVisualisation(source, visualisation.person_image_id);
      router.push(`/try-on/result?id=${next.id}`);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not retry visualisation.");
      setAction("");
    }
  };

  return <Layout><div className="space-y-7">
    <Link href="/wardrobe" className="text-sm underline">Back to wardrobe</Link>
    <div className="border-2 border-black bg-white p-6"><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">OUTFIT VISUALISATION</p><h1 className="mt-2 text-3xl font-black">Your outfit preview</h1><p className="mt-2 text-sm text-zinc-600">{pending ? "Processing status is updating…" : visualisation?.notice ?? "Open a saved visualisation request to see its result."}</p></div>
    {(error || !id) && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700"><span>{error || "No visualisation was selected."}</span>{id && <button type="button" onClick={() => setReload((value) => value + 1)} className="inline-flex min-h-10 items-center gap-2 px-3 font-bold underline"><RefreshCw className="h-4 w-4" aria-hidden="true" /> Reload</button>}</div>}
    {visualisation?.status === "failed" && <div role="alert" className="border-2 border-rose-600 bg-rose-50 p-4 text-sm text-rose-700"><p>{visualisation.error_message ?? "Visualisation failed. Choose another image and retry."}</p><button type="button" onClick={() => void retry()} disabled={Boolean(action)} className="mt-3 inline-flex min-h-10 items-center gap-2 bg-black px-3 py-2 font-bold text-white disabled:opacity-50"><RefreshCw className="h-4 w-4" aria-hidden="true" />{action === "retry" ? "Retrying…" : "Retry same inputs"}</button></div>}
    {visualisation?.status === "cancelled" && <div className="border-2 border-zinc-500 bg-zinc-50 p-4 text-sm"><p>This request was cancelled. Its inputs remain available for a new request.</p><button type="button" onClick={() => void retry()} disabled={Boolean(action)} className="mt-3 inline-flex min-h-10 items-center gap-2 bg-black px-3 py-2 font-bold text-white disabled:opacity-50"><RefreshCw className="h-4 w-4" aria-hidden="true" />{action === "retry" ? "Retrying…" : "Submit again"}</button></div>}
    {pending && id && <div className="border-2 border-dashed border-zinc-400 p-12 text-center text-sm" role="status" aria-live="polite"><RefreshCw className="mx-auto mb-3 h-6 w-6 animate-spin" aria-hidden="true" />Status: {visualisation?.status ?? "loading"}{visualisation && <button type="button" onClick={() => void cancel()} disabled={Boolean(action)} className="mx-auto mt-5 flex min-h-10 items-center gap-2 border-2 border-black px-3 py-2 font-bold disabled:opacity-50"><X className="h-4 w-4" aria-hidden="true" />{action === "cancel" ? "Cancelling…" : "Cancel request"}</button>}</div>}
    {visualisation?.status === "completed" && visualisation.output_media_id && <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
      <section className="border-2 border-black bg-zinc-50 p-4"><ProtectedImage mediaId={visualisation.output_media_id} alt="Generated outfit visualisation" className="mx-auto max-h-[70vh] w-auto max-w-full" /><p className="mt-3 text-xs text-zinc-600">{visualisation.is_development_fallback ? "Development fallback output: this is not a real virtual try-on result." : visualisation.notice}</p></section>
      <aside className="h-fit border-2 border-black p-4 lg:sticky lg:top-24"><h2 className="font-bold">Request details</h2><p className="mt-3 text-sm text-zinc-600">{visualisation.items.length} frozen garment reference(s) were used.</p>{visualisation.model_version && <p className="mt-2 break-words text-xs text-zinc-500">Model: {visualisation.model_version}</p>}<button type="button" onClick={() => void download()} disabled={Boolean(action)} className="mt-5 flex min-h-11 w-full items-center justify-center gap-2 bg-black px-3 py-2 text-sm font-bold text-white disabled:opacity-50"><Download className="h-4 w-4" aria-hidden="true" /> {action === "download" ? "Preparing…" : "Download output"}</button><button type="button" onClick={() => void retry()} disabled={Boolean(action)} className="mt-3 flex min-h-11 w-full items-center justify-center gap-2 border-2 border-black px-3 py-2 text-sm font-bold disabled:opacity-50"><RefreshCw className="h-4 w-4" aria-hidden="true" /> {action === "retry" ? "Retrying…" : "Generate again"}</button></aside>
    </div>}
  </div></Layout>;
}

export default function OutfitVisualisationResultPage() { return <Suspense fallback={<Layout><div className="p-8 text-sm">Loading result...</div></Layout>}><ResultContent /></Suspense>; }
