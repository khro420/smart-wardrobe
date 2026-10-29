"use client";

import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import { getWardrobeQuota, wardrobeCapacityText, type WardrobeQuota, cancelProcessingJob, confirmProcessingJob, getProcessingJob, reviewProcessingJob, type ProcessingItem, type ProcessingJob } from "@/lib/api";

const textValue = (value: unknown) => Array.isArray(value) ? value.join(", ") : typeof value === "string" ? value : "";
const inputClass = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:outline-offset-2 focus:outline-purple-800";
const categories = ["short_sleeve_top", "long_sleeve_top", "short_sleeve_outwear", "long_sleeve_outwear", "vest", "sling", "shorts", "trousers", "skirt", "short_sleeve_dress", "long_sleeve_dress", "vest_dress", "sling_dress"];
const patterns = ["plain", "abstract", "cartoon", "letters, numbers", "camouflage", "check", "dot", "fair isle", "floral", "geometric", "paisley", "stripe", "houndstooth", "herringbone", "chevron", "argyle", "leopard", "snakeskin", "cheetah", "peacock", "zebra", "giraffe", "toile de jouy", "plant"];
const silhouettes = ["asymmetrical", "symmetrical", "peplum", "circle", "flare", "fit and flare", "trumpet", "mermaid", "balloon", "bell", "bell bottom", "bootcut", "peg", "pencil", "straight", "a-line", "tent", "baggy", "wide leg", "high low", "curved", "tight", "regular", "loose", "oversized"];
const necklines = ["collarless", "asymmetric", "crew", "round", "v-neck", "surplice", "oval", "u-neck", "sweetheart", "queen anne", "boat", "scoop", "square", "plunging", "keyhole", "halter", "crossover", "choker", "high", "turtle", "cowl", "straight across", "illusion", "off-the-shoulder", "one shoulder"];
const sleeveLengths = ["sleeveless", "short", "elbow-length", "wrist-length"];
const styles = ["casual", "classic", "formal", "minimal", "smart casual", "sporty", "streetwear", "vintage", "bohemian"];
const materials = ["cotton", "denim", "leather", "linen", "silk", "synthetic", "wool", "not sure"];

