"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { getAccessToken, getAttributePreferences, saveAttributePreferences } from "@/lib/api";
import { authenticationSession } from "@/lib/wearer-selection";
import { AXIS_LABELS, FAMILY_LABELS, SCOPES, copyFamilies, isInheritedFamily, percentageMinimum, preferenceDraftKey, togglePreference, valueKey, type AttributePreferenceCapability, type AttributePreferenceView, type PreferenceAxis, type PreferenceFamilies, type PreferenceFamily, type PreferenceSaveAction, type PreferenceValue } from "@/lib/attribute-preferences";

const label = (value: PreferenceValue) => typeof value === "object" ? `${value.colour}, at least ${Number(value.minimum) * 100}%` : typeof value === "boolean" ? value ? "Yes" : "No" : value.replaceAll("_", " ");
const blankAxis = (scope: string): PreferenceAxis => ({ scope, importance: "1", liked: [], avoided: [] });
function Importance({ value, onChange, name }: { value: string; onChange: (value: string) => void; name: string }) {
  const [custom, setCustom] = useState(false);
  return <label className="block text-sm">{name}<select aria-label={name} value={!custom && ["0", "0.5", "1"].includes(value) ? value : "custom"} onChange={e => { setCustom(e.target.value === "custom"); if (e.target.value !== "custom") onChange(e.target.value); }} className="ml-2 border-2 border-black p-2"><option value="0">Off</option><option value="0.5">Low</option><option value="1">Normal</option><option value="custom">Custom</option></select>{(custom || !["0", "0.5", "1"].includes(value)) && <input aria-label={`${name} custom value`} inputMode="decimal" value={value} onChange={e => onChange(e.target.value)} className="mt-2 w-28 border-2 border-black p-2" />}</label>;
}

