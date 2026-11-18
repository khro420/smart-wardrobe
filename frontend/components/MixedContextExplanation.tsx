import type { MixedContextDisplay } from "../lib/api";

export default function MixedContextExplanation({ value }: { value?: MixedContextDisplay }) {
  if (!value) return null;
  return <section aria-label="Contextual recommendation" className="rounded-xl border border-slate-200 p-3 text-sm">
    <strong>Context: {value.summary.label}</strong>
    {value.interview_default?.inferred && <p role="note">{value.interview_default.message}</p>}
    {value.summary.assumptions.map((note, index) => <p key={index}>{note}</p>)}
    {value.summary.policy_note && <p>{value.summary.policy_note}</p>}
    {value.summary.limits_note && <p>{value.summary.limits_note}</p>}
    <p>Context suitability and mandatory garment conditions were checked before optional preferences.</p>
    {value.selection_mode === "baseline_disclosed_v1" && <p>No complete relative appearance score was available. The existing baseline ranking was retained among context-eligible outfits.</p>}
    {value.selection_mode !== "baseline_disclosed_v1" && (value.coverage?.unresolved_candidates ?? 0) > 0 && value.global_optimum_certified === false && <p>Some otherwise eligible outfits lack complete appearance evidence; their relative ranking remains uncertain.</p>}
  </section>;
}
