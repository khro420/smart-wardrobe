import type { LocalPreferenceDisplay } from "@/lib/api";

export default function LocalPreferenceExplanation({display}: {display: LocalPreferenceDisplay}) {
  const wish=display.optional_intent;
  const state=display.decision.selected_optional.state;
  return <section aria-label="Optional outfit preference" className="space-y-2 rounded-xl border border-slate-200 p-4 text-sm">
    <h3 className="font-semibold">Your optional preference</h3>
    <p>{wish.role === "upper" ? "Top" : "Bottom"}: {wish.predicates.flatMap(p => p.values).map(v => v.replaceAll("_", " ")).join(" · ")}</p>
    <p>{state === "Satisfied" ? "This outfit matches the preference using qualified recorded evidence." : state === "Unverifiable" ? "The preference could not be verified from recorded garment evidence. It was not treated as a match." : "The preference was not matched. It did not remove otherwise eligible outfits."}</p>
    {display.decision.explanation === "original_baseline_retained" && <p>The original baseline outfit was retained; no preference-based promotion was made.</p>}
    {display.decision.optional_counts?.Satisfied === 0 && <p>No eligible outfit was verified to match the preference. Missing evidence does not prove that none could match.</p>}
    {wish.resolution.state === "ContradictedByHard" && <p>Your mandatory requirement overrides the conflicting preference.</p>}
    {wish.resolution.state === "EntailedByHard" && <p>This preference is already required; it adds no separate benefit.</p>}
    <p>Mandatory conditions remain strict. Optional preferences add no score weight; they may change the selection only within the existing quality limits.</p>
    <p>Suggest another outfit is unavailable for preference requests. Start a new chat for a fresh request.</p>
  </section>;
}
