"use client";
import { useState } from "react";
import { subtypeSummary, type VerifiedSubtypeView, type SubtypeUpdate } from "@/lib/verified-subtypes";
export default function VerifiedSubtypeFields({ view, category, disabled = false, onConfirm }: { view?: VerifiedSubtypeView; category: string; disabled?: boolean; onConfirm: (value: SubtypeUpdate) => Promise<void> }) {
  const [choice, setChoice] = useState(view?.state === "Known" ? view.value ?? "" : "");
  const [reason, setReason] = useState(""); const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  if (!view) return null;
  const applicable = view.registry.applies_to_parents.includes(category);
  const options = view.registry.entries.filter(entry => entry.parents.includes(category));
  if (!applicable && !view.events.length) return null;
  const submit = async () => {
    if (!confirmed || !reason.trim() || busy) return;
    setBusy(true); setError("");
    try {
      await onConfirm({ action_id: crypto.randomUUID(), expected_revision: view.revision, state: !applicable ? "Inapplicable" : choice ? "Known" : "Unspecified", value: applicable && choice ? choice : null, review_basis: "owner_review", reason: reason.trim() });
      window.dispatchEvent(new Event("wearer-category-policy-changed")); setConfirmed(false); setReason("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "The garment type review could not be saved."); }
    finally { setBusy(false); }
  };
  return <section aria-label="Garment type review" className="my-3 space-y-3 rounded-lg border border-slate-300 p-3 text-sm">
    <p className="font-semibold">Garment type: {subtypeSummary(view)}</p>
    <p>This owner review adds a garment type. The extracted category and other attributes stay as recorded. A name or image suggestion does not confirm the type.</p>
    <label className="block">Reviewed garment type<select className="mt-1 min-h-11 w-full rounded border p-2" disabled={disabled || busy || !applicable} value={applicable ? choice : ""} onChange={e => { setChoice(e.target.value); setConfirmed(false); }}><option value="">Unknown / unspecified</option>{options.map(entry => <option key={entry.id} value={entry.id}>{entry.label}</option>)}</select></label>
    {choice && <p>{options.find(entry => entry.id === choice)?.definition}</p>}
    {!applicable && <p>Confirming this correction records that a garment type is no longer applicable to the current category.</p>}
    <label className="block">Reason for this review<input maxLength={500} className="mt-1 min-h-11 w-full rounded border p-2" disabled={disabled || busy} value={reason} onChange={e => setReason(e.target.value)} /></label>
    <label className="flex gap-2"><input type="checkbox" checked={confirmed} disabled={disabled || busy} onChange={e => setConfirmed(e.target.checked)} />I reviewed this garment and confirm this choice, including Unknown when I cannot establish its type.</label>
    <button type="button" disabled={disabled || busy || !confirmed || !reason.trim()} onClick={() => void submit()} className="min-h-11 rounded border px-3 disabled:opacity-50">{busy ? "Saving garment type…" : "Confirm garment type"}</button>
    {error && <p role="alert">{error}</p>}
    {!!view.events.length && <details><summary className="cursor-pointer">Type review history</summary><ul>{view.events.map((event, index) => <li key={index}>{event.recorded_at}: {event.state} {event.subtype?.replaceAll("_", " ")}. {event.reason}</li>)}</ul></details>}
  </section>;
}
