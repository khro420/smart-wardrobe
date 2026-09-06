"use client";

import { FormEvent, Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import { cancelProcessingJob, confirmProcessingJob, getProcessingJob, reviewProcessingJob, type ProcessingItem, type ProcessingJob } from "@/lib/api";

const textValue = (value: unknown) => Array.isArray(value) ? value.join(", ") : typeof value === "string" ? value : "";
const inputClass = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:outline-offset-2 focus:outline-purple-800";
const categories = ["short_sleeve_top", "long_sleeve_top", "short_sleeve_outwear", "long_sleeve_outwear", "vest", "sling", "shorts", "trousers", "skirt", "short_sleeve_dress", "long_sleeve_dress", "vest_dress", "sling_dress"];

function CandidateReview({ item, disabled, onReview, onDirty }: {
  item: ProcessingItem;
  disabled: boolean;
  onReview: (update: Record<string, unknown>) => Promise<boolean>;
  onDirty: (id: string, dirty: boolean) => void;
}) {
  const [draft, setDraft] = useState({
    name: textValue(item.attributes.name) || item.detected_category.replaceAll("_", " "),
    category: textValue(item.attributes.reviewed_category) || item.detected_category,
    primary_colour: textValue(item.attributes.primary_colour),
    pattern: textValue(item.attributes.pattern),
    fit: textValue(item.attributes.fit), style: textValue(item.attributes.style),
    material: textValue(item.attributes.material), custom_tags: textValue(item.attributes.custom_tags),
    color_temperature: textValue(item.attributes.color_temperature) || "neutral",
    is_dominant: item.attributes.is_dominant === true,
    preferred_media: item.vtoff_media_id && item.preferred_media_id === item.vtoff_media_id ? "vtoff" : "crop",
  });
  const [dirty, setDirty] = useState(false);
  const change = (key: keyof typeof draft, value: string | boolean) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setDirty(true); onDirty(item.id, true);
  };
  const decide = async (decision: "accepted" | "rejected") => {
    const success = await onReview({
      item_id: item.id, decision,
      ...(decision === "accepted" ? {
        name: draft.name.trim(), category: draft.category,
        primary_colour: draft.primary_colour.trim() || null,
        pattern: draft.pattern.trim() || null,
        preferred_media: draft.preferred_media,
        attributes: { fit: draft.fit.trim() || null, style: draft.style.trim() || null,
          material: draft.material.trim() || null,
          custom_tags: draft.custom_tags.split(",").map((tag) => tag.trim()).filter(Boolean),
          color_temperature: draft.color_temperature, is_dominant: draft.is_dominant },
      } : {}),
    });
    if (success) { setDirty(false); onDirty(item.id, false); }
  };
  const submit = (event: FormEvent) => { event.preventDefault(); void decide("accepted"); };
  const fallback = item.attributes.source === "development fallback";

  return <article className="rounded-xl border border-slate-200 bg-white p-4" aria-label={`Candidate ${item.detected_category}`}>
    <form onSubmit={submit}>
      <fieldset disabled={disabled} className="min-w-0 space-y-4">
        <div className="flex items-start gap-4">
          <ProtectedImage mediaId={draft.preferred_media === "vtoff" && item.vtoff_media_id ? item.vtoff_media_id : item.crop_media_id} alt={`Candidate ${draft.name}`} className="h-28 w-28 shrink-0 rounded-lg bg-slate-100 object-contain" />
          <div className="min-w-0 flex-1">
            <h2 className="break-words font-semibold">{draft.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{fallback ? "Development preview — no AI segmentation" : `Detection confidence: ${Math.round(item.confidence * 100)}%`}</p>
            <p className="mt-2 text-sm font-medium" role="status">{dirty ? "Unsaved changes — accept to apply" : `Review: ${item.review_status}`}</p>
          </div>
        </div>
        <details className="rounded-lg border border-slate-200 p-3">
          <summary className="cursor-pointer text-sm font-semibold">Edit details and review image</summary>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm">Garment name<input required maxLength={100} value={draft.name} onChange={(e) => change("name", e.target.value)} className={inputClass} /></label>
            <label className="text-sm">Category<select aria-label="Category" value={draft.category} onChange={(e) => change("category", e.target.value)} className={inputClass}>
              {!categories.includes(draft.category) && <option value={draft.category}>{draft.category}</option>}
              {categories.map((category) => <option key={category} value={category}>{category.replaceAll("_", " ")}</option>)}
            </select></label>
            {([['primary_colour', 'Primary colour'], ['pattern', 'Pattern'], ['fit', 'Fit'], ['style', 'Style'], ['material', 'Material'], ['custom_tags', 'Tags (comma separated)']] as const).map(([key, label]) =>
              <label key={key} className="text-sm">{label}<input maxLength={key === "custom_tags" ? 500 : key === "primary_colour" || key === "pattern" ? 50 : 100} value={draft[key]} onChange={(e) => change(key, e.target.value)} placeholder="Not specified" className={inputClass} /></label>)}
            <label className="text-sm">Colour temperature<select value={draft.color_temperature} onChange={(event) => change("color_temperature", event.target.value)} className={inputClass}><option value="warm">Warm</option><option value="cool">Cool</option><option value="neutral">Neutral</option></select></label>
            <label className="flex items-center gap-2 self-end rounded-lg border border-slate-300 px-3 py-2 text-sm"><input type="checkbox" checked={draft.is_dominant} onChange={(event) => change("is_dominant", event.target.checked)} />One colour covers most of garment</label>
          </div>
          <p className="mt-3 text-xs text-slate-600">Colour and dominance are automated suggestions; all displayed details remain reviewable. Detection confidence does not establish attribute accuracy.</p>
          {item.vtoff_media_id ? <fieldset className="mt-4">
            <legend className="text-sm font-semibold">Compare and choose the image to save</legend>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {([{"value": "crop", "label": "Original segmentation crop", "mediaId": item.crop_media_id},
                {"value": "vtoff", "label": "AI-generated VTOFF reconstruction", "mediaId": item.vtoff_media_id}] as const).map((choice) =>
                <label key={choice.value} className={`cursor-pointer rounded-lg border p-3 ${draft.preferred_media === choice.value ? "border-[#6d335b] bg-purple-50" : "border-slate-200"}`}>
                  <input type="radio" name={`preferred-media-${item.id}`} value={choice.value} checked={draft.preferred_media === choice.value} onChange={(e) => change("preferred_media", e.target.value)} className="mr-2" />
                  <span className="text-sm font-medium">{choice.label}</span>
                  <ProtectedImage mediaId={choice.mediaId} alt={`${choice.label} for ${draft.name}`} className="mt-2 aspect-square w-full rounded bg-[linear-gradient(45deg,#e2e8f0_25%,transparent_25%),linear-gradient(-45deg,#e2e8f0_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#e2e8f0_75%),linear-gradient(-45deg,transparent_75%,#e2e8f0_75%)] bg-[length:20px_20px] object-contain" />
                </label>)}
            </div>
            <p className="mt-2 text-xs text-amber-800">The VTOFF image is synthetic and may invent hidden logos, texture, shape, or colour. Compare it with the observed segmentation crop before selecting it.</p>
          </fieldset> : <p className="mt-4 text-xs text-slate-600">AI VTOFF is unavailable or failed for this item. You can review and save the retained segmentation crop.</p>}
          {item.mask_media_id && <details className="mt-3 text-sm"><summary className="cursor-pointer">View segmentation evidence</summary>
            <ProtectedImage mediaId={item.mask_media_id} alt="Garment mask in the uploaded image coordinates" className="mt-2 max-h-64 w-full bg-slate-900 object-contain" />
            <p className="mt-2 text-xs">Bounding box (left, top, right, bottom): {item.bounding_box?.map((n) => Math.round(n)).join(", ")}</p>
          </details>}
        </details>
        <div className="flex flex-wrap gap-3">
          <button type="submit" className="rounded-lg bg-[#6d335b] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Accept candidate</button>
          <button type="button" onClick={() => void decide("rejected")} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:opacity-50">Reject candidate</button>
        </div>
      </fieldset>
    </form>
  </article>;
}

function ExtractionResultsContent() {
  const jobId = useSearchParams().get("job");
  const [job, setJob] = useState<ProcessingJob>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const actionLock = useRef(false);
  const [dirtyIds, setDirtyIds] = useState<Set<string>>(new Set());
  const [outfitName, setOutfitName] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const next = await getProcessingJob(jobId);
        if (active) { setJob(next); setError(""); if (["queued", "processing"].includes(next.status)) timer = setTimeout(load, 900); }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Could not load the job."); }
    };
    void load();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, reload]);
  const review = async (update: Record<string, unknown>) => {
    if (!jobId || actionLock.current) return false;
    actionLock.current = true; setBusy(true); setError("");
    try { setJob(await reviewProcessingJob(jobId, [update])); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Could not update review."); return false; }
    finally { actionLock.current = false; setBusy(false); }
  };
  const accepted = job?.items.filter((item) => item.review_status === "accepted").map((item) => item.id) ?? [];
  const save = async (mode: "garments" | "outfit") => {
    if (!jobId || actionLock.current || !accepted.length || dirtyIds.size) return;
    actionLock.current = true; setBusy(true); setError("");
    try { await confirmProcessingJob(jobId, accepted, mode, outfitName.trim()); window.location.assign("/wardrobe"); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not save candidates."); }
    finally { actionLock.current = false; setBusy(false); }
  };
  const cancel = async () => {
    if (!jobId || actionLock.current) return;
    actionLock.current = true; setBusy(true); setError("");
    try { await cancelProcessingJob(jobId); setReload((value) => value + 1); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not cancel processing."); }
    finally { actionLock.current = false; setBusy(false); }
  };
  const processing = jobId && (!job || ["queued", "processing"].includes(job.status));
  return <Layout><div className="mx-auto max-w-4xl space-y-6">
    <div><h1 className="text-2xl font-bold">Review garment candidates</h1><p className="mt-2 text-sm text-slate-600">Review and accept each item you want to save. Pending and rejected items stay out of your wardrobe.</p></div>
    {(error || !jobId) && <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800"><p>{error || "No processing job was selected."}</p>{jobId && <button onClick={() => setReload((value) => value + 1)} className="mt-2 underline">Retry loading</button>} <Link href="/auth" className="underline">Sign in</Link></div>}
    {processing && !error && <p role="status" className="rounded-lg bg-white p-6">{job?.status === "processing" ? "Analysing garments. This may take a moment…" : "Loading processing status…"}</p>}
    {job?.status === "failed" && <p role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-rose-800">{job.error_message || "Processing failed. Please try another image."}</p>}
    {job?.status === "cancelled" && <p role="status">Processing cancelled. Your existing wardrobe has not changed.</p>}
    {job?.status === "completed" && <p role="status">These candidates have already been saved. <Link href="/wardrobe" className="underline">Open wardrobe</Link></p>}
    {job?.status === "review_required" && <>
      <div className="space-y-4">{job.items.map((item) => <CandidateReview key={item.id} item={item} disabled={busy} onReview={review} onDirty={(id, dirty) => setDirtyIds((current) => { const next = new Set(current); if (dirty) next.add(id); else next.delete(id); return next; })} />)}</div>
      <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
        <p className="font-semibold">{accepted.length} of {job.items.length} candidates accepted</p>
        {dirtyIds.size > 0 && <p className="text-sm text-amber-800">Accept or reject edited candidates before saving.</p>}
        <label className="block text-sm">Outfit name (required when saving as an outfit)<input value={outfitName} onChange={(e) => setOutfitName(e.target.value)} maxLength={100} className={inputClass} placeholder="For example, Campus outfit" disabled={busy} /></label>
        <div className="flex flex-wrap gap-3">
          <button disabled={busy || !accepted.length || dirtyIds.size > 0} onClick={() => void save("garments")} className="rounded-lg bg-[#6d335b] px-4 py-3 text-sm font-semibold text-white disabled:opacity-40">Save selected garments</button>
          <button disabled={busy || !accepted.length || dirtyIds.size > 0 || !outfitName.trim()} onClick={() => void save("outfit")} className="rounded-lg border border-slate-400 px-4 py-3 text-sm font-semibold disabled:opacity-40">Save as outfit</button>
        </div>
      </div>
    </>}
    <div className="flex flex-wrap gap-4 text-sm">
      {job && ["queued", "processing", "review_required"].includes(job.status) && <button disabled={busy} onClick={() => void cancel()} className="underline">Cancel this operation</button>}
      <Link href="/extract" className="underline">Choose another photo</Link>
      <Link href="/wardrobe" className="underline">Back to wardrobe</Link>
    </div>
  </div></Layout>;
}

export default function ExtractionResultsPage() {
  return <Suspense fallback={<Layout><p role="status">Loading processing job…</p></Layout>}><ExtractionResultsContent /></Suspense>;
}