function CandidateReview({ item, disabled, onReview, onDirty, automatic = false }: {
  automatic?: boolean;
  item: ProcessingItem;
  disabled: boolean;
  onReview: (update: Record<string, unknown>) => Promise<boolean>;
  onDirty: (id: string, dirty: boolean) => void;
}) {
  const visible = item.attributes.fashionpedia_visible_attributes as Record<string, { value?: string }> | undefined;
  const suggestion = (field: string) => visible?.[field]?.value ?? "";
  const clean = (value: string) => value.replace(" (pattern)", "").replace(" (length)", "").replace(" (fit)", "").replace(" (neck)", "").replace(" (neckline)", "");
  const supportsUpperDetails = !["shorts", "trousers", "skirt"].includes(item.detected_category);
  const [draft, setDraft] = useState({
    name: textValue(item.attributes.name) || item.detected_category.replaceAll("_", " "),
    category: textValue(item.attributes.reviewed_category) || item.detected_category,
    primary_colour: textValue(item.attributes.primary_colour),
    pattern: textValue(item.attributes.pattern) || clean(suggestion("pattern")),
    fit: textValue(item.attributes.fit) || clean(suggestion("silhouette")), style: textValue(item.attributes.style),
    material: textValue(item.attributes.material), neckline: supportsUpperDetails ? clean(suggestion("neckline")) : "", sleeve_length: supportsUpperDetails ? clean(suggestion("sleeve_length")) : "",
    color_temperature: textValue(item.attributes.color_temperature) || "neutral",
    is_dominant: item.attributes.is_dominant === true,
    preferred_media: item.vtoff_media_id && item.preferred_media_id === item.vtoff_media_id ? "vtoff" : "crop",
  });
  const [styleChoice, setStyleChoice] = useState("__keep");
  const [dirty, setDirty] = useState(false);
  const change = (key: keyof typeof draft, value: string | boolean) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setDirty(true); onDirty(item.id, true);
  };
  const decide = async (decision: "accepted" | "rejected") => {
    const reviewedValue = (key: "fit" | "style" | "material", value: string) =>
      Array.isArray(item.attributes[key]) && value === textValue(item.attributes[key]) ? item.attributes[key] : value.trim() || null;
    const existingTags = Array.isArray(item.attributes.custom_tags) ? item.attributes.custom_tags.filter((tag): tag is string => typeof tag === "string") : typeof item.attributes.custom_tags === "string" ? [item.attributes.custom_tags] : [];
    const success = await onReview({
      item_id: item.id, decision,
      ...(decision === "accepted" ? {
        name: draft.name.trim(), category: draft.category,
        ...(item.style_confirmation && styles.includes(styleChoice) ? { style_confirmation: { contract: "owner-style-confirmation-1.0.0", expected_revision: item.style_confirmation.revision, style: styleChoice } } : {}),
        primary_colour: draft.primary_colour.trim() || null,
        pattern: draft.pattern.trim() || null,
        preferred_media: draft.preferred_media,
        attributes: { fit: reviewedValue("fit", draft.fit),
          ...(styleChoice === "__keep" ? {} : { style: styleChoice === "__unknown" ? null : styleChoice === "__empty" ? [] : styleChoice }),
          material: reviewedValue("material", draft.material),
          custom_tags: [...new Set([...existingTags, ...[supportsUpperDetails && draft.neckline && `neckline: ${draft.neckline}`, supportsUpperDetails && draft.sleeve_length && `sleeve length: ${draft.sleeve_length}`, draft.fit && `silhouette: ${draft.fit}`].filter((value): value is string => Boolean(value))])],
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
            <p className="mt-2 text-sm font-medium" role="status">{dirty ? automatic ? "Unsaved corrections" : "Unsaved changes — accept to apply" : `Review: ${item.review_status}`}</p>
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
            <label className="text-sm">Primary colour<input maxLength={50} value={draft.primary_colour} onChange={(e) => change("primary_colour", e.target.value)} placeholder="Not specified" className={inputClass} /></label>
            {([['pattern', 'Pattern', patterns], ['fit', 'Fit (visible silhouette)', silhouettes], ['material', 'Material', materials], ...(supportsUpperDetails ? [['neckline', 'Neckline', necklines], ['sleeve_length', 'Sleeve length', sleeveLengths]] as const : [])] as const).map(([key, label, options]) => <label key={key} className="text-sm">{label}<select value={draft[key]} onChange={(e) => change(key, e.target.value)} className={inputClass}><option value="">Not specified</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>)}
            <label className="text-sm">Style<select value={styleChoice} onChange={(event) => { setStyleChoice(event.target.value); setDirty(true); onDirty(item.id, true); }} className={inputClass}><option value="__keep">Preserve current value: {item.attributes.style == null ? "Unknown" : Array.isArray(item.attributes.style) && item.attributes.style.length === 0 ? "No assigned tags (empty set)" : textValue(item.attributes.style) || "Invalid stored value"}</option><option value="__unknown">Unknown</option><option value="__empty">No assigned tags (empty set)</option>{styles.map((style) => <option key={style} value={style}>{style}</option>)}</select></label>
            <p className="text-xs text-slate-600 sm:col-span-2">{item.style_confirmation ? "Style is optional for storage. Ordinary suggestions can use a supported saved style provisionally without review. Explicitly selecting a style also records your optional confirmation; preserving a suggestion does not." : "This backend does not yet support style confirmation during addition. Saved styles may still need the separate contextual review."} {item.style_confirmation?.current && "Your selected style is confirmed for this candidate; save it to your wardrobe to use it."}</p>
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
          <button type="submit" className="rounded-lg bg-[#6d335b] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{automatic ? "Save corrections" : "Accept candidate"}</button>
          <button type="button" onClick={() => void decide("rejected")} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:opacity-50">Reject candidate</button>
        </div>
      </fieldset>
    </form>
  </article>;
}

function ExtractionResultsContent() {
  const params = useSearchParams();
  const jobId = params.get("job");
  const [job, setJob] = useState<ProcessingJob>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyMessage, setBusyMessage] = useState("");
  const actionLock = useRef(false);
  const [dirtyIds, setDirtyIds] = useState<Set<string>>(new Set());
  const [outfitName, setOutfitName] = useState("");
  const [reload, setReload] = useState(0);
  const [excludedIds, setExcludedIds] = useState<Set<string>>(new Set());
  const [quota, setQuota] = useState<WardrobeQuota>();
  const quotaSequence = useRef(0);
  const refreshQuota = useCallback(async () => {
    const sequence = ++quotaSequence.current;
    try { const next = await getWardrobeQuota(); if (sequence === quotaSequence.current) setQuota(next); }
    catch { if (sequence === quotaSequence.current) setQuota(undefined); }
  }, []);
  useEffect(() => {
    const refresh = () => { if (document.visibilityState === "visible") void refreshQuota(); };
    const initial = window.setTimeout(() => void refreshQuota(), 0);
    window.addEventListener("focus", refresh); document.addEventListener("visibilitychange", refresh);
    return () => { window.clearTimeout(initial); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [refreshQuota]);

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let preparedPolls = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const next = await getProcessingJob(jobId);
        if (active) {
          setJob(next); setError("");
          // Processing commits the prepared batch before the writer finalises it.
          // Briefly follow that transition; a failed writer still exposes Retry.
          const finalising = next.status === "review_required" && next.admission?.mode === "automatic_structural_v1" && next.admission.state === "prepared";
          if (["queued", "processing"].includes(next.status) || (finalising && preparedPolls++ < 3)) timer = setTimeout(load, 900);
        }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Could not load the job."); }
    };
    void load();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, reload]);
  const review = async (update: Record<string, unknown>) => {
    if (!jobId || actionLock.current) return false;
    actionLock.current = true; setBusy(true); setBusyMessage("Saving your review decision…"); setError("");
    try { setJob(await reviewProcessingJob(jobId, [update])); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Could not update review."); return false; }
    finally { actionLock.current = false; setBusy(false); setBusyMessage(""); }
  };
  const automaticMode = job?.admission?.mode === "automatic_structural_v1" || ((!job || !job.items.length) && params.get("admission_mode") === "automatic_structural_v1");
  const accepted = job?.items.filter((item) => item.review_status === "accepted").map((item) => item.id) ?? [];
  const selected = accepted.filter((id) => !excludedIds.has(id));
  const exceedsCapacity = quota !== undefined && selected.length > quota.remaining;
  const save = async (mode: "garments" | "outfit") => {
    if (!jobId || actionLock.current || !selected.length || dirtyIds.size || exceedsCapacity) return;
    actionLock.current = true; setBusy(true); setBusyMessage(mode === "outfit" ? "Saving your outfit…" : "Saving selected garments…"); setError("");
    try { await confirmProcessingJob(jobId, selected, mode, outfitName.trim()); window.location.assign("/wardrobe"); }
    catch (e) {
      setError(e instanceof Error ? e.message : "Could not save candidates."); void refreshQuota();
      // A lost response may follow a successful commit; reconcile without resubmitting.
      try { setJob(await getProcessingJob(jobId)); } catch { /* Preserve the original save error. */ }
    }
    finally { actionLock.current = false; setBusy(false); setBusyMessage(""); }
  };
  const retryAutomatic = async () => {
    if (!jobId || !job || actionLock.current || dirtyIds.size) return;
    actionLock.current = true; setBusy(true); setError(""); setBusyMessage("Retrying automatic saving…");
    try { await confirmProcessingJob(jobId, job.items.map(item => item.id), "garments", undefined, "automatic_structural_v1"); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not automatically save garments."); }
    finally { try { setJob(await getProcessingJob(jobId)); await refreshQuota(); } catch { /* Preserve action error. */ } actionLock.current = false; setBusy(false); setBusyMessage(""); }
  };
  const cancel = async () => {
    if (!jobId || actionLock.current) return;
    actionLock.current = true; setBusy(true); setBusyMessage("Cancelling processing…"); setError("");
    try { await cancelProcessingJob(jobId); setReload((value) => value + 1); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not cancel processing."); }
    finally { actionLock.current = false; setBusy(false); setBusyMessage(""); }
  };
  const processing = jobId && (!job || ["queued", "processing"].includes(job.status));
  return <Layout><div className="mx-auto max-w-4xl space-y-6">
    <div><h1 className="text-2xl font-bold">{automaticMode ? "Automatic garment addition" : "Processing garment candidates"}</h1><p className="mt-2 text-sm text-slate-600">{automaticMode ? "Complete garments are saved automatically. Correct only genuinely missing details; style review is optional." : "This submission uses the legacy review flow. Review and accept the items you want to save."}</p></div>
    {params.get("automatic_unavailable") === "1" && <p role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4">This backend did not acknowledge automatic garment admission. Automatic saving is unavailable; this job uses its existing legacy review flow. A backend update/restart is needed to enable the new flow.</p>}
    {(error || !jobId) && <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800"><p>{error || "No processing job was selected."}</p>{jobId && <button onClick={() => setReload((value) => value + 1)} className="mt-2 underline">Retry loading</button>} <Link href="/auth" className="underline">Sign in</Link></div>}
    {busy && <p role="status" aria-live="polite" className="rounded-lg border border-purple-200 bg-purple-50 p-3 text-sm text-purple-900">{busyMessage}</p>}
    <section aria-label="Wardrobe capacity" className="rounded-lg border border-slate-200 p-3 text-sm">
      <p role="status" aria-live="polite">{quota ? wardrobeCapacityText(quota) : "Capacity unavailable"}</p>
      <p className="text-xs text-slate-600">Non-archived entries include unavailable items. Pending uploads do not reserve spaces. Archiving a garment releases its space.</p>
      <button type="button" onClick={() => void refreshQuota()} className="mt-1 underline">Refresh capacity</button>
    </section>
    {processing && !error && <section role="status" aria-live="polite" className="rounded-lg border-2 border-dashed border-slate-400 bg-white p-6"><p className="font-semibold capitalize">{job?.status ?? "Loading"}</p><p className="mt-1 text-sm text-slate-600">{job?.progress_message ?? "Loading processing status…"}</p><div className="mt-4"><div className="flex justify-between text-xs font-semibold"><span>Image processing</span><span>{job?.progress_percent ?? 0}%</span></div><div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={job?.progress_percent ?? 0}><div className="h-full bg-[#6d335b] transition-all duration-500" style={{ width: `${job?.progress_percent ?? 0}%` }} /></div><p className="mt-2 text-xs text-slate-500">You can keep this page open; it updates automatically as each garment is prepared.</p></div></section>}
    {job?.status === "failed" && <p role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-rose-800">{job.error_message || "Processing failed. Please try another image."}</p>}
    {job?.status === "cancelled" && <p role="status">Processing cancelled. Your existing wardrobe has not changed.</p>}
    {job?.status === "completed" && <p role="status">{automaticMode ? `${job.admission?.garment_ids.length ?? 0} garment(s) automatically added. Saved attributes may be unreviewed.` : "These candidates have already been saved."} <Link href="/wardrobe" className="underline">Open wardrobe</Link></p>}
    {job?.status === "review_required" && <>
      {automaticMode && <section aria-label="Automatic saving outcome" className="rounded-xl border border-amber-300 bg-amber-50 p-4">
        <h2 className="font-semibold">Garments have not been added yet</h2>
        <p className="mt-2 text-sm">{job.admission?.reason === "category_missing_or_unsupported" ? "A supported category is missing. Correct the category and save corrections once. A missing style is not required for storage, but can prevent a style-dependent recommendation." : job.admission?.reason === "WardrobeQuotaExceeded" ? "This complete batch does not fit the 100 non-archived garment limit. You may archive garments or cancel this operation. No partial batch was saved." : "The complete batch is not ready to save. Check the processing details and any rejected item; all items must be valid. No partial batch was saved."}</p>
        <button disabled={busy || dirtyIds.size > 0} onClick={() => void retryAutomatic()} className="mt-3 min-h-11 rounded-lg border border-slate-500 px-4 text-sm font-semibold disabled:opacity-40">Retry automatic saving</button>
      </section>}
      <div className="space-y-4">{job.items.map((item) => <CandidateReview key={item.id} item={item} automatic={automaticMode} disabled={busy} onReview={review} onDirty={(id, dirty) => setDirtyIds((current) => { const next = new Set(current); if (dirty) next.add(id); else next.delete(id); return next; })} />)}</div>
      {!automaticMode && (<div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
        <p className="font-semibold">{accepted.length} of {job.items.length} candidates accepted</p>
        <fieldset disabled={busy} className="space-y-2"><legend className="font-semibold">Choose accepted garments to save</legend>
          {job.items.filter((item) => item.review_status === "accepted").map((item, index) => <label key={item.id} className="flex items-center gap-2">
            <input type="checkbox" data-testid={`save-candidate-${item.id}`} checked={!excludedIds.has(item.id)} onChange={() => setExcludedIds((current) => { const next = new Set(current); if (next.has(item.id)) next.delete(item.id); else next.add(item.id); return next; })} />
            Save {typeof item.attributes.name === "string" ? item.attributes.name : item.detected_category.replaceAll("_", " ")} ({index + 1})
          </label>)}
        </fieldset>
        <p role="status">{selected.length} selected to save{quota ? `; ${quota.remaining} space(s) remaining.` : "; capacity will be checked when saving."}</p>
        {exceedsCapacity && <p className="text-amber-800">Select fewer candidates or archive garments before saving. <Link href="/wardrobe" className="underline">Open wardrobe</Link></p>}
        <p className="text-sm text-slate-600">Only these selected garments will be saved. This completes the job; unselected candidates will not be saved.</p>
        {dirtyIds.size > 0 && <p className="text-sm text-amber-800">Accept or reject edited candidates before saving.</p>}
        <label className="block text-sm">Outfit name (required when saving as an outfit)<input value={outfitName} onChange={(e) => setOutfitName(e.target.value)} maxLength={100} className={inputClass} placeholder="For example, Campus outfit" disabled={busy} /></label>
        <div className="flex flex-wrap gap-3">
          <button disabled={busy || !selected.length || exceedsCapacity || dirtyIds.size > 0} onClick={() => void save("garments")} className="rounded-lg bg-[#6d335b] px-4 py-3 text-sm font-semibold text-white disabled:opacity-40">Save selected garments</button>
          <button disabled={busy || !selected.length || exceedsCapacity || dirtyIds.size > 0 || !outfitName.trim()} onClick={() => void save("outfit")} className="rounded-lg border border-slate-400 px-4 py-3 text-sm font-semibold disabled:opacity-40">Save as outfit</button>
        </div>
      </div>)}
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