function AxisEditor({ axis, definition, capability, onChange }: { axis: PreferenceAxis; definition: { axis: string; default_scope: string }; capability: AttributePreferenceCapability; onChange: (axis: PreferenceAxis) => void }) {
  const [search, setSearch] = useState("");
  const [literal, setLiteral] = useState("");
  const [percentage, setPercentage] = useState("50");
  const [message, setMessage] = useState("");
  const name = definition.axis;
  const finite = (capability.values ?? []).filter(v => v.axis === name);
  const dynamic = name === "descriptive_tag" || ["primary_colour", "secondary_colour", "palette_colour", "palette_coverage"].includes(name);
  const options: PreferenceValue[] = finite.filter(v => v.status !== "Blocked").map(v => v.value);
  for (const v of [...axis.liked, ...axis.avoided]) if (!options.some(item => valueKey(item) === valueKey(v))) options.push(v);
  const add = (polarity: "liked" | "avoided") => {
    try {
      const text = literal.trim().normalize("NFC");
      if (!text) throw new Error("Enter a value first.");
      const value: PreferenceValue = name === "palette_coverage" ? { colour: text.toLowerCase(), minimum: percentageMinimum(percentage) } : name === "descriptive_tag" ? text : text.toLowerCase();
      onChange(togglePreference(axis, value, polarity)); setLiteral(""); setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Check this value."); }
  };
  return <details className="min-w-0 border border-zinc-300 p-3"><summary className="cursor-pointer font-bold">{AXIS_LABELS[name]} ({axis.liked.length} liked, {axis.avoided.length} avoided)</summary>
    <div className="mt-3 space-y-3">
      <label className="block text-sm">Apply to<select value={axis.scope} onChange={e => onChange({ ...axis, scope: e.target.value })} className="ml-2 max-w-full border-2 border-black p-2">{Object.entries(SCOPES).map(([key, text]) => <option value={key} key={key}>{text}</option>)}</select></label>
      <Importance name={`${AXIS_LABELS[name]} importance`} value={axis.importance} onChange={importance => onChange({ ...axis, importance })} />
      {name === "material" && <p className="text-sm">Recorded material labels only; this does not establish fibre purity or allergy safety.</p>}
      {name === "palette_coverage" && <p className="text-sm">Minimum share of a garment&apos;s recorded image palette, rather than whole-outfit area.</p>}
      {options.length > 8 && <label className="block text-sm">Search {AXIS_LABELS[name].toLowerCase()}<input type="search" value={search} onChange={e => setSearch(e.target.value)} className="mt-1 w-full border-2 border-black p-2" /></label>}
      <div className="max-h-80 space-y-2 overflow-y-auto">{options.filter(v => label(v).toLowerCase().includes(search.toLowerCase())).map(v => <div key={valueKey(v)} className="flex flex-wrap items-center gap-2 rounded border p-2"><span className="min-w-0 flex-1 break-words">{label(v)}</span>{(["liked", "avoided"] as const).map(p => <button type="button" key={p} aria-pressed={axis[p].some(x => valueKey(x) === valueKey(v))} aria-label={`${p === "liked" ? "Like" : "Avoid"} ${AXIS_LABELS[name]} ${label(v)}`} onClick={() => onChange(togglePreference(axis, v, p))} className={`min-h-11 border-2 border-black px-3 ${axis[p].some(x => valueKey(x) === valueKey(v)) ? "bg-black text-white" : "bg-white"}`}>{p === "liked" ? "Like" : "Avoid"}</button>)}</div>)}</div>
      {finite.filter(v => v.status === "Blocked").map(v => <p key={valueKey(v.value)} className="text-sm text-zinc-600">{label(v.value)} is unavailable: {v.blocker}.</p>)}
      {dynamic && <div className="space-y-2"><label className="block text-sm">{name === "descriptive_tag" ? "Add a literal descriptive tag" : name === "palette_coverage" ? "Colour name or exact hex" : "Add an exact hex colour"}<input maxLength={100} value={literal} onChange={e => setLiteral(e.target.value)} className="mt-1 w-full border-2 border-black p-2" /></label>{name === "palette_coverage" && <label className="block text-sm">Minimum image coverage (%)<input inputMode="decimal" value={percentage} onChange={e => setPercentage(e.target.value)} className="ml-2 w-24 border-2 border-black p-2" /></label>}<div className="flex gap-2"><button type="button" onClick={() => add("liked")} className="min-h-11 border-2 border-black px-3">Add liked value</button><button type="button" onClick={() => add("avoided")} className="min-h-11 border-2 border-black px-3">Add avoided value</button></div></div>}
      {message && <p role="alert">{message}</p>}
      <button type="button" onClick={() => onChange({ ...axis, liked: [], avoided: [] })} className="min-h-11 border-2 border-black px-3">Clear this selection</button>
    </div>
  </details>;
}

export default function AttributePreferenceEditor({ wearerId, wearerName, capability }: { wearerId: string; wearerName: string; capability: AttributePreferenceCapability }) {
  const [view, setView] = useState<AttributePreferenceView>();
  const [families, setFamilies] = useState<PreferenceFamilies>({});
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState("");
  const identity = useRef<{ session: string; token: string } | undefined>(undefined);
  const pending = useRef<PreferenceSaveAction | undefined>(undefined);
  const applyView = useCallback((next: AttributePreferenceView) => { setView(next); setFamilies(copyFamilies(next.document?.families ?? {})); setRevision(next.revision); pending.current = undefined; }, []);
  useEffect(() => {
    let live = true;
    const session = authenticationSession(), token = getAccessToken();
    if (!token) return;
    identity.current = { session, token };
    void getAttributePreferences(wearerId, token).then(next => {
      if (!live || authenticationSession() !== session) return;
      applyView(next);
      try {
        const draft = JSON.parse(sessionStorage.getItem(preferenceDraftKey(wearerId, session)) ?? "null");
        if (draft?.wearerId === wearerId && draft.session === session && typeof draft.revision === "string" && draft.families && typeof draft.families === "object") {
          setFamilies(draft.families); setRevision(draft.revision); setMessage("Your unsaved preference edits were restored. A changed server revision requires review before saving.");
          if (draft.action?.wearer_id === wearerId) pending.current = draft.action;
        }
      } catch { /* Invalid local drafts never establish server preference evidence. */ }
    }).catch(error => { if (live) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not load preferences."); } });
    return () => { live = false; };
  }, [wearerId, applyView]);
  const change = (next: PreferenceFamilies) => {
    setFamilies(next); pending.current = undefined;
    const session = identity.current?.session;
    if (session) sessionStorage.setItem(preferenceDraftKey(wearerId, session), JSON.stringify({ session, wearerId, revision, families: next }));
  };
  const save = async (event: FormEvent) => {
    event.preventDefault();
    const captured = identity.current;
    if (!view || !captured) return;
    if (captured.session !== authenticationSession()) { setFailed(true); setMessage("Your sign-in session changed. Reload before saving."); return; }
    if (JSON.stringify(families) === JSON.stringify(view.document?.families ?? {})) { setFailed(false); setMessage("No preference changes to save."); return; }
    const action = pending.current ?? { contract: "attribute-preferences-update-1.0.0" as const, wearer_id: wearerId, expected_revision: revision, action_id: crypto.randomUUID(), families: copyFamilies(families) };
    pending.current = action;
    sessionStorage.setItem(preferenceDraftKey(wearerId, captured.session), JSON.stringify({ session: captured.session, wearerId, revision, families, action }));
    setBusy(true); setMessage("");
    try {
      const next = await saveAttributePreferences(action, captured.token);
      if (authenticationSession() !== captured.session) return;
      applyView(next); sessionStorage.removeItem(preferenceDraftKey(wearerId, captured.session)); setFailed(false); setMessage(`Soft preferences saved for ${wearerName}. Start a fresh recommendation to use them.`);
    } catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not save. Your edits and action are retained."); }
    finally { setBusy(false); }
  };
  const cancel = () => { if (view) applyView(view); if (identity.current) sessionStorage.removeItem(preferenceDraftKey(wearerId, identity.current.session)); setFailed(false); setMessage("Edits cancelled."); };
  const reload = async () => { const captured = identity.current; if (!captured || captured.session !== authenticationSession()) return; try { const next = await getAttributePreferences(wearerId, captured.token); if (captured.session === authenticationSession()) { applyView(next); sessionStorage.removeItem(preferenceDraftKey(wearerId, captured.session)); setFailed(false); setMessage("Latest preferences loaded. Previous unsaved edits were discarded."); } } catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Could not reload."); } };
  return <form onSubmit={save} className="min-w-0 space-y-4 border-2 border-black bg-white p-4" aria-label={`Soft preferences for ${wearerName}`} aria-busy={busy}>
    <h2 className="text-xl font-black">Soft preferences for {wearerName}</h2>
    <p>Likes and avoids influence ranking. They never override your request&apos;s requirements or exclusions. You can leave every family off; no new setup is required.</p>
    {!view && !failed && <p role="status">Loading soft preferences…</p>}
    <fieldset disabled={busy || !view} className="min-w-0 space-y-3"><legend className="sr-only">Saved soft preferences</legend>
      {(capability.families ?? []).map(family => {
        const record: PreferenceFamily = families[family] ?? { mode: isInheritedFamily(family) ? "inherit_p1" : "disabled" };
        return <details key={family} className="min-w-0 border-2 border-black p-3"><summary className="cursor-pointer font-bold">{FAMILY_LABELS[family]}</summary><div className="mt-3 space-y-3">
          <label className="block text-sm">{FAMILY_LABELS[family]} setting<select aria-label={`${FAMILY_LABELS[family]} setting`} value={record.mode} onChange={e => change({ ...families, [family]: e.target.value === "override" ? { mode: "override", importance: "1", axes: {} } : { mode: e.target.value as "inherit_p1" | "disabled" } })} className="mt-1 block max-w-full border-2 border-black p-2"><option value="disabled">Off</option>{isInheritedFamily(family) && <option value="inherit_p1">Use existing preference</option>}<option value="override">Choose likes and avoids</option></select></label>
          {record.mode === "inherit_p1" && <p className="text-sm">Your existing preference and its importance are retained{view?.effective[family] ? ` (Custom importance preserved: ${view.effective[family].importance === "1" ? "Normal" : "Custom"})` : "; none is currently configured"}.</p>}
          {record.mode === "override" && <><Importance name={`${FAMILY_LABELS[family]} family importance`} value={record.importance} onChange={importance => change({ ...families, [family]: { ...record, importance } })} />{family === "colour" && <p className="text-sm">Colour controls share one bounded family importance.</p>}{(capability.axes ?? []).filter(a => a.family === family).map(definition => <AxisEditor key={definition.axis} axis={record.axes[definition.axis] ?? blankAxis(definition.default_scope)} definition={definition} capability={capability} onChange={axis => change({ ...families, [family]: { ...record, axes: { ...record.axes, [definition.axis]: axis } } })} />)}</>}
          <button type="button" onClick={() => change({ ...families, [family]: { mode: "disabled" } })} className="min-h-11 border-2 border-black px-3">Clear {FAMILY_LABELS[family].toLowerCase()} preference</button>
        </div></details>;
      })}
    </fieldset>
    {message && <p role={failed ? "alert" : "status"} className="break-words">{message}</p>}
    <div className="flex flex-wrap gap-3"><button disabled={busy || !view} className="min-h-11 bg-black px-4 py-2 font-bold text-white disabled:opacity-40">Save soft preferences</button><button disabled={busy || !view} type="button" onClick={cancel} className="min-h-11 border-2 border-black px-4">Cancel preference edits</button>{failed && <button disabled={busy} type="button" onClick={() => void reload()} className="min-h-11 border-2 border-black px-4">Discard edits and reload</button>}</div>
  </form>;
}
