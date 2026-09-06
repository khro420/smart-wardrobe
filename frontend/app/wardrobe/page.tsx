"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, Heart, Pencil, Plus, Search, Trash2, WandSparkles, X } from "lucide-react";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import {
  createOutfit, deleteGarment, deleteOutfit, getGarmentDependencies, getGarments,
  getOutfitDependencies, getOutfits, updateGarment, updateOutfit,
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

function GarmentEditor({ garment, onCancel, onSaved, onError }: { garment: Garment; onCancel: () => void; onSaved: () => Promise<void>; onError: (message: string) => void }) {
  const [name, setName] = useState(garment.name);
  const [category, setCategory] = useState(garment.category);
  const [colour, setColour] = useState(garment.primary_colour ?? "");
  const [pattern, setPattern] = useState(garment.pattern ?? "");
  const [fit, setFit] = useState(asText(garment.attributes.fit));
  const [style, setStyle] = useState(asCsv(garment.attributes.style));
  const [material, setMaterial] = useState(asText(garment.attributes.material));
  const [tags, setTags] = useState(asCsv(garment.attributes.custom_tags));
  const [temperature, setTemperature] = useState(asText(garment.attributes.color_temperature) || "neutral");
  const [dominant, setDominant] = useState(garment.attributes.is_dominant === true);
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    const payload: GarmentUpdate = {
      name: name.trim(), category: category.trim(), primary_colour: colour.trim() || null, pattern: pattern.trim() || null,
      attributes: { fit: fit.trim(), style: csv(style), material: material.trim(), custom_tags: csv(tags), color_temperature: temperature, is_dominant: dominant },
    };
    try { await updateGarment(garment.id, payload); await onSaved(); } catch (caught) { onError(caught instanceof Error ? caught.message : "Could not update the garment."); } finally { setSaving(false); }
  };

  return <form onSubmit={submit} className="mt-3 space-y-3 border-t border-zinc-200 pt-3" aria-label={`Edit ${garment.name}`}>
    <div className="grid grid-cols-2 gap-2">
      <label className="col-span-2 text-xs font-bold">Name<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Category<input required maxLength={50} value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Primary colour<input maxLength={50} value={colour} onChange={(event) => setColour(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Pattern<input maxLength={50} value={pattern} onChange={(event) => setPattern(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Fit<input maxLength={100} value={fit} onChange={(event) => setFit(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="col-span-2 text-xs font-bold">Styles (comma-separated)<input value={style} onChange={(event) => setStyle(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Material<input maxLength={100} value={material} onChange={(event) => setMaterial(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
      <label className="text-xs font-bold">Tags<input value={tags} onChange={(event) => setTags(event.target.value)} className="mt-1 w-full border-2 border-black p-2 text-sm" /></label>
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
  const [saving, setSaving] = useState(false);
  const byId = useMemo(() => new Map(garments.map((item) => [item.id, item])), [garments]);
  const unused = garments.filter((item) => !ids.includes(item.id));
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
    {unused.length > 0 && <label className="block text-xs font-bold">Add garment<select value="" onChange={(event) => event.target.value && setIds((current) => [...current, event.target.value])} className="mt-1 w-full border-2 border-black bg-white p-2 text-sm"><option value="">Choose a garment…</option>{unused.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.category}</option>)}</select></label>}
    <div className="flex gap-2"><button disabled={saving || !ids.length} className="bg-black px-3 py-2 text-xs font-bold text-white disabled:opacity-50">{saving ? "Saving…" : "Save changes"}</button><button type="button" onClick={onCancel} className="border-2 border-black px-3 py-2 text-xs font-bold">Cancel</button></div>
  </form>;
}

export default function WardrobePage() {
  const [tab, setTab] = useState<"garments" | "outfits">("garments");
  const [garments, setGarments] = useState<Garment[]>([]);
  const [allGarments, setAllGarments] = useState<Garment[]>([]);
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [garmentQuery, setGarmentQuery] = useState("");
  const [garmentCategory, setGarmentCategory] = useState("");
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
  const [editingGarment, setEditingGarment] = useState<string | null>(null);
  const [editingOutfit, setEditingOutfit] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creatingOutfit, setCreatingOutfit] = useState(false);
  const loadSequence = useRef(0);

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    try {
      const [completeGarments, nextGarments, nextOutfits] = await Promise.all([
        getGarments(),
        getGarments({ query: garmentQuery, category: garmentCategory || undefined, favourite: garmentFavourite ? garmentFavourite === "true" : undefined, sort: garmentSort }),
        getOutfits({ query: outfitQuery, category: outfitCategory || undefined, creationType: outfitType || undefined, favourite: outfitFavourite ? outfitFavourite === "true" : undefined, sort: outfitSort }),
      ]);
      if (sequence !== loadSequence.current) return;
      setAllGarments(completeGarments); setGarments(nextGarments); setOutfits(nextOutfits); setError("");
    } catch (caught) { if (sequence === loadSequence.current) setError(caught instanceof Error ? caught.message : "Could not load your wardrobe."); }
    finally { if (sequence === loadSequence.current) setLoading(false); }
  }, [garmentCategory, garmentFavourite, garmentQuery, garmentSort, outfitCategory, outfitFavourite, outfitQuery, outfitSort, outfitType]);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 200); return () => window.clearTimeout(timer); }, [load]);
  const categories = useMemo(() => [...new Set(allGarments.map((garment) => garment.category))].sort(), [allGarments]);
  const garmentFiltersActive = Boolean(garmentQuery || garmentCategory || garmentFavourite || garmentSort !== "updated_desc");
  const outfitFiltersActive = Boolean(outfitQuery || outfitCategory || outfitType || outfitFavourite || outfitSort !== "updated_desc");
  const resetGarmentFilters = () => { setGarmentQuery(""); setGarmentCategory(""); setGarmentFavourite(""); setGarmentSort("updated_desc"); };
  const resetOutfitFilters = () => { setOutfitQuery(""); setOutfitCategory(""); setOutfitType(""); setOutfitFavourite(""); setOutfitSort("updated_desc"); };
  const toggleSelection = (id: string) => setSelectedIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  const perform = async (action: () => Promise<void>, success: string) => { try { setError(""); setNotice(""); await action(); setNotice(success); await load(); } catch (caught) { setError(caught instanceof Error ? caught.message : "The request could not be completed."); } };

  const createManualOutfit = async (event: FormEvent) => {
    event.preventDefault();
    if (!newOutfitName.trim() || !selectedIds.length) return;
    setCreatingOutfit(true);
    try { await perform(async () => { await createOutfit(newOutfitName.trim(), selectedIds, newOutfitDescription.trim()); setNewOutfitName(""); setNewOutfitDescription(""); setSelectedIds([]); setTab("outfits"); }, "Outfit saved."); }
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
    <div className="flex flex-col justify-between gap-4 border-b-4 border-black pb-5 sm:flex-row sm:items-end"><div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">DIGITAL WARDROBE</p><h1 className="text-3xl font-black tracking-tight">Your confirmed items</h1><p className="mt-1 text-sm text-zinc-600">Browse garments and outfits, update their details, or archive them after dependency checks.</p></div><Link href="/extract" className="inline-flex items-center justify-center gap-2 bg-black px-4 py-3 text-xs font-mono font-black uppercase text-white"><Plus className="h-4 w-4" /> Add from image</Link></div>
    <div className="grid grid-cols-2 border-2 border-black p-1 text-sm font-bold" role="tablist" aria-label="Wardrobe collection"><button type="button" role="tab" aria-selected={tab === "garments"} onClick={() => setTab("garments")} className={`min-h-11 p-2 ${tab === "garments" ? "bg-black text-white" : ""}`}>Garments ({garments.length})</button><button type="button" role="tab" aria-selected={tab === "outfits"} onClick={() => setTab("outfits")} className={`min-h-11 p-2 ${tab === "outfits" ? "bg-black text-white" : ""}`}>Outfits ({outfits.length})</button></div>
    {error && <p role="alert" className="border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    {notice && <p role="status" className="border-2 border-emerald-600 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}

    {tab === "garments" && <>
      <div className="grid gap-3 border-2 border-black p-3 sm:grid-cols-2 lg:grid-cols-4"><label className="flex min-h-11 items-center gap-2 border-2 border-black px-3"><Search className="h-4 w-4" aria-hidden="true" /><input value={garmentQuery} onChange={(event) => setGarmentQuery(event.target.value)} className="w-full py-2 text-sm outline-none" placeholder="Search garments" aria-label="Search garments" /></label><select value={garmentCategory} onChange={(event) => setGarmentCategory(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter garments by category"><option value="">All categories</option>{categories.map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select><select value={garmentFavourite} onChange={(event) => setGarmentFavourite(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter garments by favourite"><option value="">All favourites</option><option value="true">Favourites only</option><option value="false">Not favourites</option></select><select value={garmentSort} onChange={(event) => setGarmentSort(event.target.value as WardrobeSort)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Sort garments">{SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
      <div className="flex min-h-10 items-center justify-between gap-3 text-xs text-zinc-500"><span role="status">{loading ? "Updating garments…" : `${garments.length} garment${garments.length === 1 ? "" : "s"} shown`}</span>{garmentFiltersActive && <button type="button" onClick={resetGarmentFilters} className="inline-flex min-h-10 items-center gap-1 px-2 font-bold text-zinc-700 underline"><X className="h-3.5 w-3.5" aria-hidden="true" /> Clear filters</button>}</div>
      {loading ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Loading garments">{[0, 1, 2].map((item) => <div key={item} className="ui-skeleton aspect-[4/5] rounded-xl" />)}</div> : garments.length ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{garments.map((garment) => <article key={garment.id} className="border-2 border-black bg-white p-3" data-garment-id={garment.id}><div className="flex aspect-square items-center justify-center overflow-hidden bg-zinc-100">{garment.preferred_media_id ? <ProtectedImage mediaId={garment.preferred_media_id} alt={garment.name} className="h-full w-full object-cover" /> : <span className="text-xs text-zinc-500">No reviewed image</span>}</div><div className="mt-3 flex items-start justify-between gap-3"><label className="flex flex-1 items-start gap-2"><input type="checkbox" checked={selectedIds.includes(garment.id)} onChange={() => toggleSelection(garment.id)} aria-label={`Select ${garment.name} for outfit`} /><span><strong className="block">{garment.name}</strong><span className="text-xs text-zinc-500">{garment.category.replaceAll("_", " ")}{garment.primary_colour ? ` · ${garment.primary_colour}` : ""}{garment.pattern ? ` · ${garment.pattern}` : ""}</span></span></label><button type="button" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" onClick={() => void perform(() => updateGarment(garment.id, { is_favourite: !garment.is_favourite }).then(() => undefined), "Favourite updated.")} aria-label={`${garment.is_favourite ? "Remove" : "Add"} ${garment.name} ${garment.is_favourite ? "from" : "to"} favourites`} aria-pressed={garment.is_favourite}><Heart className={`h-5 w-5 ${garment.is_favourite ? "fill-black" : ""}`} /></button></div><div className="mt-3 flex gap-2"><button type="button" onClick={() => setEditingGarment(editingGarment === garment.id ? null : garment.id)} className="inline-flex min-h-10 items-center gap-1 border-2 border-black px-3 py-1 text-xs font-bold"><Pencil className="h-3 w-3" aria-hidden="true" /> Edit</button><button type="button" onClick={() => void archiveGarment(garment)} className="flex h-10 w-10 items-center justify-center border-2 border-black text-rose-700" aria-label={`Archive ${garment.name}`}><Trash2 className="h-4 w-4" /></button></div>{editingGarment === garment.id && <GarmentEditor garment={garment} onCancel={() => setEditingGarment(null)} onError={setError} onSaved={async () => { setEditingGarment(null); setNotice("Garment updated."); await load(); }} />}</article>)}</div> : <p className="border-2 border-dashed border-zinc-400 p-8 text-center text-sm text-zinc-500">No matching garments. Adjust the filters or add a wardrobe image.</p>}
      <form onSubmit={createManualOutfit} aria-busy={creatingOutfit} className="grid gap-3 border-2 border-black bg-zinc-50 p-4 sm:grid-cols-2 sm:items-end"><label className="text-sm font-bold">Create an outfit from {selectedIds.length} selected garment(s)<input required maxLength={100} disabled={creatingOutfit} value={newOutfitName} onChange={(event) => setNewOutfitName(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" placeholder="Outfit name" /></label><label className="text-sm font-bold">Description (optional)<input maxLength={500} disabled={creatingOutfit} value={newOutfitDescription} onChange={(event) => setNewOutfitDescription(event.target.value)} className="mt-1 min-h-11 w-full border-2 border-black bg-white p-2" placeholder="When or how you wear it" /></label><button type="submit" disabled={!selectedIds.length || !newOutfitName.trim() || creatingOutfit} className="min-h-11 bg-black px-4 py-3 text-xs font-mono font-black uppercase text-white disabled:opacity-40 sm:col-span-2">{creatingOutfit ? "Saving outfit…" : "Save outfit"}</button></form>
    </>}

    {tab === "outfits" && <>
      <div className="grid gap-3 border-2 border-black p-3 sm:grid-cols-2 lg:grid-cols-5"><label className="flex min-h-11 items-center gap-2 border-2 border-black px-3"><Search className="h-4 w-4" aria-hidden="true" /><input value={outfitQuery} onChange={(event) => setOutfitQuery(event.target.value)} className="w-full py-2 text-sm outline-none" placeholder="Search outfits" aria-label="Search outfits" /></label><select value={outfitCategory} onChange={(event) => setOutfitCategory(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter outfits by category"><option value="">All categories</option>{categories.map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select><select value={outfitType} onChange={(event) => setOutfitType(event.target.value as "" | Outfit["creation_type"])} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter outfits by source"><option value="">All sources</option><option value="manual">Manual</option><option value="image_upload">Image upload</option><option value="recommendation">Recommendation</option></select><select value={outfitFavourite} onChange={(event) => setOutfitFavourite(event.target.value)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Filter outfits by favourite"><option value="">All favourites</option><option value="true">Favourites only</option><option value="false">Not favourites</option></select><select value={outfitSort} onChange={(event) => setOutfitSort(event.target.value as WardrobeSort)} className="min-h-11 border-2 border-black bg-white px-3 py-2 text-sm" aria-label="Sort outfits">{SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
      <div className="flex min-h-10 items-center justify-between gap-3 text-xs text-zinc-500"><span role="status">{loading ? "Updating outfits…" : `${outfits.length} outfit${outfits.length === 1 ? "" : "s"} shown`}</span>{outfitFiltersActive && <button type="button" onClick={resetOutfitFilters} className="inline-flex min-h-10 items-center gap-1 px-2 font-bold text-zinc-700 underline"><X className="h-3.5 w-3.5" aria-hidden="true" /> Clear filters</button>}</div>
      {loading ? <div className="grid gap-4 md:grid-cols-2" role="status" aria-label="Loading outfits">{[0, 1].map((item) => <div key={item} className="ui-skeleton h-44 rounded-xl" />)}</div> : outfits.length ? <div className="grid gap-4 md:grid-cols-2">{outfits.map((outfit) => <article key={outfit.id} className="border-2 border-black bg-white p-4" data-outfit-id={outfit.id}><div className="flex justify-between gap-3"><div><h2 className="font-black">{outfit.name}</h2>{outfit.description && <p className="mt-1 text-sm text-zinc-600">{outfit.description}</p>}<p className="mt-1 text-xs text-zinc-500">{outfit.items.map((item) => item.name).join(" · ") || "No items"} · {outfit.creation_type.replace("_", " ")}</p></div><button type="button" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" onClick={() => void perform(() => updateOutfit(outfit.id, { is_favourite: !outfit.is_favourite }).then(() => undefined), "Favourite updated.")} aria-label={`${outfit.is_favourite ? "Remove" : "Add"} ${outfit.name} ${outfit.is_favourite ? "from" : "to"} favourites`} aria-pressed={outfit.is_favourite}><Heart className={`h-5 w-5 ${outfit.is_favourite ? "fill-black" : ""}`} /></button></div><div className="mt-4 flex flex-wrap gap-2"><Link href={`/try-on?outfit=${outfit.id}`} className="inline-flex min-h-10 items-center gap-1 bg-black px-3 py-2 text-xs font-bold text-white"><WandSparkles className="h-4 w-4" aria-hidden="true" /> Visualise</Link><button type="button" onClick={() => setEditingOutfit(editingOutfit === outfit.id ? null : outfit.id)} className="inline-flex min-h-10 items-center gap-1 border-2 border-black px-3 py-2 text-xs font-bold"><Pencil className="h-3 w-3" aria-hidden="true" /> Edit</button><button type="button" onClick={() => void archiveOutfit(outfit)} className="min-h-10 border-2 border-black px-3 py-2 text-xs font-bold text-rose-700">Archive</button></div>{editingOutfit === outfit.id && <OutfitEditor outfit={outfit} garments={allGarments} onCancel={() => setEditingOutfit(null)} onError={setError} onSaved={async () => { setEditingOutfit(null); setNotice("Outfit updated."); await load(); }} />}</article>)}</div> : <p className="border-2 border-dashed border-zinc-400 p-8 text-center text-sm text-zinc-500">No matching outfits. Adjust the filters or create one from confirmed garments.</p>}
    </>}
  </div></Layout>;
}
