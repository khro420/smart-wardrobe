import type { IntegratedRecommendation, ScoringDisplay } from "@/lib/api";

const labels = {
  Computed: "Rule-based compatibility",
  PartiallyConventional: "Partially estimated compatibility contribution",
  FullyConventional: "Default compatibility contribution due to unavailable evidence",
  NoPairReference: "Default contribution for a single-piece outfit",
} as const;

function percent(value: { numerator: number; denominator: number }) {
  return `${Number((100 * value.numerator / value.denominator).toFixed(1))}%`;
}

export default function CompatibilityExplanation({ recommendation }: { recommendation: IntegratedRecommendation }) {
  const view: ScoringDisplay | undefined = recommendation.scoring_display;
  if (!view) {
    return recommendation.provenance?.scoring_profile === "compatibility_deferred"
      ? <p className="text-sm text-slate-600">Ranked using request and supported preferences. Compatibility was not measured.</p>
      : null;
  }
  if (view.version !== "assistant-scoring-display-1.0.0" || view.kind === "Unavailable") {
    return <p className="text-sm text-slate-600">Scoring details are unavailable for this recorded recommendation.</p>;
  }
  if (view.kind === "Deferred") {
    return <p className="text-sm text-slate-600">Ranked using request and supported preferences. Compatibility was not measured.</p>;
  }
  return <section className="space-y-2 text-sm text-slate-600" aria-label="Compatibility scoring" data-testid="compatibility-explanation">
    <p className="font-semibold">{labels[view.basis]}</p>
    <p>Contribution used for ranking: {percent(view.decision_contribution)}.</p>
    {view.basis === "Computed"
      ? <p>Calculated from supported colour and style rules. This is not an independent fashion rating.</p>
      : view.basis === "NoPairReference"
        ? <p>A single-piece outfit has no garment-pair comparisons. The default contribution is a ranking convention, not a measured quality rating.</p>
        : <p>{view.basis === "FullyConventional" ? "Colour and style evidence is unavailable." : "Some colour or style evidence is unavailable."} A midpoint convention is used for ranking. Unknown evidence does not mean poor compatibility.</p>}
    <details>
      <summary className="cursor-pointer underline">Compatibility details</summary>
      <p>Raw compatibility: {view.raw_value === null ? view.raw_state === "NotApplicable" ? "Not applicable" : "Unknown" : percent(view.raw_value)}.</p>
      <p>Available rule evidence: {view.known} of {view.possible} comparisons.</p>
      {view.lower !== null && view.upper !== null && view.basis !== "Computed" && <p>Possible-value range: {percent(view.lower)} to {percent(view.upper)}. This is not a confidence interval.</p>}
    </details>
  </section>;
}
