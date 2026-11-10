"use client";
import { useWearerCategoryEligibility } from "@/lib/wearer-category-eligibility";

import { FormEvent, useEffect, useState } from "react";
import Layout from "@/components/Layout";
import AttributePreferenceEditor from "@/components/AttributePreferenceEditor";
import { selectedWearer } from "@/lib/wearer-selection";
import type { AttributePreferenceCapability } from "@/lib/attribute-preferences";
import { getWearerProfileDetails, saveWearerProfileDetails, type WearerProfileDetails, getAttributePreferenceCapabilities } from "@/lib/api";
import { createWardrobeProfile, archiveWardrobeProfile, getPreferences, getPreferenceOptions, getProfile, getSelectedWardrobeProfileId, getWardrobeProfiles, savePreference, setSelectedWardrobeProfileId, updateProfile, type Profile, type PreferenceOptions, type UserPreference, type WardrobeProfile } from "@/lib/api";

type Kind = keyof PreferenceOptions;
type Draft = { values: string[]; weight: number };
const LABELS: Record<Kind, string> = { colours: "Colours", styles: "Styles", garment_categories: "Garment categories", formality: "Formality" };
const KINDS = Object.keys(LABELS) as Kind[];
const emptyDraft = (): Draft => ({ values: [], weight: 1 });
function storedDraft(kind: Kind, rows: UserPreference[]): Draft {
  const row = rows.find((item) => item.preference_type === kind);
  const raw = row?.preference_value.values;
  const values = Array.isArray(raw) ? raw.flatMap((value) => {
    if (typeof value === "string") return [value];
    if (kind === "garment_categories" && value && typeof value === "object" && "kind" in value && "value" in value) return [`${value.kind}:${value.value}`];
    return [];
  }) : [];
  return { values, weight: row?.weight ?? 1 };
}

function PreferenceEditor({ kind, options, stored, onSaved }: { kind: Kind; options: string[]; stored: Draft; onSaved: (next: Draft) => void }) {
  const [draft, setDraft] = useState<Draft>(stored);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const save = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const values = kind === "garment_categories" ? draft.values.map((value) => { const [kind, category] = value.split(":"); return { kind, value: category }; }) : draft.values;
      await savePreference(kind, { values }, draft.weight);
      onSaved({ values: [...draft.values], weight: draft.weight });
      setFailed(false); setMessage(draft.values.length ? "Preference saved for future recommendations." : "Preference cleared.");
    } catch (error) {
      setFailed(true); setMessage(error instanceof Error ? error.message : "Could not save preference. Your edits are retained; try again.");
    } finally { setBusy(false); }
  };
  return <form onSubmit={save} aria-label={`${LABELS[kind]} preferences`} aria-busy={busy} className="space-y-4 border-2 border-black bg-white p-6">
    <fieldset disabled={busy}><legend className="text-xl font-black">{LABELS[kind]}</legend>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">{options.map((value) => <label key={value} className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={draft.values.includes(value)} onChange={(event) => setDraft({ ...draft, values: event.target.checked ? [...draft.values, value] : draft.values.filter((item) => item !== value) })} />{value.replace(":", ": ").replaceAll("_", " ")}</label>)}</div>
      {draft.values.some((value) => !options.includes(value)) && <p className="mt-2 text-sm">This stored preference includes values outside the supported choices. Existing records remain stored until you save supported choices.</p>}
      <label className="mt-4 block text-sm font-bold">{LABELS[kind]} importance<input type="number" required min={0} max={1} step="0.01" value={draft.weight} onChange={(event) => setDraft({ ...draft, weight: event.target.valueAsNumber })} className="ml-3 w-24 border-2 border-black p-2" /></label>
    </fieldset>
    <p className="text-xs text-zinc-600">Importance ranges from 0 (ignored) to 1. Clear every selection and save to remove this preference. Preferences influence ranking within mandatory request constraints.</p>
    {message && <p role={failed ? "alert" : "status"}>{message}</p>}
    <div className="flex flex-wrap gap-3"><button disabled={busy} className="min-h-11 bg-black px-4 py-2 font-bold text-white disabled:opacity-40">Save {LABELS[kind].toLowerCase()}</button><button type="button" disabled={busy} onClick={() => setDraft({ ...draft, values: [] })} className="min-h-11 border-2 border-black px-4 py-2">Clear {LABELS[kind].toLowerCase()} selection</button><button type="button" disabled={busy} onClick={() => { setDraft({ values: [...stored.values], weight: stored.weight }); setMessage("Edits cancelled."); setFailed(false); }} className="min-h-11 border-2 border-black px-4 py-2">Cancel {LABELS[kind].toLowerCase()}</button></div>
  </form>;
}


