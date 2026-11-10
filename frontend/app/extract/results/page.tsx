"use client";
import VerifiedSubtypeFields from "@/components/VerifiedSubtypeFields";
import { useWearerCategoryEligibility } from "@/lib/wearer-category-eligibility";

import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import { DESCRIPTION_FIELDS, descriptionUpdate, type DescriptionView, type DescriptionDraft } from "@/lib/api";
import { getHistoricalProcessingJob, getHistoricalProcessingJobs, getWardrobeQuota, wardrobeCapacityText, type WardrobeQuota, cancelProcessingJob, confirmProcessingJob, createMirroredReconstruction, getProcessingJob, reviewProcessingJob, type ProcessingItem, type ProcessingJob } from "@/lib/api";

const textValue = (value: unknown) => Array.isArray(value) ? value.join(", ") : typeof value === "string" ? value : "";
const inputClass = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:outline-offset-2 focus:outline-purple-800";
const categories = ["short_sleeve_top", "long_sleeve_top", "short_sleeve_outwear", "long_sleeve_outwear", "vest", "sling", "shorts", "trousers", "skirt", "short_sleeve_dress", "long_sleeve_dress", "vest_dress", "sling_dress"];
const patterns = ["plain", "abstract", "cartoon", "letters, numbers", "camouflage", "check", "dot", "fair isle", "floral", "geometric", "paisley", "stripe", "houndstooth", "herringbone", "chevron", "argyle", "leopard", "snakeskin", "cheetah", "peacock", "zebra", "giraffe", "toile de jouy", "plant"];
const silhouettes = ["asymmetrical", "symmetrical", "peplum", "circle", "flare", "fit and flare", "trumpet", "mermaid", "balloon", "bell", "bell bottom", "bootcut", "peg", "pencil", "straight", "a-line", "tent", "baggy", "wide leg", "high low", "curved", "tight", "regular", "loose", "oversized"];
const necklines = ["collarless", "asymmetric", "crew", "round", "v-neck", "surplice", "oval", "u-neck", "sweetheart", "queen anne", "boat", "scoop", "square", "plunging", "keyhole", "halter", "crossover", "choker", "high", "turtle", "cowl", "straight across", "illusion", "off-the-shoulder", "one shoulder"];
const sleeveLengths = ["sleeveless", "short", "elbow-length", "wrist-length"];
const styles = ["casual", "classic", "formal", "minimal", "smart casual", "sporty", "streetwear", "vintage", "bohemian"];
const materials = ["cotton", "denim", "leather", "linen", "silk", "synthetic", "wool", "not sure"];


