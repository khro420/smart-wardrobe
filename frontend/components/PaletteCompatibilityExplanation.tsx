import type { PaletteCompatibilityDisplay, StringRatio } from "@/lib/api";

function exact(value: StringRatio | null): string {
  if (value === null) return "not applicable";
  const { numerator, denominator } = value;
  if (typeof numerator !== "string" || typeof denominator !== "string" || numerator.length > 4096 || denominator.length > 4096 || !/^(0|[1-9][0-9]*)$/.test(numerator) || !/^[1-9][0-9]*$/.test(denominator) || BigInt(numerator) > BigInt(denominator)) return "unavailable";
  return `${numerator}/${denominator}`;
}

export default function PaletteCompatibilityExplanation({ display }: { display: PaletteCompatibilityDisplay }) {
  return <section aria-label="Recorded palette compatibility" className="min-w-0 space-y-3 rounded-xl bg-slate-50 p-4 text-sm [overflow-wrap:anywhere]">
    <h3 className="font-semibold">Recorded palette compatibility</h3>
    <p>Exact ranking total: {exact(display.total)}. This ranks eligible outfits; it is not confidence or a validated fashion rating.</p>
    <p>Compatibility contribution: {exact(display.palette.contribution)}. Recorded evidence: {display.palette.state}.</p>
    {display.compatibility_basis === "NoPairReference" ? <p>A single dress has no garment-pair comparisons. Its compatibility contribution is the existing one-half reference.</p> : <>
      <p>Possible-value range: {exact(display.palette.lower)} to {exact(display.palette.upper)}. This is not a confidence interval.</p>
      {display.palette.state === "Unknown" && <p>Some palette or style information is unresolved. The midpoint is used as a disclosed ranking convention; missing evidence was not confirmed as compatible.</p>}
      <p>{display.palette.known} of {display.palette.possible} pair-rule observations have exact point values.</p>
    </>}
    {display.source_limitations.map(value => <p key={value}>{value}</p>)}
    {display.objective && <p>{display.objective.explanation} {display.objective.limitations}</p>}
    {display.coverage && <p>{display.coverage.global_optimum_certified ? "This outfit ranks first under the captured facts and conventions." : "Other eligible outfits have unresolved contextual evidence and could rank higher."}</p>}
    {display.preference_ledger && <section aria-label="Captured wearer preferences" className="space-y-2">
      <h4 className="font-semibold">Your captured preferences</h4>
      {!display.preference_ledger.families.length && <p>No preferences were configured for this request.</p>}
      <ul>{display.preference_ledger.families.map(family => <li key={family.family}>{family.family.replaceAll("_", " ")}: {family.axes.some(axis => axis.mask) ? "Rewards already implied by the request were suppressed with the original denominator retained." : "Likes and avoids remain soft ranking preferences."}</li>)}</ul>
    </section>}
    {display.refinement && <section aria-label="Recommendation sequence" className="space-y-2">
      <h4 className="font-semibold">{display.refinement.ordinal ? `Alternative ${display.refinement.ordinal}` : "Initial option"}</h4>
      <p>Request exclusions: {display.refinement.excluded_categories.map(c => c.replaceAll("_", " ")).join(", ") || "none"}. These are not saved preferences.</p>
      <p>Original style-alignment floor: {exact(display.refinement.root_R)}. Retries and alternatives retain the same compatibility mode and captured scope.</p>
      {display.refinement.ordinal > 0 && <p>{display.refinement.total_vs_root === "lower" ? "This alternative has a lower total than the initial option." : "This alternative has the same total as the initial option."} Changing only outerwear is not another base outfit.</p>}
      {display.refinement.limit_reached && <p>The ten-result limit has been reached. This does not establish exhaustion.</p>}
    </section>}
    <details><summary className="min-h-11 cursor-pointer py-3 font-semibold">Stored R C P score details</summary>
      <ul>{display.components.map(component => <li key={component.name}>{component.name}: {exact(component.contribution)}; weight {exact(component.weight)}; weighted term {exact(component.weighted)}.</li>)}</ul>
    </details>
  </section>;
}
