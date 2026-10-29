"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, Heart, Pencil, Plus, Search, Trash2, WandSparkles, X } from "lucide-react";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import { reviewContextualSuitability } from "@/lib/api";
import GarmentSuitabilityFields, { declarationKey, type SuitabilityChoice } from "@/components/GarmentSuitabilityFields";
import {
  createOutfit, deleteGarment, deleteOutfit, getGarmentDependencies, getGarments,
  getOutfitDependencies, getOutfits, updateGarment, updateOutfit, getWardrobeQuota, wardrobeCapacityText, type WardrobeQuota,
  type Garment, type GarmentUpdate, type Outfit, type WardrobeSort,
} from "@/lib/api";

const SORT_OPTIONS: { value: WardrobeSort; label: string }[] = [
  { value: "updated_desc", label: "Recently updated" },
  { value: "updated_asc", label: "Oldest updated" },
  { value: "name_asc", label: "Name A–Z" },
  { value: "name_desc", label: "Name Z–A" },
  { value: "favourites", label: "Favourites first" },
];

const asText = (value: unknown) => typeof value === "string" ? value : "";
const asCsv = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").join(", ") : asText(value);
const csv = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);

function AppearanceReviewControls({ garment, onSaved, onError }: { garment: Garment; onSaved: () => Promise<void>; onError: (message: string) => void }) {
  const view = garment.appearance_edit;
  const original = Object.fromEntries(view?.features ?? []);
  const initial = Object.fromEntries(["collared_neckline", "tailored_cut", "structured_shape"].map(key => [key, original[key] === true ? "true" : original[key] === false ? "false" : "unknown"]));
  const [features, setFeatures] = useState(initial);
  const [condition, setCondition] = useState(view?.condition ?? "unknown");
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  if (!view) return null;
  const save = async (withdraw: boolean) => {
    if (busy.current) return;
    busy.current = true; setPending(true);
    const value = (key: string) => features[key] === "unknown" ? null : features[key] === "true";
    try {
      await reviewContextualSuitability(garment.id, { revision: view.revision, appearance_review: withdraw ? { withdraw: true } : {
        construction_features: { collared_neckline: value("collared_neckline"), tailored_cut: value("tailored_cut"), structured_shape: value("structured_shape") },
        condition_observation: condition as "clean_intact" | "needs_attention" | "unknown" } });
      await onSaved();
    } catch (cause) { onError(cause instanceof Error ? cause.message : "Could not save appearance observations."); }
    finally { busy.current = false; setPending(false); }
  };
  return <fieldset className="min-w-0 space-y-2 border-t border-zinc-200 pt-3 [overflow-wrap:anywhere]" disabled={pending} aria-busy={pending}>
    <legend className="font-bold">Reusable appearance observations</legend>
    <p>Optional for bounded interview suggestions. These are your observations, not AI verification or professional certification.</p>
    <p>{view.current ? "Current value-bound observations." : "No current observations; earlier values may need review."} Last recorded: {view.reviewed_at ?? "never"}.</p>
    <p>A collar is visible at the neckline. Tailored cut means shaping from darts, panels or a defined waist. Structured shape means construction intended to hold an outline rather than only drape. If uncertain, choose Unknown.</p>
    {(["collared_neckline", "tailored_cut", "structured_shape"] as const).map(key => <label key={key} className="block">{key.replaceAll("_", " ")}<select aria-label={key.replaceAll("_", " ")} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" value={features[key]} onChange={event => setFeatures({ ...features, [key]: event.target.value })}><option value="unknown">Unknown</option><option value="true">Yes, I observed this</option><option value="false">No</option></select></label>)}
    <label className="block">Dated condition observation<select aria-label="Dated condition observation" className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" value={condition} onChange={event => setCondition(event.target.value)}><option value="unknown">Unknown</option><option value="clean_intact">I observed it clean and without visible damage</option><option value="needs_attention">Needs attention</option></select></label>
    <p>This records a dated observation. Check current condition and wearer fit before wearing; shoes and accessories are not assessed.</p>
    <div className="flex flex-wrap gap-2"><button type="button" onClick={() => void save(false)} className="min-h-11 border-2 border-black px-3">I reviewed these appearance observations</button><button type="button" onClick={() => { setFeatures(initial); setCondition(view.condition ?? "unknown"); }} className="min-h-11 border-2 border-black px-3">Cancel appearance changes</button><button type="button" onClick={() => void save(true)} className="min-h-11 border-2 border-black px-3">Withdraw appearance observations</button></div>
  </fieldset>;
}

function ContextualReviewControls({ garment, onSaved, onError }: { garment: Garment; onSaved: () => Promise<void>; onError: (message: string) => void }) {
  const view = garment.contextual_edit;
  const [choice, setChoice] = useState(view?.wedding_choice ?? "unknown");
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  if (!view) return null;
  const save = async (action: { review_style?: boolean; wedding_choice?: "unknown" | "allow" | "deny" }) => {
    if (busy.current) return;
    busy.current = true; setPending(true);
    try { await reviewContextualSuitability(garment.id, { revision: view.revision, ...action }); await onSaved(); }
    catch (cause) { onError(cause instanceof Error ? cause.message : "Could not save the contextual review."); }
    finally { busy.current = false; setPending(false); }
  };
  return <details className="mt-3 border-t border-zinc-200 pt-3" aria-label={`Contextual review for ${garment.name}`}>
    <summary className="cursor-pointer text-sm font-bold">Contextual recommendations</summary>
    <div className="mt-2 space-y-3 text-sm" aria-busy={pending}>
        <p>Ordinary campus, shopping, outings, date and dinner can use usable saved styles provisionally without this review. Review and restrictions are optional; wedding, presentations and interviews retain their specific evidence requirements.</p>
      <p>Current style: {view.styles.join(", ") || "Unknown"}. {view.review_current ? "Reviewed for contextual inference." : "Not reviewed for contextual inference."}</p>
      <p>{garment.style_confirmation?.source ? "This style was confirmed when you added or edited the garment. No additional review is required." : "You may optionally confirm a supported style in Add/Edit or below. Ordinary saved-style suggestions do not require this confirmation."} Confirmation supplies style evidence, not permission for every occasion. You can withdraw it below.</p>
      <div className="flex flex-wrap gap-2"><button type="button" disabled={pending || view.style_state !== "Known" || view.styles.length !== 1} onClick={() => void save({ review_style: true })} className="min-h-11 border-2 border-black px-3 py-1 text-xs font-bold disabled:opacity-40">I reviewed the current style</button><button type="button" disabled={pending || !view.review_current} onClick={() => void save({ review_style: false })} className="min-h-11 border-2 border-black px-3 py-1 text-xs font-bold disabled:opacity-40">Remove style review</button></div>
      <label className="block">Wedding suitability override (optional)<select disabled={pending} value={choice} onChange={event => setChoice(event.target.value as typeof choice)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2"><option value="unknown">Use attribute inference when supported</option><option value="allow">Allow for wedding</option><option value="deny">Deny for wedding</option></select></label>
      <button type="button" disabled={pending || choice === view.wedding_choice} onClick={() => void save({ wedding_choice: choice })} className="min-h-11 border-2 border-black px-3 py-1 text-xs font-bold disabled:opacity-40">Save wedding override</button>
      <p>Your explicit Deny always blocks selection. An Allow does not waive another required condition.</p>
        <AppearanceReviewControls garment={garment} onSaved={onSaved} onError={onError} />
    </div>
  </details>;
}

function GarmentEditor({ garment, onCancel, onSaved, onError }: { garment: Garment; onCancel: () => void; onSaved: () => Promise<void>; onError: (message: string) => void }) {
  const [name, setName] = useState(garment.name);
  const [category, setCategory] = useState(garment.category);
  const [colour, setColour] = useState(garment.primary_colour ?? "");
  const [pattern, setPattern] = useState(garment.pattern ?? "");
  const [fit, setFit] = useState(asText(garment.attributes.fit));
  const attributeStyle = Object.prototype.hasOwnProperty.call(garment.attributes, "style")
    ? garment.attributes.style : garment.additional_attributes?.style;
  const currentStyle = garment.style_tags ?? attributeStyle;
  const [style, setStyle] = useState(asCsv(currentStyle));
  const [styleMode, setStyleMode] = useState("keep");
  const [material, setMaterial] = useState(asText(garment.attributes.material));
  const tagEdit = garment.tag_edit;
  const [tags, setTags] = useState(tagEdit ? asCsv(tagEdit.ordinary_tags) : asCsv(garment.attributes.custom_tags));
  const [suitabilityChoices, setSuitabilityChoices] = useState<Record<string, SuitabilityChoice>>({});
  const [removedAnnotations, setRemovedAnnotations] = useState<number[]>([]);
  const [temperature, setTemperature] = useState(asText(garment.attributes.color_temperature) || "neutral");
  const [dominant, setDominant] = useState(garment.attributes.is_dominant === true);
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const payload: GarmentUpdate = {};
    const attributes: NonNullable<GarmentUpdate["attributes"]> = {};
    if (name !== garment.name) payload.name = name.trim();
    if (category !== garment.category) payload.category = category.trim();
    if (colour !== (garment.primary_colour ?? "")) payload.primary_colour = colour.trim() || null;
    if (pattern !== (garment.pattern ?? "")) payload.pattern = pattern.trim() || null;
    if (fit !== asText(garment.attributes.fit)) attributes.fit = fit.trim();
    if (material !== asText(garment.attributes.material)) attributes.material = material.trim();
    const ordinaryChanged = tags !== (tagEdit ? asCsv(tagEdit.ordinary_tags) : asCsv(garment.attributes.custom_tags));
    if (ordinaryChanged || Object.keys(suitabilityChoices).length || removedAnnotations.length) {
      if (!tagEdit?.editable) { onError("Reload the garment before changing its tags. Invalid stored collections require explicit repair."); return; }
      const ordinary = csv(tags);
      if (ordinaryChanged && ordinary.some(tag=>tag.toLowerCase().startsWith("rec:"))) { onError("Use the suitability controls for reserved annotations."); return; }
      const reserved = new Set(tagEdit.reserved_indices);
      let nextTags = tagEdit.tags.filter((_,index)=>!removedAnnotations.includes(index) && (!ordinaryChanged || reserved.has(index)));
      if (ordinaryChanged) nextTags = [...nextTags,...ordinary];
      for (const [key,choice] of Object.entries(suitabilityChoices)) {
        const declaration = tagEdit.declarations.find(item=>declarationKey(item.field,item.value) === key)!;
        nextTags = nextTags.filter(tag=>tag.trim() !== declaration.allow_tag && tag.trim() !== declaration.deny_tag);
        if (choice !== "unknown") nextTags.push(choice === "allow" ? declaration.allow_tag : declaration.deny_tag);
      }
      attributes.custom_tags = nextTags;
    }
    if (temperature !== (asText(garment.attributes.color_temperature) || "neutral")) attributes.color_temperature = temperature;
    if (dominant !== (garment.attributes.is_dominant === true)) attributes.is_dominant = dominant;
    if (styleMode === "unknown") attributes.style = null;
    if (styleMode === "empty") attributes.style = [];
    if (styleMode === "values") {
      const values = csv(style);
      if (!values.length) { onError("Enter style tags, or explicitly choose Unknown or No assigned tags."); return; }
      attributes.style = values;
      const canonical = values.length === 1 ? values[0].trim().toLowerCase().replace(/\s+/g, " ") : undefined;
      if (garment.style_confirmation && canonical && garment.contextual_edit?.style_options.includes(canonical)) {
        payload.style_confirmation = { contract: "owner-style-confirmation-1.0.0", expected_revision: garment.style_confirmation.revision, style: canonical };
      }
    }
    if (Object.keys(attributes).length) payload.attributes = attributes;
    setSaving(true);
    try { await updateGarment(garment.id, payload, tagEdit?.revision); await onSaved(); } catch (caught) { onError(caught instanceof Error ? caught.message : "Could not update the garment."); } finally { setSaving(false); }
  };

  return <form onSubmit={submit} className="mt-3 space-y-3 border-t border-zinc-200 pt-3" aria-label={`Edit ${garment.name}`}>
    <div className="grid grid-cols-2 gap-2">
      <label className="col-span-2 text-xs font-bold">Name<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Category<input required maxLength={50} value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Primary colour<input list={`primary-colours-${garment.id}`} maxLength={50} value={colour} onChange={(event) => setColour(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      {tagEdit && <><datalist id={`primary-colours-${garment.id}`}>{tagEdit.colour_names.map(name=><option key={name} value={name} />)}</datalist><p className="col-span-2 text-xs text-zinc-600">Review the primary colour explicitly. Supported names: {tagEdit.colour_names.join(", ")}. Exact anchors also work; other hex values may be unknown. No approximate conversion is performed.</p></>}
      <label className="text-xs font-bold">Pattern<input maxLength={50} value={pattern} onChange={(event) => setPattern(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Fit<input maxLength={100} value={fit} onChange={(event) => setFit(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="col-span-2 text-xs font-bold">Style evidence<select value={styleMode} onChange={(event) => setStyleMode(event.target.value)} className="mt-1 w-full border-2 border-black bg-white p-2 text-sm"><option value="keep">Preserve current value</option><option value="unknown">Unknown</option><option value="empty">No assigned tags (empty set)</option><option value="values">Assigned style tags</option></select></label>
      <p className="col-span-2 text-xs text-zinc-600">{garment.style_confirmation ? "Saving an explicit supported style also records your optional confirmation. Ordinary suggestions can use supported saved styles without it. Preserving the current value creates no new human-review event." : "This backend does not yet support style confirmation during editing. The separate contextual review remains available."}</p>
      <label className="col-span-2 text-xs font-bold">Styles (comma-separated)<input value={style} disabled={styleMode === "unknown" || styleMode === "empty"} onChange={(event) => { setStyle(event.target.value); setStyleMode("values"); }} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <p className="col-span-2 text-xs text-zinc-600">Current style evidence: {currentStyle == null ? "Unknown" : Array.isArray(currentStyle) && currentStyle.length === 0 ? "No assigned tags (empty set)" : asCsv(currentStyle) || "Invalid stored value"}. Unknown means missing evidence; an empty set means no assigned style tags. Unchanged values are preserved.</p>
      <label className="text-xs font-bold">Material<input maxLength={100} value={material} onChange={(event) => setMaterial(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Tags<input disabled={!tagEdit?.editable} value={tags} onChange={(event) => setTags(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      {tagEdit && <GarmentSuitabilityFields view={tagEdit} choices={suitabilityChoices} removed={removedAnnotations} onChoice={(key,choice)=>setSuitabilityChoices(current=>({...current,[key]:choice}))} onRemove={index=>setRemovedAnnotations(current=>[...current,index])} />}
      <label className="text-xs font-bold">Colour temperature<select value={temperature} onChange={(event) => setTemperature(event.target.value)} className="mt-1 w-full border-2 border-black bg-white p-2 text-sm"><option value="warm">Warm</option><option value="cool">Cool</option><option value="neutral">Neutral</option></select></label>
      <label className="flex items-center gap-2 self-end border-2 border-black p-2 text-xs font-bold"><input type="checkbox" checked={dominant} onChange={(event) => setDominant(event.target.checked)} />One dominant colour</label>
    </div>
    <div className="flex gap-2"><button disabled={saving} className="bg-black px-3 py-2 text-xs font-bold text-white disabled:opacity-50">{saving ? "Saving…" : "Save changes"}</button><button type="button" onClick={onCancel} className="border-2 border-black px-3 py-2 text-xs font-bold">Cancel</button></div>
  </form>;
}

function OutfitEditor({ outfit, garments, onCancel, onSaved, onError }: { outfit: Outfit; garments: Garment[]; onCancel: () => void; onSaved: () => Promise<void>; onError: (message: string) => void }) {
  const [name, setName] = useState(outfit.name);
  const [description, setDescription] = useState(outfit.description ?? "");
  const [ids, setIds] = useState(outfit.items.map((item) => item.garment_id));
  const [garmentToAdd, setGarmentToAdd] = useState("");
  const [saving, setSaving] = useState(false);
  const byId = useMemo(() => new Map(garments.map((item) => [item.id, item])), [garments]);
  const unused = garments.filter((item) => !ids.includes(item.id));
  const candidate = unused.find((item) => item.id === garmentToAdd);
  const move = (index: number, offset: number) => setIds((current) => {
    const next = [...current];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    return next;
  });
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!ids.length) return;
    setSaving(true);
    try { await updateOutfit(outfit.id, { name: name.trim(), description: description.trim(), garment_ids: ids }); await onSaved(); } catch (caught) { onError(caught instanceof Error ? caught.message : "Could not update the outfit."); } finally { setSaving(false); }
  };

  return <form onSubmit={submit} className="mt-4 space-y-3 border-t border-zinc-200 pt-3" aria-label={`Edit ${outfit.name}`}>
    <label className="block text-xs font-bold">Name<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
    <label className="block text-xs font-bold">Description<textarea maxLength={500} value={description} onChange={(event) => setDescription(event.target.value)} className="mt-1 min-h-20 w-full border-2 border-black p-2 text-sm" /></label>
    <fieldset><legend className="text-xs font-bold">Garments and order</legend><div className="mt-1 space-y-1">
      {ids.map((id, index) => <div key={id} className="flex items-center gap-1 border border-zinc-200 p-2 text-xs"><span className="flex-1">{byId.get(id)?.name ?? "Unavailable garment"}</span><button type="button" disabled={index === 0} onClick={() => move(index, -1)} aria-label="Move garment up"><ChevronUp className="h-4 w-4" /></button><button type="button" disabled={index === ids.length - 1} onClick={() => move(index, 1)} aria-label="Move garment down"><ChevronDown className="h-4 w-4" /></button><button type="button" disabled={ids.length === 1} onClick={() => setIds((current) => current.filter((value) => value !== id))} aria-label="Remove garment from outfit"><X className="h-4 w-4" /></button></div>)}
    </div></fieldset>
    {unused.length > 0 && <section aria-label="Preview garment before adding" className="space-y-2 border-2 border-black bg-zinc-50 p-3"><label className="block text-xs font-bold">Add garment<select value={garmentToAdd} onChange={(event) => setGarmentToAdd(event.target.value)} className="mt-1 w-full border-2 border-black bg-white p-2 text-sm"><option value="">Choose a garment…</option>{unused.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.category}</option>)}</select></label>{candidate && <div className="flex gap-3 border border-zinc-300 bg-white p-2"><div className="h-24 w-24 shrink-0 overflow-hidden bg-zinc-200">{candidate.preferred_media_id ? <ProtectedImage mediaId={candidate.preferred_media_id} alt={candidate.name} className="h-full w-full object-cover" /> : <span className="flex h-full items-center justify-center p-2 text-center text-xs text-zinc-500">Image unavailable</span>}</div><div className="min-w-0"><p className="font-bold">{candidate.name}</p><p className="text-sm text-zinc-600">{candidate.category.replaceAll("_", " ")}</p><p className="mt-2 text-xs text-zinc-500">Preview this garment before adding it to the outfit.</p><button type="button" onClick={() => { setIds((current) => [...current, candidate.id]); setGarmentToAdd(""); }} className="mt-2 min-h-10 bg-black px-3 text-xs font-bold text-white">Add this garment</button></div></div>}</section>}
    <div className="flex gap-2"><button disabled={saving || !ids.length} className="bg-black px-3 py-2 text-xs font-bold text-white disabled:opacity-50">{saving ? "Saving…" : "Save changes"}</button><button type="button" onClick={onCancel} className="border-2 border-black px-3 py-2 text-xs font-bold">Cancel</button></div>
  </form>;
}

function OutfitGarments({ outfit, garments }: { outfit: Outfit; garments: Garment[] }) {
  const byId = useMemo(() => new Map(garments.map((garment) => [garment.id, garment])), [garments]);
  return <section className="mt-4 border-t-2 border-black pt-3" aria-label={`Garments in ${outfit.name}`}>
    <p className="text-xs font-black uppercase tracking-wide">Garments in this outfit ({outfit.items.length})</p>
    <ol className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
      {outfit.items.map((item) => {
        const garment = byId.get(item.garment_id);
        const mediaId = garment?.preferred_media_id ?? item.preferred_media_id;
        return <li key={item.garment_id} className="min-w-0 border border-zinc-300 bg-zinc-50 p-2">
          <div className="aspect-square overflow-hidden bg-zinc-200">{mediaId ? <ProtectedImage mediaId={mediaId} alt={item.name} className="h-full w-full object-cover" /> : <span className="flex h-full items-center justify-center p-2 text-center text-xs text-zinc-500">Image unavailable</span>}</div>
          <p className="mt-2 truncate text-xs font-bold" title={item.name}>{item.name}</p>
          <p className="truncate text-[11px] text-zinc-600">{item.category.replaceAll("_", " ")} · {item.role.replaceAll("_", " ")}</p>
        </li>;
      })}
    </ol>
  </section>;
}

function OutfitBuilder({ garments, selectedIds, onToggle, name, onNameChange, description, onDescriptionChange, onCancel, onSubmit, saving }: { garments: Garment[]; selectedIds: string[]; onToggle: (id: string) => void; name: string; onNameChange: (value: string) => void; description: string; onDescriptionChange: (value: string) => void; onCancel: () => void; onSubmit: (event: FormEvent) => void; saving: boolean }) {
  const available = garments.filter((garment) => garment.status === "available");
  return <form onSubmit={onSubmit} aria-busy={saving} className="space-y-4 border-2 border-black bg-zinc-50 p-4">
    <div className="flex items-start justify-between gap-3"><div><h2 className="font-black">Create outfit from your garments</h2><p className="text-sm text-zinc-600">Choose confirmed, available garments, then give the outfit a name.</p></div><button type="button" onClick={onCancel} className="min-h-10 border-2 border-black px-3 text-xs font-bold">Cancel</button></div>
    <fieldset><legend className="text-sm font-bold">Select garments ({selectedIds.length})</legend><div className="mt-2 grid max-h-80 gap-2 overflow-y-auto sm:grid-cols-2 lg:grid-cols-4">{available.map((garment) => <label key={garment.id} className={`flex cursor-pointer gap-2 border-2 p-2 ${selectedIds.includes(garment.id) ? "border-black bg-white" : "border-zinc-300 bg-zinc-100"}`}><input type="checkbox" checked={selectedIds.includes(garment.id)} onChange={() => onToggle(garment.id)} /><div className="h-14 w-14 shrink-0 overflow-hidden bg-zinc-200">{garment.preferred_media_id && <ProtectedImage mediaId={garment.preferred_media_id} alt="" className="h-full w-full object-cover" />}</div><span className="min-w-0 text-xs"><strong className="block truncate">{garment.name}</strong><span className="block truncate text-zinc-600">{garment.category.replaceAll("_", " ")}</span></span></label>)}</div></fieldset>
    <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm font-bold">Outfit name<input required maxLength={100} disabled={saving} value={name} onChange={(event) => onNameChange(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" placeholder="Outfit name" /></label><label className="text-sm font-bold">Description (optional)<input maxLength={500} disabled={saving} value={description} onChange={(event) => onDescriptionChange(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" placeholder="When or how you wear it" /></label></div>
    <button type="submit" disabled={!selectedIds.length || !name.trim() || saving} className="min-h-11 bg-black px-4 py-3 text-xs font-mono font-black uppercase text-white disabled:opacity-40">{saving ? "Saving outfit…" : "Create outfit"}</button>
  </form>;
}

export default function WardrobePage() {
  const [tab, setTab] = useState<"garments" | "outfits">("garments");
  const [garments, setGarments] = useState<Garment[]>([]);
  const [allGarments, setAllGarments] = useState<Garment[]>([]);
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [garmentQuery, setGarmentQuery] = useState("");
  const [garmentCategory, setGarmentCategory] = useState("");
  const [garmentColour, setGarmentColour] = useState("");
  const [garmentStyle, setGarmentStyle] = useState("");
  const [garmentAvailability, setGarmentAvailability] = useState<"available" | "unavailable" | "archived" | "all">("available");
  const [garmentFavourite, setGarmentFavourite] = useState("");
  const [garmentSort, setGarmentSort] = useState<WardrobeSort>("updated_desc");
  const [outfitQuery, setOutfitQuery] = useState("");
  const [outfitCategory, setOutfitCategory] = useState("");
  const [outfitType, setOutfitType] = useState<"" | Outfit["creation_type"]>("");
  const [outfitFavourite, setOutfitFavourite] = useState("");
  const [outfitSort, setOutfitSort] = useState<WardrobeSort>("updated_desc");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [newOutfitName, setNewOutfitName] = useState("");
  const [newOutfitDescription, setNewOutfitDescription] = useState("");
  const [showOutfitBuilder, setShowOutfitBuilder] = useState(false);
  const [editingGarment, setEditingGarment] = useState<string | null>(null);
  const [editingOutfit, setEditingOutfit] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creatingOutfit, setCreatingOutfit] = useState(false);
  const loadSequence = useRef(0);
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


  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    try {
      const [completeGarments, nextGarments, nextOutfits] = await Promise.all([
        getGarments(),
        getGarments({ colour: garmentColour, style: garmentStyle, availability: garmentAvailability, query: garmentQuery, category: garmentCategory || undefined, favourite: garmentFavourite ? garmentFavourite === "true" : undefined, sort: garmentSort }),
        getOutfits({ query: outfitQuery, category: outfitCategory || undefined, creationType: outfitType || undefined, favourite: outfitFavourite ? outfitFavourite === "true" : undefined, sort: outfitSort }),
      ]);
      if (sequence !== loadSequence.current) return;
      setAllGarments(completeGarments); setGarments(nextGarments); setOutfits(nextOutfits); setError("");
    } catch (caught) { if (sequence === loadSequence.current) setError(caught instanceof Error ? caught.message : "Could not load your wardrobe."); }
    finally { if (sequence === loadSequence.current) setLoading(false); }
  }, [garmentColour, garmentStyle, garmentAvailability, garmentCategory, garmentFavourite, garmentQuery, garmentSort, outfitCategory, outfitFavourite, outfitQuery, outfitSort, outfitType]);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 200); return () => window.clearTimeout(timer); }, [load]);
  const categories = useMemo(() => [...new Set(allGarments.map((garment) => garment.category))].sort(), [allGarments]);
  const garmentFiltersActive = Boolean(garmentColour || garmentStyle || garmentAvailability !== "available" || garmentQuery || garmentCategory || garmentFavourite || garmentSort !== "updated_desc");
  const outfitFiltersActive = Boolean(outfitQuery || outfitCategory || outfitType || outfitFavourite || outfitSort !== "updated_desc");
  const resetGarmentFilters = () => { setGarmentColour(""); setGarmentStyle(""); setGarmentAvailability("available"); setGarmentQuery(""); setGarmentCategory(""); setGarmentFavourite(""); setGarmentSort("updated_desc"); };
  const resetOutfitFilters = () => { setOutfitQuery(""); setOutfitCategory(""); setOutfitType(""); setOutfitFavourite(""); setOutfitSort("updated_desc"); };
  const toggleSelection = (id: string) => setSelectedIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  const perform = async (action: () => Promise<void>, success: string) => { try { setError(""); setNotice(""); await action(); setNotice(success); await load(); await refreshQuota(); } catch (caught) { setError(caught instanceof Error ? caught.message : "The request could not be completed."); } };

  const createManualOutfit = async (event: FormEvent) => {
    event.preventDefault();
    if (!newOutfitName.trim() || !selectedIds.length) return;
    setCreatingOutfit(true);
    try { await perform(async () => { await createOutfit(newOutfitName.trim(), selectedIds, newOutfitDescription.trim()); setNewOutfitName(""); setNewOutfitDescription(""); setSelectedIds([]); setShowOutfitBuilder(false); setTab("outfits"); }, "Outfit saved."); }
    finally { setCreatingOutfit(false); }
  };

  const archiveGarment = async (garment: Garment) => {
    try {
      const dependencies = await getGarmentDependencies(garment.id);
      if (!dependencies.can_archive) {
        const outfitNames = dependencies.active_outfits.map((item) => item.name).join(", ");
        setError(`${dependencies.policy}${outfitNames ? ` Remove it from: ${outfitNames}.` : ""}${dependencies.active_visualisations.length ? ` ${dependencies.active_visualisations.length} visualisation(s) are unfinished.` : ""}`);
        return;
      }
      if (window.confirm(`Archive ${garment.name}? It will be removed from your active garment collection.`)) await perform(() => deleteGarment(garment.id), "Garment archived.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not check garment dependencies."); }
  };

  const archiveOutfit = async (outfit: Outfit) => {
    try {
      const dependencies = await getOutfitDependencies(outfit.id);
      if (!dependencies.can_archive) { setError(`${dependencies.policy} ${dependencies.active_visualisations.length} visualisation(s) are unfinished.`); return; }
      if (window.confirm(`Archive ${outfit.name}? Its garments will remain in your garment collection.`)) await perform(() => deleteOutfit(outfit.id), "Outfit archived.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not check outfit dependencies."); }
  };

  return <Layout><div className="space-y-6">
    <div className="flex flex-col justify-between gap-4 border-b-4 border-black pb-5 sm:flex-row sm:items-end"><div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">DIGITAL WARDROBE</p><h1 className="text-3xl font-black tracking-tight">Your confirmed items</h1><p className="mt-1 text-sm text-zinc-600">Browse garments and outfits, update their details, or archive them after dependency checks.</p></div><div className="flex flex-wrap gap-2">{quota?.remaining === 0 ? <button type="button" disabled className="bg-zinc-200 px-4 py-3 text-xs font-bold">Add from image (wardrobe full)</button> : <Link href="/extract" className="inline-flex min-h-11 items-center justify-center gap-2 bg-black px-4 py-3 text-xs font-mono font-black uppercase text-white"><Plus className="h-4 w-4" /> Add from image</Link>}<button type="button" onClick={() => { setTab("garments"); setShowOutfitBuilder(true); }} className="inline-flex min-h-11 items-center justify-center gap-2 border-2 border-black px-4 py-3 text-xs font-mono font-black uppercase"><Plus className="h-4 w-4" /> Create outfit</button></div></div>
    <section aria-label="Wardrobe capacity" className="rounded-lg border border-slate-200 p-3 text-sm">
      <p role="status" aria-live="polite">{quota ? wardrobeCapacityText(quota) : "Capacity unavailable"}</p>
      <p className="text-xs text-slate-600">Non-archived entries include unavailable items. Pending uploads do not reserve spaces. Archiving a garment releases its space.</p>
      <button type="button" onClick={() => void refreshQuota()} className="mt-1 underline">Refresh capacity</button>
    </section>
    <div className="grid grid-cols-2 border-2 border-black p-1 text-sm font-bold" role="tablist" aria-label="Wardrobe collection"><button type="button" role="tab" aria-selected={tab === "garments"} onClick={() => setTab("garments")} className={`min-h-11 p-2 ${tab === "garments" ? "bg-black text-white" : ""}`}>Garments ({garments.length})</button><button type="button" role="tab" aria-selected={tab === "outfits"} onClick={() => setTab("outfits")} className={`min-h-11 p-2 ${tab === "outfits" ? "bg-black text-white" : ""}`}>Outfits ({outfits.length})</button></div>
    {error && <p role="alert" className="border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    {notice && <p role="status" className="border-2 border-emerald-600 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}

    {tab === "garments" && <>
      {showOutfitBuilder && <OutfitBuilder garments={allGarments} selectedIds={selectedIds} onToggle={toggleSelection} name={newOutfitName} onNameChange={setNewOutfitName} description={newOutfitDescription} onDescriptionChange={setNewOutfitDescription} onCancel={() => setShowOutfitBuilder(false)} onSubmit={createManualOutfit} saving={creatingOutfit} />}
      <div className="grid gap-3 border-2 border-black p-3 sm:grid-cols-2 lg:grid-cols-4"><label className="flex min-h-11 items-center gap-2 border-2 border-black px-3"><Search className="h-4 w-4" aria-hidden="true" /><input value={garmentQuery} onChange={(event) => setGarmentQuery(event.target.value)} className="w-full py-2 text-sm outline-none" placeholder="Search garments" aria-label="Search garments" /></label><select value={garmentCategory} onChange={(event) => setGarmentCategory(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter garments by category"><option value="">All categories</option>{categories.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select><label className="text-xs font-bold">Primary colour<input value={garmentColour} maxLength={50} onChange={(event) => setGarmentColour(event.target.value)} placeholder="Exact stored colour" className="mt-1 min-h-11 w-full border-2 border-black px-3 text-sm" /></label><label className="text-xs font-bold">Style filter<input value={garmentStyle} maxLength={100} onChange={(event) => setGarmentStyle(event.target.value)} placeholder="Exact stored style" className="mt-1 min-h-11 w-full border-2 border-black px-3 text-sm" /></label><select aria-label="Filter garments by availability" value={garmentAvailability} onChange={(event) => setGarmentAvailability(event.target.value as typeof garmentAvailability)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm"><option value="available">Available</option><option value="unavailable">Unavailable / other active status</option><option value="archived">Archived</option><option value="all">All stored garments</option></select><select value={garmentFavourite} onChange={(event) => setGarmentFavourite(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter garments by favourite"><option value="">All favourites</option><option value="true">Favourites only</option><option value="false">Not favourites</option></select><select value={garmentSort} onChange={(event) => setGarmentSort(event.target.value as WardrobeSort)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Sort garments">{SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
      <div className="flex min-h-10 items-center justify-between gap-3 text-xs text-zinc-500"><span role="status">{loading ? "Updating garments…" : `${garments.length} garment${garments.length === 1 ? "" : "s"} shown`}</span>{garmentFiltersActive && <button type="button" onClick={resetGarmentFilters} className="inline-flex min-h-10 items-center gap-1 px-2 font-bold text-zinc-700 underline"><X className="h-3.5 w-3.5" aria-hidden="true" /> Clear filters</button>}</div>
      {loading ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Loading garments">{[0, 1, 2].map((item) => <div key={item} className="ui-skeleton aspect-[4/5] rounded-xl" />)}</div> : garments.length ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{garments.map((garment) => <article key={garment.id} className="border-2 border-black bg-white p-3" data-garment-id={garment.id}><div className="flex aspect-square items-center justify-center overflow-hidden bg-zinc-100">{garment.preferred_media_id ? <ProtectedImage mediaId={garment.preferred_media_id} alt={garment.name} className="h-full w-full object-cover" /> : <span className="text-xs text-zinc-500">No reviewed image</span>}</div><div className="mt-3 flex items-start justify-between gap-3"><label className="flex flex-1 items-start gap-2"><input type="checkbox" disabled={garment.status !== "available"} checked={selectedIds.includes(garment.id)} onChange={() => toggleSelection(garment.id)} aria-label={`Select ${garment.name} for outfit`} /><span><strong className="block">{garment.name}</strong><span className="block text-xs">{garment.status ?? "Unknown status"}</span><span className="text-xs text-zinc-500">{garment.category.replaceAll("_", " ")}{garment.primary_colour ? ` · ${garment.primary_colour}` : ""}{garment.pattern ? ` · ${garment.pattern}` : ""}</span></span></label><button type="button" disabled={garment.status !== "available"} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg disabled:opacity-40" onClick={() => void perform(() => updateGarment(garment.id, { is_favourite: !garment.is_favourite }).then(() => undefined), "Favourite updated.")} aria-label={`${garment.is_favourite ? "Remove" : "Add"} ${garment.name} ${garment.is_favourite ? "from" : "to"} favourites`} aria-pressed={garment.is_favourite}><Heart className={`h-5 w-5 ${garment.is_favourite ? "fill-black" : ""}`} /></button></div><div className="mt-3 flex gap-2"><button type="button" disabled={garment.status !== "available"} onClick={() => setEditingGarment(editingGarment === garment.id ? null : garment.id)} className="inline-flex min-h-10 items-center gap-1 border-2 border-black px-3 py-1 text-xs font-bold"><Pencil className="h-3 w-3" aria-hidden="true" /> Edit</button><button type="button" disabled={garment.status !== "available"} onClick={() => void archiveGarment(garment)} className="flex h-10 w-10 items-center justify-center border-2 border-black text-rose-700" aria-label={`Archive ${garment.name}`}><Trash2 className="h-4 w-4" /></button></div>{garment.status === "available" && editingGarment !== garment.id && <ContextualReviewControls key={`${garment.id}:${garment.contextual_edit?.revision}`} garment={garment} onSaved={load} onError={setError} />}{garment.status === "available" && editingGarment === garment.id && <GarmentEditor garment={garment} onCancel={() => setEditingGarment(null)} onError={setError} onSaved={async () => { setEditingGarment(null); setNotice("Garment updated."); await load(); }} />}</article>)}</div> : <p className="border-2 border-dashed border-zinc-400 p-8 text-center text-sm text-zinc-500">No matching garments. Adjust the filters or add a wardrobe image.</p>}
      <form onSubmit={createManualOutfit} aria-busy={creatingOutfit} className="grid gap-3 border-2 border-black bg-zinc-50 p-4 sm:grid-cols-2 sm:items-end"><label className="text-sm font-bold">Create an outfit from {selectedIds.length} selected garment(s)<input required maxLength={100} disabled={creatingOutfit} value={newOutfitName} onChange={(event) => setNewOutfitName(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" placeholder="Outfit name" /></label><label className="text-sm font-bold">Description (optional)<input maxLength={500} disabled={creatingOutfit} value={newOutfitDescription} onChange={(event) => setNewOutfitDescription(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" placeholder="When or how you wear it" /></label><button type="submit" disabled={!selectedIds.length || !newOutfitName.trim() || creatingOutfit} className="min-h-11 bg-black px-4 py-3 text-xs font-mono font-black uppercase text-white disabled:opacity-40 sm:col-span-2">{creatingOutfit ? "Saving outfit…" : "Save outfit"}</button></form>
    </>}

    {tab === "outfits" && <>
      <div className="grid gap-3 border-2 border-black p-3 sm:grid-cols-2 lg:grid-cols-5"><label className="flex min-h-11 items-center gap-2 border-2 border-black px-3"><Search className="h-4 w-4" aria-hidden="true" /><input value={outfitQuery} onChange={(event) => setOutfitQuery(event.target.value)} className="w-full py-2 text-sm outline-none" placeholder="Search outfits" aria-label="Search outfits" /></label><select value={outfitCategory} onChange={(event) => setOutfitCategory(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter outfits by category"><option value="">All categories</option>{categories.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select><select value={outfitType} onChange={(event) => setOutfitType(event.target.value as "" | Outfit["creation_type"])} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter outfits by source"><option value="">All sources</option><option value="manual">Manual</option><option value="image_upload">Image upload</option><option value="recommendation">Recommendation</option></select><select value={outfitFavourite} onChange={(event) => setOutfitFavourite(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter outfits by favourite"><option value="">All favourites</option><option value="true">Favourites only</option><option value="false">Not favourites</option></select><select value={outfitSort} onChange={(event) => setOutfitSort(event.target.value as WardrobeSort)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Sort outfits">{SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
      <div className="flex min-h-10 items-center justify-between gap-3 text-xs text-zinc-500"><span role="status">{loading ? "Updating outfits…" : `${outfits.length} outfit${outfits.length === 1 ? "" : "s"} shown`}</span>{outfitFiltersActive && <button type="button" onClick={resetOutfitFilters} className="inline-flex min-h-10 items-center gap-1 px-2 font-bold text-zinc-700 underline"><X className="h-3.5 w-3.5" aria-hidden="true" /> Clear filters</button>}</div>
      {loading ? <div className="grid gap-4 md:grid-cols-2" role="status" aria-label="Loading outfits">{[0, 1].map((item) => <div key={item} className="ui-skeleton h-44 rounded-xl" />)}</div> : outfits.length ? <div className="grid gap-4 md:grid-cols-2">{outfits.map((outfit) => <article key={outfit.id} className="border-2 border-black bg-white p-4" data-outfit-id={outfit.id}><div className="flex justify-between gap-3"><div><h2 className="font-black">{outfit.name}</h2>{outfit.description && <p className="mt-1 text-sm text-zinc-600">{outfit.description}</p>}<p className="mt-1 text-xs text-zinc-500">{outfit.creation_type.replace("_", " ")} outfit</p></div><button type="button" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" onClick={() => void perform(() => updateOutfit(outfit.id, { is_favourite: !outfit.is_favourite }).then(() => undefined), "Favourite updated.")} aria-label={`${outfit.is_favourite ? "Remove" : "Add"} ${outfit.name} ${outfit.is_favourite ? "from" : "to"} favourites`} aria-pressed={outfit.is_favourite}><Heart className={`h-5 w-5 ${outfit.is_favourite ? "fill-black" : ""}`} /></button></div><OutfitGarments outfit={outfit} garments={allGarments} /><div className="mt-4 flex flex-wrap gap-2"><Link href={`/try-on?outfit=${outfit.id}`} className="inline-flex min-h-10 items-center gap-1 bg-black px-3 py-2 text-xs font-bold text-white"><WandSparkles className="h-4 w-4" aria-hidden="true" /> Visualise</Link><button type="button" onClick={() => setEditingOutfit(editingOutfit === outfit.id ? null : outfit.id)} className="inline-flex min-h-10 items-center gap-1 border-2 border-black px-3 py-2 text-xs font-bold"><Pencil className="h-3 w-3" aria-hidden="true" /> Edit</button><button type="button" onClick={() => void archiveOutfit(outfit)} className="min-h-10 border-2 border-black px-3 py-2 text-xs font-bold text-rose-700">Archive</button></div>{editingOutfit === outfit.id && <OutfitEditor outfit={outfit} garments={allGarments} onCancel={() => setEditingOutfit(null)} onError={setError} onSaved={async () => { setEditingOutfit(null); setNotice("Outfit updated."); await load(); }} />}</article>)}</div> : <p className="border-2 border-dashed border-zinc-400 p-8 text-center text-sm text-zinc-500">No matching outfits. Adjust the filters or create one from confirmed garments.</p>}
    </>}
  </div></Layout>;
}
