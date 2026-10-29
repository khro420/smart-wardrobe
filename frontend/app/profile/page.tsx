"use client";

import { FormEvent, useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { createWardrobeProfile, deleteWardrobeProfile, getPreferences, getPreferenceOptions, getProfile, getSelectedWardrobeProfileId, getWardrobeProfiles, savePreference, setSelectedWardrobeProfileId, updateProfile, type Profile, type PreferenceOptions, type UserPreference, type WardrobeProfile } from "@/lib/api";

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
  const [newWardrobeName, setNewWardrobeName] = useState("");
  const [creatingWardrobe, setCreatingWardrobe] = useState(false);
  const [deletingWardrobeId, setDeletingWardrobeId] = useState<string>();
  useEffect(() => {
    let active = true;
    void Promise.all([getProfile(), getPreferences(), getPreferenceOptions(), getWardrobeProfiles()]).then(([next, rows, choices, profiles]) => {
      if (!active) return;
      setProfile(next); setName(next.display_name); setOptions(choices);
      setWardrobes(profiles);
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
    try { const created = await createWardrobeProfile(newWardrobeName.trim()); setWardrobes((current) => [...current, created]); setNewWardrobeName(""); window.dispatchEvent(new Event("smart-wardrobe-profiles-changed")); setFailed(false); setMessage(`${created.name} is ready. Select it from the active wardrobe menu.`); }
    catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not create this wardrobe."); }
    finally { setCreatingWardrobe(false); }
  };
  const deleteWardrobe = async (wardrobe: WardrobeProfile) => {
    if (!window.confirm(`Delete “${wardrobe.name}” and all of its garments, outfits, uploads, preferences and recommendation history? This cannot be undone.`)) return;
    setDeletingWardrobeId(wardrobe.id); setMessage("");
    try {
      const result = await deleteWardrobeProfile(wardrobe.id);
      const deletedActiveWardrobe = getSelectedWardrobeProfileId() === wardrobe.id;
      setWardrobes((current) => current.filter((item) => item.id !== wardrobe.id));
      if (deletedActiveWardrobe) setSelectedWardrobeProfileId(result.next_profile_id);
      window.dispatchEvent(new Event("smart-wardrobe-profiles-changed"));
      setFailed(false); setMessage(`${wardrobe.name} and its profile data were permanently deleted.`);
      if (deletedActiveWardrobe) window.setTimeout(() => window.location.reload(), 250);
    } catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not delete this wardrobe."); }
    finally { setDeletingWardrobeId(undefined); }
  };
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
      <h2 className="text-xl font-black">Clothing preferences</h2>
      <section className="space-y-4 border-2 border-black bg-white p-6"><div><h2 className="text-xl font-black">Wardrobe profiles</h2><p className="mt-1 text-sm text-zinc-600">Each profile has its own garments, outfits, uploads, recommendations and clothing preferences. Select the active profile from the navigation menu before adding items or asking for an outfit.</p></div><ul className="space-y-2">{wardrobes.map((wardrobe) => <li key={wardrobe.id} className="flex flex-wrap items-center justify-between gap-3 border border-zinc-200 p-3"><span className="font-semibold">{wardrobe.name}{wardrobe.is_default ? " (default)" : ""}</span><button type="button" disabled={wardrobes.length === 1 || deletingWardrobeId !== undefined} onClick={() => void deleteWardrobe(wardrobe)} className="min-h-10 border-2 border-rose-700 px-3 text-sm font-bold text-rose-700 disabled:cursor-not-allowed disabled:opacity-40">{deletingWardrobeId === wardrobe.id ? "Deleting…" : "Delete wardrobe"}</button></li>)}</ul>{wardrobes.length === 1 && <p className="text-xs text-zinc-600">Create another wardrobe before deleting this one, so the shared account always retains a usable profile.</p>}<form onSubmit={createWardrobe} className="flex flex-wrap gap-2"><label className="sr-only" htmlFor="new-wardrobe-name">New wardrobe name</label><input id="new-wardrobe-name" required maxLength={60} value={newWardrobeName} disabled={creatingWardrobe} onChange={(event) => setNewWardrobeName(event.target.value)} placeholder="e.g. Alex" className="min-h-11 flex-1 border-2 border-black px-3" /><button disabled={creatingWardrobe || !newWardrobeName.trim()} className="min-h-11 bg-black px-4 py-2 font-bold text-white disabled:opacity-40">Create wardrobe</button></form></section>
      {legacyNote !== undefined && <aside className="border-2 border-black p-4 text-sm"><p className="font-bold">Earlier style note</p><p className="whitespace-pre-wrap break-words">{legacyNote}</p><p className="mt-2">Only a supported whole style name influences ranking; structured styles take precedence when selected. This earlier note is retained.</p></aside>}
      {KINDS.map((kind) => <PreferenceEditor key={kind} kind={kind} stored={saved[kind]} options={kind === "garment_categories" ? options.garment_categories.map((item) => `${item.kind}:${item.value}`) : options[kind]} onSaved={(next) => setSaved((current) => ({ ...current, [kind]: next }))} />)}
      <p className="text-sm text-zinc-600">Your profile, wardrobe and preferences are private to your account. Your sign-in email cannot be changed here.</p>
    </>}
  </div></Layout>;
}
