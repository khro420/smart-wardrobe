import type { FashionCompatibilityDisplay } from "../lib/api";

export default function FashionCompatibilityExplanation({ value }: { value?: FashionCompatibilityDisplay }) {
  if (!value) return null;
  const labels: Record<string,string> = {colour:"Colour harmony",style:"Style coherence",pattern:"Pattern balance",layering:"Sleeve layering",silhouette:"Visible silhouette balance"};
  return <section aria-label="Fashion compatibility v2" className="rounded-xl border border-slate-200 p-3 text-sm">
    <strong>Fashion compatibility v2: {value.compatibility.value ?? value.compatibility.state}</strong>
    <p>Explainable prototype rules, not a validated fashion-quality or professional-appropriateness rating. Exact total: 3/5 request + 1/5 compatibility + 1/5 preference.</p>
    <ul>{value.factors.map(f => <li key={f.name}>{labels[f.name] ?? f.name}: {f.value ?? f.state}; evidence {f.observed}/{f.possible}; active compatibility weight {f.effective_weight}; contribution to total {f.total_contribution}.</li>)}</ul>
    {value.context.channel === "existing_request_R" && <p>Situation style target: {value.context.targets.join(", ")}. Already evaluated in request matching; not counted again in compatibility.</p>}
    {value.context.channel === "compatibility_style" && <p>Situation style comparison: {value.context.targets.join(", ")}, within the style factor. This does not verify an external dress code.</p>}
    <p>Unknown attributes remain unverified and earn no contribution. Structurally inapplicable comparisons have no active weight. Material, physical wearer fit and garment condition are not inferred.</p>
  </section>;
}