function WearerDetailsEditor({ wearer }: { wearer: WardrobeProfile }) {
  const categoryPolicy = useWearerCategoryEligibility(wearer.id);
  const [stored, setStored] = useState<WearerProfileDetails>();
  const [gender, setGender] = useState("");
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    void getWearerProfileDetails(wearer.id).then(next => {
      if (live && next.profile_id === wearer.id) { setStored(next); setGender(next.gender_identity ?? ""); }
    }).catch((error: unknown) => { if (live) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not load wearer information."); } });
    return () => { live = false; };
  }, [wearer.id]);
  const save = async (event: FormEvent) => {
    event.preventDefault(); if (!stored) return; setBusy(true); setMessage("");
    try {
      const next = await saveWearerProfileDetails(wearer.id, stored.revision, gender.trim().normalize("NFC") || null);
      if (getSelectedWardrobeProfileId() !== wearer.id) return;
      setStored(next); setGender(next.gender_identity ?? ""); window.dispatchEvent(new Event("wearer-category-policy-changed")); setFailed(false); setMessage("Wearer information saved.");
    } catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not save. Your edits are retained."); }
    finally { setBusy(false); }
  };
  const preset = !gender ? "unspecified" : ["male", "female"].includes(gender) ? gender : "custom";
  return <form onSubmit={save} aria-label="Wearer information" aria-busy={busy} className="space-y-4 border-2 border-black bg-white p-6">
    <h2 className="text-xl font-black">Wearer information: {wearer.name}</h2>
    <p className="text-sm">{categoryPolicy.data?.enabled ? "This application uses Male/Female to determine permitted garment categories. Male excludes skirts and dresses; Female permits all supported categories. Other descriptions need an approved policy before new work. Shared inventory and historical records stay available." : "Optional profile information. Gender does not filter garments or change outfit ranking. Choose your clothing preferences separately below."}</p>
    <fieldset disabled={busy || !stored} className="space-y-3">
      <label className="block font-bold">Gender (optional)<select value={preset} onChange={event => setGender(event.target.value === "unspecified" ? "" : event.target.value === "custom" ? "Self-described" : event.target.value)} className="mt-1 w-full border-2 border-black p-2"><option value="unspecified">Unspecified</option><option value="male">Male</option><option value="female">Female</option><option value="custom">Self-described</option></select></label>
      {preset === "custom" && <label className="block">Gender description<input maxLength={60} required value={gender} onChange={event => setGender(event.target.value)} className="mt-1 w-full border-2 border-black p-2" /></label>}
      <div className="flex flex-wrap gap-3"><button className="min-h-11 bg-black px-4 py-2 font-bold text-white">Save wearer information</button><button type="button" onClick={() => { setGender(stored?.gender_identity ?? ""); setMessage("Edits cancelled."); setFailed(false); }} className="min-h-11 border-2 border-black px-4 py-2">Cancel wearer information</button><button type="button" onClick={() => { void getWearerProfileDetails(wearer.id).then(next => { if (getSelectedWardrobeProfileId() === wearer.id) { setStored(next); setMessage("Latest revision loaded. Your draft is retained."); setFailed(false); } }).catch((error: unknown) => { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not reload."); }); }} className="min-h-11 border-2 border-black px-4 py-2">Reload wearer revision</button></div>
    </fieldset>
    {message && <p role={failed ? "alert" : "status"}>{message}</p>}
  </form>;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>();
  const [name, setName] = useState("");
  const [options, setOptions] = useState<PreferenceOptions>();
  const [saved, setSaved] = useState<Record<Kind, Draft>>({ colours: emptyDraft(), styles: emptyDraft(), garment_categories: emptyDraft(), formality: emptyDraft() });
  const [legacyNote, setLegacyNote] = useState<string>();
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [wardrobes, setWardrobes] = useState<WardrobeProfile[]>([]);
  const [archivedWearers, setArchivedWearers] = useState<WardrobeProfile[]>([]);
  const [newWardrobeName, setNewWardrobeName] = useState("");
  const [creatingWardrobe, setCreatingWardrobe] = useState(false);
  const [archivingWardrobeId, setArchivingWardrobeId] = useState<string>();
  const [attributeCapability, setAttributeCapability] = useState<AttributePreferenceCapability>({ enabled: false });
  useEffect(() => { let live = true; void getAttributePreferenceCapabilities().then(value => { if (live) setAttributeCapability(value); }).catch(() => { /* Existing preferences remain available if P2 capabilities cannot be loaded. */ }); return () => { live = false; }; }, []);
  useEffect(() => {
    let active = true;
    void Promise.all([getProfile(), getPreferences(), getPreferenceOptions(), getWardrobeProfiles(), getWardrobeProfiles("archived")]).then(([next, rows, choices, profiles, archived]) => {
      if (!active) return;
      setProfile(next); setName(next.display_name); setOptions(choices);
      setWardrobes(profiles); setArchivedWearers(archived);
      setSaved({ colours: storedDraft("colours", rows), styles: storedDraft("styles", rows), garment_categories: storedDraft("garment_categories", rows), formality: storedDraft("formality", rows) });
      const note = rows.find((row) => row.preference_type === "style_note")?.preference_value.value;
      setLegacyNote(typeof note === "string" ? note : undefined);
    }).catch((error: unknown) => { if (active) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not load profile."); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const save = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try { const next = await updateProfile(name.trim()); setProfile(next); setName(next.display_name); setFailed(false); setMessage("Profile updated."); }
    catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not save profile. Your edits are retained."); }
    finally { setBusy(false); }
  };
  const createWardrobe = async (event: FormEvent) => {
    event.preventDefault(); setCreatingWardrobe(true); setMessage("");
    try { const created = await createWardrobeProfile(newWardrobeName.trim()); setWardrobes((current) => [...current, created]); setNewWardrobeName(""); window.dispatchEvent(new Event("smart-wardrobe-profiles-changed")); setFailed(false); setMessage(`${created.name} is ready. Select it from the active wearer menu.`); }
    catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not create this wardrobe."); }
    finally { setCreatingWardrobe(false); }
  };
  const archiveWardrobe = async (wardrobe: WardrobeProfile) => {
    if (!window.confirm(`Archive wearer “${wardrobe.name}”? Their history, preferences, images and completed visualisations will be retained. Shared garments and outfits stay available. Finish or cancel pending work first.`)) return;
    setArchivingWardrobeId(wardrobe.id); setMessage("");
    try {
      const result = await archiveWardrobeProfile(wardrobe.id);
      const archivedActiveWardrobe = getSelectedWardrobeProfileId() === wardrobe.id;
      setWardrobes((current) => current.filter((item) => item.id !== wardrobe.id));
      setArchivedWearers((current) => [...current, { ...wardrobe, status: "archived", is_default: false }]);
      if (archivedActiveWardrobe) setSelectedWardrobeProfileId(result.next_profile_id);
      window.dispatchEvent(new Event("smart-wardrobe-profiles-changed"));
      setFailed(false); setMessage(`${wardrobe.name} was archived. Shared inventory and historical records were retained.`);
      if (archivedActiveWardrobe) window.setTimeout(() => window.location.reload(), 250);
    } catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not archive this wearer."); }
    finally { setArchivingWardrobeId(undefined); }
  };
  const activeWearer = selectedWearer(wardrobes);
  return <Layout><div className="mx-auto max-w-2xl space-y-6" aria-busy={loading}>
    <h1 className="text-2xl font-black">Your profile</h1>
    {message && <p role={failed ? "alert" : "status"} className="border-2 border-black p-3">{message}</p>}
    {loading && <p role="status">Loading profile…</p>}
    {profile && options && <>
      <form onSubmit={save} aria-label="Profile information" className="space-y-4 border-2 border-black bg-white p-6">
        <label className="block text-sm font-bold">Display name<input required maxLength={100} value={name} disabled={busy} onChange={(event) => setName(event.target.value)} className="mt-1 w-full border-2 border-black p-2" /></label>
        <label className="block text-sm font-bold">Email<input readOnly value={profile.email} className="mt-1 w-full border-2 border-zinc-300 bg-zinc-100 p-2" /></label>
        <div className="flex flex-wrap gap-3"><button disabled={busy || !name.trim()} className="min-h-11 bg-black px-4 py-2 font-bold text-white disabled:opacity-40">Save profile</button><button type="button" disabled={busy} onClick={() => { setName(profile.display_name); setFailed(false); setMessage("Edits cancelled."); }} className="min-h-11 border-2 border-black px-4 py-2">Cancel profile</button></div>
      </form>
      {activeWearer && <WearerDetailsEditor key={activeWearer.id} wearer={activeWearer} />}
      <h2 className="text-xl font-black">Clothing preferences</h2>
      <section className="space-y-4 border-2 border-black bg-white p-6"><div><h2 className="text-xl font-black">Wearer profiles</h2><p className="mt-1 text-sm text-zinc-600">All wearers use one shared wardrobe of garments and outfits. Each wearer has separate preferences, chats and recommendations. Select the active wearer before asking for an outfit.</p></div><ul className="space-y-2">{wardrobes.map((wardrobe) => <li key={wardrobe.id} className="flex flex-wrap items-center justify-between gap-3 border border-zinc-200 p-3"><span className="font-semibold">{wardrobe.name}{wardrobe.is_default ? " (default)" : ""}</span><button type="button" disabled={wardrobes.length === 1 || archivingWardrobeId !== undefined} onClick={() => void archiveWardrobe(wardrobe)} className="min-h-10 border-2 border-rose-700 px-3 text-sm font-bold text-rose-700 disabled:cursor-not-allowed disabled:opacity-40">{archivingWardrobeId === wardrobe.id ? "Archiving…" : "Archive wearer"}</button></li>)}</ul>{wardrobes.length === 1 && <p className="text-xs text-zinc-600">Create another wearer before archiving this one, so the account always retains an active wearer.</p>}<form onSubmit={createWardrobe} className="flex flex-wrap gap-2"><label className="sr-only" htmlFor="new-wardrobe-name">New wearer name</label><input id="new-wardrobe-name" required maxLength={60} value={newWardrobeName} disabled={creatingWardrobe} onChange={(event) => setNewWardrobeName(event.target.value)} placeholder="e.g. Alex" className="min-h-11 flex-1 border-2 border-black px-3" /><button disabled={creatingWardrobe || !newWardrobeName.trim()} className="min-h-11 bg-black px-4 py-2 font-bold text-white disabled:opacity-40">Add wearer</button></form></section>
      {archivedWearers.length > 0 && <section className="border-2 border-black p-4"><h2 className="font-bold">Archived wearers</h2><p className="text-sm">Records are retained. Archived wearers cannot start new work.</p><ul>{archivedWearers.map((wearer) => <li key={wearer.id} className="mt-2"><span>{wearer.name} — Archived</span> <a className="underline" href={`/history?view=historical&wearer_profile_id=${encodeURIComponent(wearer.id)}`}>Recommendation history</a> · <a className="underline" href={`/extract/results?view=historical&wearer_profile_id=${encodeURIComponent(wearer.id)}`}>Processing history</a></li>)}</ul></section>}
      {legacyNote !== undefined && <aside className="border-2 border-black p-4 text-sm"><p className="font-bold">Earlier style note</p><p className="whitespace-pre-wrap break-words">{legacyNote}</p><p className="mt-2">Only a supported whole style name influences ranking; structured styles take precedence when selected. This earlier note is retained.</p></aside>}
      {attributeCapability.enabled ? activeWearer ? <AttributePreferenceEditor key={activeWearer.id} wearerId={activeWearer.id} wearerName={activeWearer.name} capability={attributeCapability} /> : <p role="status">Choose the intended wearer in Active wearer to edit soft preferences.</p> : KINDS.map((kind) => <PreferenceEditor key={kind} kind={kind} stored={saved[kind]} options={kind === "garment_categories" ? options.garment_categories.map((item) => `${item.kind}:${item.value}`) : options[kind]} onSaved={(next) => setSaved((current) => ({ ...current, [kind]: next }))} />)}
      <p className="text-sm text-zinc-600">Your profile, wardrobe and preferences are private to your account. Your sign-in email cannot be changed here.</p>
    </>}
  </div></Layout>;
}