function DescriptionControls({ view, draft, onChange, id, readOnly = false }: { view: DescriptionView; draft: DescriptionDraft; onChange: (next: DescriptionDraft) => void; id: string; readOnly?: boolean }) {
  const categoryPolicy = useWearerCategoryEligibility();
  const display = (value: unknown): string => Array.isArray(value) ? value.map(display).join("; ") : value && typeof value === "object" && "hex" in value ? `${String(value.hex)} (coverage ${"coverage" in value && value.coverage != null ? String(value.coverage) : "unknown"})` : typeof value === "boolean" ? value ? "Yes" : "No" : typeof value === "string" ? value : "No recorded value";
  const update = (field: string, kind: DescriptionDraft[string]["kind"], value?: unknown) => {
    const next = {...draft};
    if (kind === "keep") delete next[field]; else next[field] = {kind, ...(kind === "set" ? {value} : {})};
    onChange(next);
  };
  const initial = (field: typeof DESCRIPTION_FIELDS[number]): unknown => {
    const values = view.evidence.fields[field.id]?.canonical_values ?? [];
    if (field.kind === "set" || field.kind === "palette") return values;
    if (field.kind === "tags") return values.map(String).join("\n");
    if (field.kind === "boolean") return typeof values[0] === "boolean" ? String(values[0]) : "";
    return typeof values[0] === "string" ? values[0] : "";
  };
  const category = draft.category?.kind === "set" ? draft.category.value : view.evidence.fields.category?.canonical_values[0];
  return <section className="min-w-0 space-y-3 [overflow-wrap:anywhere]" aria-label="Optional recorded descriptions">
    <p className="text-sm">{readOnly ? "Stored descriptions are read-only." : "Optional recorded descriptions. Keep leaves a value unchanged."} Suggestions and saved values with unverified sources are separate from your explicit selections. Visible silhouette does not establish physical fit; material does not establish comfort or fibre verification.</p>
    <div className="grid min-w-0 gap-3 sm:grid-cols-2">{DESCRIPTION_FIELDS.map(field => {
      const record = view.evidence.fields[field.id]; const action = draft[field.id]; const kind = action?.kind ?? "keep";
      const inapplicable = (field.id === "neckline" || field.id === "sleeve_length") && typeof category === "string" && ["shorts", "trousers", "skirt"].includes(category);
      const origin = record?.selected?.origin === "owner_selected" ? "Your recorded selection" : record?.selected?.origin === "owner_reported_label" ? "Reported label" : "Saved value; source unverified";
      const value = action?.value;
      const palette = Array.isArray(value) ? value as {hex: string; coverage: string | null}[] : [];
      return <fieldset key={field.id} disabled={inapplicable} className="min-w-0 space-y-2 rounded-lg border border-slate-300 p-3 disabled:opacity-60">
        <legend className="text-sm font-semibold">{field.label}</legend>
        <p className="text-xs">{record?.state ?? "Unavailable"}: {display(record?.canonical_values?.length ? record.canonical_values : null)}. {origin}.</p>
        {record?.applicability === "unknown" && <p className="text-xs">Applicability is unknown until the garment role is established.</p>}
        {record?.selected?.value != null && ["Unrecognized", "Unsure", "Unspecified"].includes(record.state) && <p className="text-xs">Original recorded value: {display(record.selected.value)}. It is not treated as a supported positive fact.</p>}
        {record?.suggestion && <p className="text-xs text-slate-600">Model suggestion: {display(record.suggestion.value)}. Source vocabulary is not verified; this is not your selected value.</p>}
        {readOnly ? null : inapplicable ? <p className="text-xs">Not applicable to a bottom garment.</p> : <>
          <label className="block text-xs">Action<select aria-label={`${field.label} action`} value={kind} onChange={event => update(field.id, event.target.value as DescriptionDraft[string]["kind"], initial(field))} className="mt-1 min-h-11 w-full border border-slate-400 bg-white px-2">
            <option value="keep">Keep current value</option><option value="set">Record a value</option>{field.clear && <option value="clear">Unknown / clear recorded value</option>}{field.empty && <option value="empty">Record an empty set</option>}{field.id === "material" && <option value="unsure">Not sure</option>}
          </select></label>
          {kind === "set" && <>
            {field.kind === "set" ? <label className="block text-xs">Recorded values (multiple allowed)<select multiple aria-label={`${field.label} values`} value={Array.isArray(value) ? value as string[] : []} onChange={event => update(field.id, "set", Array.from(event.target.selectedOptions,option=>option.value))} className="mt-1 min-h-28 w-full border border-slate-400 bg-white p-2">{field.options.map(option=><option key={option} value={option}>{option}</option>)}</select></label>
            : field.kind === "enum" || field.kind === "boolean" ? <select aria-label={`${field.label} value`} value={typeof value === "string" ? value : ""} onChange={event=>update(field.id,"set",event.target.value)} className="min-h-11 w-full border border-slate-400 bg-white px-2"><option value="">Choose a recorded value</option>{(field.kind === "boolean" ? ["true","false"] : field.options).filter(option => field.id !== "category" || categoryPolicy.permits(option) || option === value).map(option=><option disabled={field.id === "category" && !categoryPolicy.permits(option)} key={option} value={option}>{option === "true" ? "Yes, I observed this" : option === "false" ? "No, I observed this" : option}</option>)}</select>
            : field.kind === "palette" ? <div className="space-y-2">{palette.map((entry,index)=><div key={index} className="space-y-1 border border-slate-200 p-2"><label className="block text-xs">Exact hex colour<input aria-label={`Palette colour ${index+1}`} maxLength={7} value={entry.hex} onChange={event=>update(field.id,"set",palette.map((p,i)=>i===index ? {...p,hex:event.target.value} : p))} placeholder="#123abc" className="min-h-11 w-full border border-slate-400 px-2" /></label><label className="block text-xs">Recorded coverage 0–1 (blank means unknown)<input aria-label={`Palette coverage ${index+1}`} inputMode="decimal" value={entry.coverage ?? ""} onChange={event=>update(field.id,"set",palette.map((p,i)=>i===index ? {...p,coverage:event.target.value || null} : p))} className="min-h-11 w-full border border-slate-400 px-2" /></label><button type="button" onClick={()=>update(field.id,"set",palette.filter((_,i)=>i!==index))} className="min-h-11 border border-slate-400 px-2">Remove palette entry {index+1}</button></div>)}<button type="button" disabled={palette.length>=5} onClick={()=>update(field.id,"set",[...palette,{hex:"",coverage:null}])} className="min-h-11 border border-slate-400 px-2">Add palette entry</button></div>
            : field.kind === "tags" ? <label className="block text-xs">One literal tag per line<textarea aria-label="Literal descriptive tags values" value={typeof value === "string" ? value : ""} onChange={event=>update(field.id,"set",event.target.value)} className="mt-1 min-h-24 w-full border border-slate-400 p-2" /><span>Existing suitability restrictions stay in their separate controls.</span></label>
            : <><input aria-label={`${field.label} value`} list={field.kind === "colour" ? `${id}-${field.id}` : undefined} maxLength={field.id === "garment_name" ? 100 : 50} value={typeof value === "string" ? value : ""} onChange={event=>update(field.id,"set",event.target.value)} placeholder={field.kind === "colour" ? "Named colour or exact #RRGGBB" : "Recorded value"} className="min-h-11 w-full border border-slate-400 px-2" />{field.kind === "colour" && <datalist id={`${id}-${field.id}`}>{field.options.map(option=><option key={option} value={option} />)}</datalist>}</>}
          </>}
        </>}
      </fieldset>;
    })}</div>
    {!readOnly && <button type="button" onClick={()=>onChange({})} className="min-h-11 rounded border border-slate-400 px-3">Cancel description changes</button>}
  </section>;
}

