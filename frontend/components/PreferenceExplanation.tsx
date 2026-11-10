"use client";
import type { PreferenceDisplay } from "@/lib/api";
const labels: Record<string,string> = {colour: "Colour", styles: "Style", garment_categories: "Garment category", formality: "Formality", pattern: "Pattern", material: "Material", silhouette: "Visible silhouette", neckline: "Neckline", sleeve_length: "Sleeves", descriptive_tag: "Descriptive tags"};
export default function PreferenceExplanation({display}: {display: PreferenceDisplay}) {
  if (display.kind === "Unavailable") return <p role="status">Stored preference details are unavailable. No score was recomputed.</p>;
  const sequence = display.refinement;
  return <section aria-label="Saved preference ranking" className="min-w-0 space-y-3 rounded-xl bg-slate-50 p-4 text-sm [overflow-wrap:anywhere]">
    <h3 className="font-semibold">Your saved preferences</h3>
    <p>Likes and avoids influence ranking softly. An avoided value earns no preference reward; it does not exclude an outfit. Required conditions always apply.</p>
    {!display.preference_ledger.families.length && <p>No preferences were configured for this request.</p>}
    <ul className="space-y-2">{display.preference_ledger.families.map(f => <li key={f.family}><strong>{labels[f.family] ?? f.family}</strong>: {f.axes.some(a => a.mask) ? "Some preference rewards were already implied by this request and were not counted again." : f.raw.state === "Known" || f.raw.state === "Available" ? "Recorded garment information was used." : "Missing or uncertain information earned no invented reward."}</li>)}</ul>
    {display.objective && <p>{display.objective.explanation} {display.objective.limitations}</p>}
    {display.coverage && <p>{display.coverage.global_optimum_certified ? "This outfit ranks first under the captured facts and ranking conventions." : "Other eligible outfits have unresolved evidence and could rank higher."}</p>}
    {sequence && <section aria-label="Recommendation sequence"><h4 className="font-semibold">{sequence.ordinal ? `Alternative ${sequence.ordinal}` : "Initial option"}</h4><p>Request exclusions: {sequence.excluded_categories.map(c => c.replaceAll("_", " ")).join(", ") || "none"}. These are not saved preferences.</p><p>Alternatives retain the original preferences and style-alignment floor. Changing saved preferences requires a fresh initial request.</p>{sequence.limit_reached && <p>The ten-result limit has been reached. This does not establish exhaustion.</p>}</section>}
    <details><summary className="min-h-11 cursor-pointer py-3 font-semibold">Stored score details</summary><p>Exact ranking total: {display.total.numerator}/{display.total.denominator}. This is a ranking value, not confidence or fashion-quality validation.</p><ul>{display.components.map(c => <li key={c.name}>{c.name}: {c.contribution.numerator}/{c.contribution.denominator}; weighted contribution {c.weighted.numerator}/{c.weighted.denominator}.</li>)}</ul></details>
  </section>;
}