function CandidateReview({ item, disabled, onReview, onCreateMirror, onDirty, automatic = false }: {
  automatic?: boolean;
  item: ProcessingItem;
  disabled: boolean;
  onReview: (update: Record<string, unknown>) => Promise<boolean>;
  onCreateMirror: (side?: "left" | "right") => Promise<boolean>;
  onDirty: (id: string, dirty: boolean) => void;
}) {
  const categoryPolicy = useWearerCategoryEligibility();
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
    preferred_media: item.mirror_media_id && item.preferred_media_id === item.mirror_media_id ? "mirror" : item.vtoff_media_id && item.preferred_media_id === item.vtoff_media_id ? "vtoff" : "crop",
  });
  const [styleChoice, setStyleChoice] = useState("__keep");
  const typedDescription = item.description?.editable === true && item.description.update_contract === "garment-description-update-1.0.0";
  const [descriptionDraft, setDescriptionDraft] = useState<DescriptionDraft>({});
  const [descriptionRevision, setDescriptionRevision] = useState(item.description?.revision ?? "");
  const [confirmDescriptionStyle, setConfirmDescriptionStyle] = useState(false);
  const [descriptionError, setDescriptionError] = useState("");

  const [dirty, setDirty] = useState(false);
  const change = (key: keyof typeof draft, value: string | boolean) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setDirty(true); onDirty(item.id, true);
  };
  const decide = async (decision: "accepted" | "rejected") => {
    if (typedDescription && item.description) {
      try {
        const action = decision === "accepted" ? descriptionUpdate(item.description, descriptionDraft, descriptionRevision) : undefined;
        const selectedStyle = action?.operations.style;
        const styleValue = selectedStyle?.kind === "set" && Array.isArray(selectedStyle.value) && selectedStyle.value.length === 1 ? selectedStyle.value[0] : undefined;
        const currentMedia = item.mirror_media_id && item.preferred_media_id === item.mirror_media_id ? "mirror" : item.vtoff_media_id && item.preferred_media_id === item.vtoff_media_id ? "vtoff" : "crop";
        const success = await onReview({item_id:item.id,decision,
          ...(action ? {description_update:action} : {}),
          ...(decision === "accepted" && draft.preferred_media !== currentMedia ? {preferred_media:draft.preferred_media} : {}),
          ...(decision === "accepted" && confirmDescriptionStyle && typeof styleValue === "string" && item.style_confirmation ? {style_confirmation:{contract:"owner-style-confirmation-1.0.0",expected_revision:item.style_confirmation.revision,style:styleValue}} : {})});
        if (success) { setDescriptionDraft({}); setConfirmDescriptionStyle(false); setDescriptionError(""); setDirty(false); onDirty(item.id,false); }
      } catch (cause) { setDescriptionError(cause instanceof Error ? cause.message : "Could not prepare description changes."); }
      return;
    }

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
  const mirroredSide = typeof item.attributes.mirrored_reconstruction === "object" && item.attributes.mirrored_reconstruction !== null && (item.attributes.mirrored_reconstruction as Record<string, unknown>).mirrored_side === "left" ? "left" : "right";
  const imageChoices: { value: "crop" | "vtoff" | "mirror"; label: string; mediaId: string }[] = [
    { value: "crop", label: "Original segmentation crop", mediaId: item.crop_media_id },
    ...(item.mirror_media_id ? [{ value: "mirror" as const, label: "Mirrored reconstruction (review before saving)", mediaId: item.mirror_media_id }] : []),
    ...(item.vtoff_media_id ? [{ value: "vtoff" as const, label: "AI-generated VTOFF reconstruction", mediaId: item.vtoff_media_id }] : []),
  ];

  return <article className="rounded-xl border border-slate-200 bg-white p-4" aria-label={`Candidate ${item.detected_category}`}>
    <form onSubmit={submit}>
      <fieldset disabled={disabled} className="min-w-0 space-y-4">
        <div className="flex items-start gap-4">
          <ProtectedImage mediaId={draft.preferred_media === "mirror" && item.mirror_media_id ? item.mirror_media_id : draft.preferred_media === "vtoff" && item.vtoff_media_id ? item.vtoff_media_id : item.crop_media_id} alt={`Candidate ${draft.name}`} className="h-28 w-28 shrink-0 rounded-lg bg-slate-100 object-contain" />
          <div className="min-w-0 flex-1">
            <h2 className="break-words font-semibold">{draft.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{fallback ? "Development preview — no AI segmentation" : `Detection confidence: ${Math.round(item.confidence * 100)}%`}</p>
            <p className="mt-2 text-sm font-medium" role="status">{dirty ? automatic ? "Unsaved corrections" : "Unsaved changes — accept to apply" : `Review: ${item.review_status}`}</p>
          </div>
        </div>
        <VerifiedSubtypeFields view={item.verified_subtype} category={draft.category} disabled={disabled} onConfirm={async value => { const success = await onReview({ item_id: item.id, decision: "accepted", subtype_update: value }); if (!success) throw new Error("The garment type was not saved. Check the selected wearer and current category."); }} />
        <details className="rounded-lg border border-slate-200 p-3">
          <summary className="cursor-pointer text-sm font-semibold">Edit details and review image</summary>
          {typedDescription && item.description ? <div className="mt-4 space-y-3">
            <DescriptionControls id={item.id} view={item.description} draft={descriptionDraft} onChange={next=>{
              if (!Object.keys(descriptionDraft).length) setDescriptionRevision(item.description!.revision);
              setDescriptionDraft(next);
              const currentMedia = item.mirror_media_id && item.preferred_media_id === item.mirror_media_id ? "mirror" : item.vtoff_media_id && item.preferred_media_id === item.vtoff_media_id ? "vtoff" : "crop";
              const changed = Object.keys(next).length > 0 || draft.preferred_media !== currentMedia;
              setDirty(changed); onDirty(item.id,changed);
            }} />
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmDescriptionStyle} onChange={event=>setConfirmDescriptionStyle(event.target.checked)} />Also record the existing optional style confirmation when I explicitly select one supported style.</label>
            {descriptionError && <p role="alert" className="text-sm text-red-700">{descriptionError}</p>}
          </div> : <>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm">Garment name<input required maxLength={100} value={draft.name} onChange={(e) => change("name", e.target.value)} className={inputClass} /></label>
            <label className="text-sm">Category<select aria-label="Category" value={draft.category} onChange={(e) => change("category", e.target.value)} className={inputClass}>
              {!categories.includes(draft.category) && <option value={draft.category}>{draft.category}</option>}
              {categories.filter(value => categoryPolicy.permits(value) || value === draft.category).map((category) => <option disabled={!categoryPolicy.permits(category)} key={category} value={category}>{category.replaceAll("_", " ")}</option>)}
            </select></label>
            <label className="text-sm">Primary colour<input maxLength={50} value={draft.primary_colour} onChange={(e) => change("primary_colour", e.target.value)} placeholder="Not specified" className={inputClass} /></label>
            {([['pattern', 'Pattern', patterns], ['fit', 'Fit (visible silhouette)', silhouettes], ['material', 'Material', materials], ...(supportsUpperDetails ? [['neckline', 'Neckline', necklines], ['sleeve_length', 'Sleeve length', sleeveLengths]] as const : [])] as const).map(([key, label, options]) => <label key={key} className="text-sm">{label}<select value={draft[key]} onChange={(e) => change(key, e.target.value)} className={inputClass}><option value="">Not specified</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>)}
            <label className="text-sm">Style<select value={styleChoice} onChange={(event) => { setStyleChoice(event.target.value); setDirty(true); onDirty(item.id, true); }} className={inputClass}><option value="__keep">Preserve current value: {item.attributes.style == null ? "Unknown" : Array.isArray(item.attributes.style) && item.attributes.style.length === 0 ? "No assigned tags (empty set)" : textValue(item.attributes.style) || "Invalid stored value"}</option><option value="__unknown">Unknown</option><option value="__empty">No assigned tags (empty set)</option>{styles.map((style) => <option key={style} value={style}>{style}</option>)}</select></label>
            <p className="text-xs text-slate-600 sm:col-span-2">{item.style_confirmation ? "Style is optional for storage. Ordinary suggestions can use a supported saved style provisionally without review. Explicitly selecting a style also records your optional confirmation; preserving a suggestion does not." : "This backend does not yet support style confirmation during addition. Saved styles may still need the separate contextual review."} {item.style_confirmation?.current && "Your selected style is confirmed for this candidate; save it to your wardrobe to use it."}</p>
            <label className="text-sm">Colour temperature<select value={draft.color_temperature} onChange={(event) => change("color_temperature", event.target.value)} className={inputClass}><option value="warm">Warm</option><option value="cool">Cool</option><option value="neutral">Neutral</option></select></label>
            <label className="flex items-center gap-2 self-end rounded-lg border border-slate-300 px-3 py-2 text-sm"><input type="checkbox" checked={draft.is_dominant} onChange={(event) => change("is_dominant", event.target.checked)} />One colour covers most of garment</label>
          </div>
          </>}
          <p className="mt-3 text-xs text-slate-600">Colour and dominance are automated suggestions; all displayed details remain reviewable. Detection confidence does not establish attribute accuracy.</p>
          {imageChoices.length > 1 ? <fieldset className="mt-4">
            <legend className="text-sm font-semibold">Compare and choose the image to save</legend>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {imageChoices.map((choice) =>
                <label key={choice.value} className={`cursor-pointer rounded-lg border p-3 ${draft.preferred_media === choice.value ? "border-[#6d335b] bg-purple-50" : "border-slate-200"}`}>
                  <input type="radio" name={`preferred-media-${item.id}`} value={choice.value} checked={draft.preferred_media === choice.value} onChange={(e) => change("preferred_media", e.target.value)} className="mr-2" />
                  <span className="text-sm font-medium">{choice.label}</span>
                  <ProtectedImage mediaId={choice.mediaId} alt={`${choice.label} for ${draft.name}`} className="mt-2 aspect-square w-full rounded bg-[linear-gradient(45deg,#e2e8f0_25%,transparent_25%),linear-gradient(-45deg,#e2e8f0_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#e2e8f0_75%),linear-gradient(-45deg,transparent_75%,#e2e8f0_75%)] bg-[length:20px_20px] object-contain" />
                </label>)}
            </div>
            {item.mirror_media_id && <p className="mt-2 text-xs text-amber-800">The mirrored reconstruction duplicates the detected half and flips it to make a symmetrical garment. It does not prove the hidden side is identical; compare it with the observed crop before selecting it.</p>}
            {item.vtoff_media_id && <p className="mt-2 text-xs text-amber-800">The VTOFF image is synthetic and may invent hidden logos, texture, shape, or colour. Compare it with the observed segmentation crop before selecting it.</p>}
            {item.mirror_media_id && <div className="mt-3 flex flex-wrap items-center gap-2"><span className="text-sm font-medium">Place mirrored copy:</span><button type="button" disabled={disabled} onClick={() => void onCreateMirror("left")} className={`rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-50 ${mirroredSide === "left" ? "border-[#6d335b] bg-purple-50 text-[#6d335b]" : "border-slate-300"}`}>Left</button><button type="button" disabled={disabled} onClick={() => void onCreateMirror("right")} className={`rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-50 ${mirroredSide === "right" ? "border-[#6d335b] bg-purple-50 text-[#6d335b]" : "border-slate-300"}`}>Right</button></div>}
          </fieldset> : <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm"><p>No alternate reconstruction has been created for this item yet.</p><button type="button" disabled={disabled} onClick={() => void onCreateMirror("right")} className="mt-3 rounded-lg border border-[#6d335b] px-3 py-2 text-sm font-semibold text-[#6d335b] disabled:opacity-50">Create mirrored garment preview</button><p className="mt-2 text-xs text-slate-600">This duplicates and flips the exact crop. You can then place the mirrored copy on either side and select the saved image here.</p></div>}
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
  const categoryPolicy = useWearerCategoryEligibility();
  const params = useSearchParams();
  const jobId = params.get("job");
  const historical = params.get("view") === "historical";
  const historicalWearer = params.get("wearer_profile_id") ?? undefined;
  const [pastJobs, setPastJobs] = useState<{id: string; status: string}[]>([]);
  const [job, setJob] = useState<ProcessingJob>();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    if (historical && !jobId) void getHistoricalProcessingJobs(historicalWearer).then(rows => { if (active) setPastJobs(rows); }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : "Historical jobs could not be loaded."); });
    return () => { active = false; };
  }, [historical, historicalWearer, jobId]);
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
        const next = historical ? await getHistoricalProcessingJob(jobId) : await getProcessingJob(jobId);
        if (active) {
          setJob(next); setError("");
          // Processing commits the prepared batch before the writer finalises it.
          // Briefly follow that transition; a failed writer still exposes Retry.
          const finalising = next.status === "review_required" && next.admission?.mode === "automatic_structural_v1" && next.admission.state === "prepared";
          if (!historical && (["queued", "processing"].includes(next.status) || (finalising && preparedPolls++ < 3))) timer = setTimeout(load, 900);
        }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Could not load the job."); }
    };
    void load();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, reload, historical]);
  const review = async (update: Record<string, unknown>) => {
    if (!jobId || actionLock.current) return false;
    actionLock.current = true; setBusy(true); setBusyMessage("Saving your review decision…"); setError("");
    try { setJob(await reviewProcessingJob(jobId, [update])); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Could not update review."); return false; }
    finally { actionLock.current = false; setBusy(false); setBusyMessage(""); }
  };
  const createMirror = async (itemId: string, replace = false, side: "left" | "right" = "right") => {
    if (!jobId || actionLock.current) return false;
    actionLock.current = true; setBusy(true); setBusyMessage(`${replace ? "Regenerating" : "Creating"} a mirrored garment previewâ€¦`); setError("");
    try { setJob(await createMirroredReconstruction(jobId, itemId, replace, side)); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create the mirrored garment preview."); return false; }
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
  if (historical) return <Layout><section className="mx-auto max-w-4xl space-y-4"><h1 className="text-2xl font-bold">Processing history — read-only</h1><p>Stored results are retained for the original uploader. Opening history does not process, review or save garments.</p>{error && <p role="alert">{error}</p>}{!jobId && <ul>{pastJobs.map(past => <li key={past.id}><Link className="inline-flex min-h-11 items-center underline" href={`/extract/results?view=historical&job=${encodeURIComponent(past.id)}${historicalWearer ? `&wearer_profile_id=${encodeURIComponent(historicalWearer)}` : ""}`}>{past.status} · {past.id}</Link></li>)}</ul>}{job && <><p>Status: {job.status}</p>{job.items.map(item => <article key={item.id} className="rounded-xl border p-4"><h2>{item.detected_category.replaceAll("_", " ")}</h2><p>{item.review_status}</p>{item.description && <details><summary className="cursor-pointer text-sm font-semibold">Stored descriptions (read-only)</summary><DescriptionControls id={`${item.id}-history`} view={item.description} draft={{}} onChange={()=>undefined} readOnly /></details>}{item.preferred_media_id && <ProtectedImage mediaId={item.preferred_media_id} alt={item.detected_category} className="h-40 w-40 object-contain" />}<dl>{Object.entries(item.attributes).filter(([,value]) => typeof value === "string" || value == null).map(([key,value]) => <div key={key}><dt className="font-semibold">{key}</dt><dd>{value == null ? "Not recorded" : String(value)}</dd></div>)}</dl></article>)}</>}<Link className="underline" href="/profile">Back to wearer management</Link></section></Layout>;
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
    <p data-testid="wearer-category-guidance" role="status">{categoryPolicy.text}</p>
    {job?.status === "completed" && <p role="status">{automaticMode ? `${job.admission?.garment_ids.length ?? 0} garment(s) automatically added. Saved attributes may be unreviewed.` : "These candidates have already been saved."} <Link href="/wardrobe" className="underline">Open wardrobe</Link></p>}
    {job?.status === "review_required" && <>
      {automaticMode && <section aria-label="Automatic saving outcome" className="rounded-xl border border-amber-300 bg-amber-50 p-4">
        <h2 className="font-semibold">Garments have not been added yet</h2>
        <p className="mt-2 text-sm">{job.admission?.reason?.startsWith("WearerCategory") ? "The selected wearer policy prevents saving this batch. Correct prohibited or unresolved categories, or select an appropriate configured wearer for a new upload. Nothing was partially saved." : job.admission?.reason === "category_missing_or_unsupported" ? "A supported category is missing. Correct the category and save corrections once. A missing style is not required for storage, but can prevent a style-dependent recommendation." : job.admission?.reason === "WardrobeQuotaExceeded" ? "This complete batch does not fit the 100 non-archived garment limit. You may archive garments or cancel this operation. No partial batch was saved." : "The complete batch is not ready to save. Check the processing details and any rejected item; all items must be valid. No partial batch was saved."}</p>
        <button disabled={busy || categoryPolicy.blocked || dirtyIds.size > 0} onClick={() => void retryAutomatic()} className="mt-3 min-h-11 rounded-lg border border-slate-500 px-4 text-sm font-semibold disabled:opacity-40">Retry automatic saving</button>
      </section>}
      <div className="space-y-4">{job.items.map((item) => <CandidateReview key={item.id} item={item} automatic={automaticMode} disabled={busy} onReview={review} onCreateMirror={(side = "right") => createMirror(item.id, Boolean(item.mirror_media_id), side)} onDirty={(id, dirty) => setDirtyIds((current) => { const next = new Set(current); if (dirty) next.add(id); else next.delete(id); return next; })} />)}</div>
      {!automaticMode && (<div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
        <p className="font-semibold">{accepted.length} of {job.items.length} candidates accepted</p>
        <fieldset disabled={busy} className="space-y-2"><legend className="font-semibold">Choose accepted garments to save</legend>
          {job.items.filter((item) => item.review_status === "accepted").map((item, index) => <label key={item.id} className="flex items-center gap-2">
            <input type="checkbox" data-testid={`save-candidate-${item.id}`} disabled={categoryPolicy.blocked || item.wearer_category_eligibility?.usable === false} checked={!excludedIds.has(item.id)} onChange={() => setExcludedIds((current) => { const next = new Set(current); if (next.has(item.id)) next.delete(item.id); else next.add(item.id); return next; })} />
            Save {typeof item.attributes.name === "string" ? item.attributes.name : item.detected_category.replaceAll("_", " ")} ({index + 1})
          </label>)}
        </fieldset>
        <p role="status">{selected.length} selected to save{quota ? `; ${quota.remaining} space(s) remaining.` : "; capacity will be checked when saving."}</p>
        {exceedsCapacity && <p className="text-amber-800">Select fewer candidates or archive garments before saving. <Link href="/wardrobe" className="underline">Open wardrobe</Link></p>}
        <p className="text-sm text-slate-600">Only these selected garments will be saved. This completes the job; unselected candidates will not be saved.</p>
        {dirtyIds.size > 0 && <p className="text-sm text-amber-800">Accept or reject edited candidates before saving.</p>}
        <label className="block text-sm">Outfit name (required when saving as an outfit)<input value={outfitName} onChange={(e) => setOutfitName(e.target.value)} maxLength={100} className={inputClass} placeholder="For example, Campus outfit" disabled={busy} /></label>
        <div className="flex flex-wrap gap-3">
          <button disabled={busy || categoryPolicy.blocked || job.items.some(item => selected.includes(item.id) && item.wearer_category_eligibility?.usable === false) || !selected.length || exceedsCapacity || dirtyIds.size > 0} onClick={() => void save("garments")} className="rounded-lg bg-[#6d335b] px-4 py-3 text-sm font-semibold text-white disabled:opacity-40">Save selected garments</button>
          <button disabled={busy || categoryPolicy.blocked || job.items.some(item => selected.includes(item.id) && item.wearer_category_eligibility?.usable === false) || !selected.length || exceedsCapacity || dirtyIds.size > 0 || !outfitName.trim()} onClick={() => void save("outfit")} className="rounded-lg border border-slate-400 px-4 py-3 text-sm font-semibold disabled:opacity-40">Save as outfit</button>
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
