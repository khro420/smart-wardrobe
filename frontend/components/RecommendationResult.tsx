"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import ProtectedImage from "@/components/ProtectedImage";
import CompatibilityExplanation from "./CompatibilityExplanation";
import { relativeCoverageMessage } from "@/lib/recommendation-messages";
import { getRecommendationSavedOutfit, saveRecommendationAsOutfit, type ContextSummary, type IntegratedRecommendation } from "@/lib/api";

type Props = { recommendation: IntegratedRecommendation; historical?: boolean; historicalActions?: boolean; onSaved?: () => Promise<void> };

function exactRatioText(value: unknown): string | null {
  if (!value || typeof value !== "object" || !("numerator" in value) || !("denominator" in value)) return null;
  const { numerator, denominator } = value;
  if (typeof numerator !== "string" || typeof denominator !== "string" || numerator.length > 4096 || denominator.length > 4096 || !/^(0|[1-9][0-9]*)$/.test(numerator) || !/^[1-9][0-9]*$/.test(denominator)) return null;
  if (BigInt(numerator) > BigInt(denominator)) return null;
  return `${numerator}/${denominator}`;
}

function RelativeRankingDetails({ recommendation }: { recommendation: IntegratedRecommendation }) {
  const view = recommendation.scoring_display;
  if (!view || (view.version !== "assistant-scoring-display-2.0.0" && view.version !== "assistant-scoring-display-2.1.0" && view.version !== "assistant-scoring-display-2.2.0")) return null;
  if (view.kind === "Unavailable") return <p role="status">Stored ranking details are unavailable. No score was recomputed.</p>;
  const total = exactRatioText(view.total);
  if (!total || view.components.length !== 3 || view.components.some(c => !exactRatioText(c.contribution) || !exactRatioText(c.weight) || !exactRatioText(c.weighted) || c.raw_value !== null && !exactRatioText(c.raw_value))) return <p role="status">Exact stored ranking details are unavailable. No rounded score is substituted.</p>;
  const fallback = view.selection_mode === "baseline_disclosed_v1";
  return <section aria-label="Context relevance ranking" className="min-w-0 space-y-3 rounded-xl bg-slate-50 p-3 text-sm [overflow-wrap:anywhere]">
    <div aria-label="Stored ranking score"><p className="font-semibold">Ranking score: {total}</p><p>This is a ranking fraction, not confidence or independently validated fashion quality.</p></div>
    {fallback ? <p role="status" className="font-semibold">Baseline fallback: contextual appearance gates applied; differentiated contextual relevance was not established. {view.fallback_reason === "objective_unavailable" ? "No applicable relative objective was available." : "No eligible outfit had computable relative style alignment."}</p> : <p className="font-semibold">{view.refinement?.ordinal ? (view.coverage.global_optimum_certified ? "Highest-ranked remaining permitted base outfit under the captured facts and original style-alignment floor." : "Best remaining permitted outfit with computable style alignment. Other unseen eligible outfits have missing relative evidence and could rank higher.") : relativeCoverageMessage(view.coverage.global_optimum_certified, view.coverage.unresolved_candidates)}</p>}
    {view.refinement && <section aria-label="Recommendation sequence" className="space-y-2">
      <h4 className="font-semibold">{view.refinement.ordinal === 0 ? "Initial option" : `Alternative ${view.refinement.ordinal} ? option ${view.refinement.ordinal + 1} in this sequence`}</h4>
      <p>Hard exclusions for this request: {view.refinement.excluded_categories.map(c => c.replaceAll("_", " ")).join(", ") || "none"}. These are not saved preferences.</p>
      <p>Original style-alignment floor: {exactRatioText(view.refinement.root_R)}. Initial total: {exactRatioText(view.refinement.root_total)}. Current total: {total}.</p>
      {view.refinement.ordinal > 0 && <p>{view.refinement.total_vs_root === "lower" ? "This alternative has a lower total than the initial option." : "This alternative has the same total as the initial option."} Recorded-style alignment remains at or above the original floor. Changing only outerwear does not count as another base outfit.</p>}
      {view.refinement.limit_reached && <p>The ten-result safety limit has been reached; this is not a claim that the pool is exhausted.</p>}
      <p>Already seen candidates: {view.coverage.already_seen}; known points below the floor: {view.coverage.below_floor_points}; unresolved candidates below the floor: {view.coverage.unresolved_below_floor}.</p>
    </section>}
    {view.objective && <><p>{view.objective.explanation}</p><p>{view.objective.authority === "prototype_convention" ? "Unvalidated prototype appearance convention" : "Your explicit style objective"}: {view.objective.target}.</p><p>{view.objective.limitations}</p></>}
    {!fallback && view.components[0].contribution.numerator === "0" && <p>The recorded base styles do not match this appearance goal. It is a soft goal; the selected outfit still passed the mandatory requirements.</p>}
    <dl aria-label="Full R C P breakdown" className="min-w-0 space-y-2">
      {view.components.map(component => <div key={component.name} className="min-w-0">
        <dt className="font-semibold">{component.name === "R" ? fallback ? "R — legacy request match" : "R — base style alignment" : component.name === "C" ? "C — compatibility" : "P — independent preferences"}</dt>
        <dd>Recorded state: {component.state}. Raw value: {component.raw_value === null ? "not measured / unavailable" : exactRatioText(component.raw_value)}. Contribution: {exactRatioText(component.contribution)}; weight: {exactRatioText(component.weight)}; weighted term: {exactRatioText(component.weighted)}.</dd>
      </div>)}
    </dl>
    <p>Compatibility basis: {view.compatibility_basis}. {view.compatibility_basis === "NoPairReference" ? "The single-piece contribution is a no-pair reference, not a measured garment relationship." : view.compatibility_basis !== "Computed" ? "Missing pair evidence uses the existing midpoint convention; this is not a confidence interval." : "Colour and style pair rules do not establish event appropriateness."}</p>
    {view.preferences.some(p => p.suppressed) && <p>Exactly duplicated style preferences were suppressed for relative ranking; the original positive-weight denominator was retained. {fallback && "The baseline uses the original unmasked preferences."}</p>}
    <p>Eligible outfits: {view.coverage.hard_passed}; computable alignment: {view.coverage.point_candidates}; unresolved relative evidence: {view.coverage.unresolved_candidates}.</p>
    {view.numeric_ties > 1 && <p>{view.numeric_ties} outfits tied numerically. A deterministic garment key selected this result; the tie is not evidence of greater contextual appropriateness.</p>}
    <ul>{view.selected_members.map(member => <li key={member.garment_id}>{recommendation.items.find(item => item.garment_id === member.garment_id)?.name ?? "Recorded garment"}: saved style {member.styles.join(", ") || "unknown"}; origin {member.origin}; review state {member.review_state}. {member.role === "outerwear" ? "Outerwear passes the hard rules but does not contribute directly to base-style R." : "Recorded-label alignment remains provisional."}</li>)}</ul>
    <details><summary className="cursor-pointer underline">Stored ranking policy</summary><p>Scoring profile: {view.profile_name}. Policy: {view.policy_version}. Selection mode: {view.selection_mode}.</p></details>
  </section>;
}

function RankingScore({ metadata }: { metadata: unknown }) {
  if (!metadata || typeof metadata !== "object" || !("profile_name" in metadata) || metadata.profile_name !== "experimental_compatibility_decision_v1" || !("total" in metadata)) return null;
  const total = metadata.total;
  if (!total || typeof total !== "object" || !("numerator" in total) || !("denominator" in total)) return null;
  const { numerator, denominator } = total;
  if (typeof numerator !== "number" || typeof denominator !== "number" || !Number.isSafeInteger(numerator) || !Number.isSafeInteger(denominator) || numerator < 0 || denominator <= 0 || numerator > denominator) return null;
  return <div className="min-w-0 text-sm [overflow-wrap:anywhere]" aria-label="Stored ranking score"><p className="font-semibold">Ranking score: {numerator}/{denominator}</p><p>This score ranks eligible outfits; it is not a confidence or fashion-quality rating.</p></div>;
}

function GeneralContextExplanation({ recommendation }: { recommendation: IntegratedRecommendation }) {
  const raw = recommendation.provenance?.general_context;
  if (!raw || typeof raw !== "object" || !("version" in raw) || !["general-context-explanation-1.0.0", "general-context-explanation-1.1.0", "general-context-explanation-1.2.0", "general-context-explanation-1.3.0", "general-context-explanation-1.4.0", "general-context-explanation-2.0.0"].includes(String(raw.version))) return null;
  const context = raw as ContextSummary;
  const social = context.version !== "general-context-explanation-1.0.0";
  return <section aria-label="Context suggestion basis" className="min-w-0 space-y-2 rounded-xl bg-slate-50 p-3 text-sm [overflow-wrap:anywhere]">
    <p className="font-semibold">Understood situation: {context.label}.</p>
    {context.facets && context.facets.length > 0 && <p>Also understood: {context.facets.map(f => f.replaceAll(":", " — ")).join(", ")}. Both admitted context requirements apply; one appearance goal is scored.</p>}
    {context.negative_scope && <p>Applicable broad restriction: {context.negative_scope}. Broad permission does not supply missing child-context style evidence.</p>}
    {context.scope_note && <p>{context.scope_note}</p>}
    {context.role && <p>Stated role: {context.role}.</p>}
    {context.parent_negative && <p>Applicable negative scope: {context.parent_negative}. Broad permission does not establish this situation’s appearance evidence.</p>}
    <p>{context.dress_code ? `Requested dress code: ${context.dress_code.replaceAll("_", " ")}.` : social ? "Dress code unspecified; no dress code was inferred." : "Dress code unspecified. Check the invitation."}</p>
    {context.formality && <p>Requested formality: {context.formality.replaceAll("_", " ")}.</p>}
    {context.assumptions.map(text => <p key={text}>{text}</p>)}
    {social && context.venue && <p>Stated venue: {context.venue}. No venue dress code has been established.</p>}
    {social && context.companions && context.companions.length > 0 && <p>Stated companions: {context.companions.join(", ")}. This does not determine the dress code.</p>}
    {context.temporal.length > 0 && <p>Stated time: {context.temporal.join(", ")}. Current wardrobe used; weather and future availability are not inferred.</p>}
    <ul>{context.members?.map(member => <li key={member.garment_id}>{recommendation.items.find(item => item.garment_id === member.garment_id)?.name ?? "Recorded garment"}: {member.conditions.map(condition => `${condition.field}: ${["explicit_allow", "explicit_declaration"].includes(condition.basis) ? "your explicit suitability choice" : condition.basis === "saved_attribute_provisional" ? `provisional inference from saved, unreviewed style (origin: ${member.saved_attribute_evidence?.origin ?? "unknown"})` : "inferred from reviewed style attributes"}`).join("; ")}.</li>)}</ul>
    {context.members?.filter(member => member.appearance_observations).map(member => <div key={member.garment_id} className="min-w-0 space-y-1">
      <p>{recommendation.items.find(item => item.garment_id === member.garment_id)?.name ?? "Recorded garment"}: additional owner-reviewed appearance observations.</p>
      <p>{member.appearance_observations!.features.map(([field, value]) => `${field.replaceAll("_", " ")}: ${value === null ? "unknown" : value ? "yes" : "no"}`).join("; ")}.</p>
      <p>Dated condition observation: {member.appearance_observations!.condition?.replaceAll("_", " ") ?? "unknown"}; recorded {member.appearance_observations!.reviewed_at ?? "unknown"}. Check current physical condition and fit before wearing.</p>
    </div>)}
    {(context.version === "general-context-explanation-1.4.0" || context.version === "general-context-explanation-2.0.0") && <p>Saved labels may be unreviewed. Source or storage timestamps are not owner-review times; model-reported information is not independently verified. No separate style review is required for this ordinary policy.</p>}
    <p>{social ? context.limits_note : "This is a suggestion based on recorded evidence. Invitation details, shoes and accessories are not established by these garment records."}</p>
  </section>;
}

function WeddingExplanation({ recommendation }: { recommendation: IntegratedRecommendation }) {
  const raw = recommendation.provenance?.contextual_wedding;
  if (!raw || typeof raw !== "object" || !("version" in raw) || raw.version !== "wedding-guest-suitability-1.0.0" || !("context" in raw) || !raw.context || typeof raw.context !== "object") return null;
  const context = raw.context;
  const code = "dress_code" in context && typeof context.dress_code === "string" ? context.dress_code.replaceAll("_", " ") : undefined;
  const members = "members" in raw && Array.isArray(raw.members) ? raw.members : [];
  return <section className="min-w-0 space-y-2 rounded-xl bg-slate-50 p-3 text-sm" aria-label="Wedding suggestion basis">
    <p className="font-semibold">Wedding guest suggestion{code ? `; requested dress code: ${code}.` : "; dress code unspecified. Check the invitation."}</p>
    {"assumed_role" in context && context.assumed_role === "guest" && <p>Guest role assumed because you did not specify your role.</p>}
    <ul className="space-y-1">{members.map((member: unknown, index: number) => {
      if (!member || typeof member !== "object" || !("garment_id" in member) || typeof member.garment_id !== "string" || !("conditions" in member) || !Array.isArray(member.conditions)) return null;
      const item = recommendation.items.find(item => item.garment_id === member.garment_id);
      return <li key={index} className="[overflow-wrap:anywhere]">{item?.name ?? "Recorded garment"}: {member.conditions.map((condition: unknown) => {
        if (!condition || typeof condition !== "object" || !("field" in condition) || typeof condition.field !== "string" || !("basis" in condition)) return "";
        return `${condition.field}: ${condition.basis === "explicit_allow" ? "your explicit suitability choice" : "inferred from reviewed style attributes"}`;
      }).filter(Boolean).join("; ")}.</li>;
    })}</ul>
    <p>This is a suggestion based on the recorded evidence. Invitation details, shoes and accessories are not established by these garment records.</p>
  </section>;
}

export default function RecommendationResult(props: Props) {
  return <RecommendationResultContent key={`${props.recommendation.id}:${props.historicalActions === true}`} {...props} />;
}

function RecommendationResultContent({ recommendation, historical = false, historicalActions = false, onSaved }: Props) {
  const actionsEnabled = !historical || historicalActions;
  const [saved, setSaved] = useState(!historicalActions && recommendation.status === "saved");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [savedStatus, setSavedStatus] = useState<"loading" | "ready" | "error">("loading");
  const [checkAttempt, setCheckAttempt] = useState(0);
  const [feedback, setFeedback] = useState("");
  const mounted = useRef(false);
  const saveLock = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => {
    if (!actionsEnabled) return;
    let active = true;
    void getRecommendationSavedOutfit(recommendation.id).then(result => {
      if (active) {
        setSaved(result.saved || (!historicalActions && recommendation.status === "saved"));
        setSavedStatus("ready");
        if (result.saved) setFeedback("Already saved as an independent outfit.");
      }
    }).catch(cause => {
      if (active) {
        setSavedStatus("error");
        setError(cause instanceof Error ? cause.message : "Could not check saved outfit status.");
      }
    });
    return () => { active = false; };
  }, [actionsEnabled, historicalActions, recommendation.id, recommendation.status, checkAttempt]);
  const eligible = recommendation.items.length > 0 && recommendation.items.every(item => item.currently_eligible === true);
  const outerwear = recommendation.items.some(item => item.garment_role === "outerwear" || item.category === "short_sleeve_outwear" || item.category === "long_sleeve_outwear");
  const save = async () => {
    if (saveLock.current || saved || !actionsEnabled || !eligible || savedStatus !== "ready") return;
    saveLock.current = true;
    setError("");
    setSaving(true);
    try {
      await saveRecommendationAsOutfit(recommendation.id, "Recommended outfit");
      if (!mounted.current) return;
      setSaved(true);
      setFeedback("Saved as an independent outfit. The original recommendation is unchanged.");
      try { await onSaved?.(); }
      catch { if (mounted.current) setError("Outfit saved, but the outfit list could not be refreshed. Open your wardrobe to view it."); }
    }
    catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : "Could not save outfit."); }
    finally { saveLock.current = false; if (mounted.current) setSaving(false); }
  };
  return <article className="min-w-0 space-y-4 rounded-2xl border border-slate-200 bg-white p-5" data-testid="recommendation-result">
    <h3 className="text-lg font-semibold">{historical ? "Saved recommendation · read-only" : "Your outfit recommendation"}</h3>
    {historical && <p className="text-sm text-slate-600">This is the original result. Current availability does not establish that it still matches the original request.</p>}
    {!eligible && <p role="status" className="text-sm text-amber-800">One or more recorded garments are no longer eligible in your current wardrobe.</p>}
    <div className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">{[...recommendation.items].sort((a,b) => a.item_order-b.item_order).map(item => <div key={item.garment_id} className="min-w-0 rounded-xl border border-slate-200 p-3">
      {item.preferred_media_id ? <ProtectedImage mediaId={item.preferred_media_id} alt={item.name ?? "Recorded garment"} className="h-48 w-full rounded-lg object-contain" /> : <div className="flex h-48 items-center justify-center rounded-lg bg-slate-100 text-sm text-slate-500">Historical image unavailable</div>}
      <p className="mt-3 font-semibold [overflow-wrap:anywhere]">{item.name ?? "Historical garment details unavailable"}</p><p className="text-sm text-slate-600">{item.item_order}. {item.garment_role.replaceAll("_", " ")}{item.category ? ` · ${item.category.replaceAll("_", " ")}` : ""}</p>
      {!item.currently_eligible && <p className="text-sm text-amber-800">Unavailable for current use</p>}
    </div>)}</div>
    {(recommendation.scoring_display?.version === "assistant-scoring-display-2.0.0" || recommendation.scoring_display?.version === "assistant-scoring-display-2.1.0" || recommendation.scoring_display?.version === "assistant-scoring-display-2.2.0") ? <RelativeRankingDetails recommendation={recommendation} /> : <RankingScore metadata={recommendation.score_metadata} />}
    <WeddingExplanation recommendation={recommendation} />
    <GeneralContextExplanation recommendation={recommendation} />
    {recommendation.scoring_display?.version !== "assistant-scoring-display-2.0.0" && recommendation.scoring_display?.version !== "assistant-scoring-display-2.1.0" && recommendation.scoring_display?.version !== "assistant-scoring-display-2.2.0" && <CompatibilityExplanation recommendation={recommendation} />}
    {outerwear && <p className="text-sm text-slate-600">All outfit garments are shown. Visualisation is unavailable for outfits containing outerwear.</p>}
    {actionsEnabled && savedStatus === "loading" && <p role="status" className="text-sm text-slate-600">Checking saved outfit status…</p>}
    {actionsEnabled && feedback && <p role="status" className="text-sm text-emerald-800">{feedback}</p>}
    {historicalActions && recommendation.status === "saved" && !saved && savedStatus === "ready" && <p className="text-sm text-slate-600">This older recommendation was marked saved. Its original outfit may only be available through your wardrobe.</p>}
    {actionsEnabled && eligible && <div className="flex flex-wrap gap-3"><button disabled={saving || saved || savedStatus !== "ready"} onClick={() => void save()} className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50">{saving ? "Saving…" : saved ? "Saved as outfit" : "Save as outfit"}</button>{!outerwear && <Link href={`/try-on?recommendation=${encodeURIComponent(recommendation.id)}`} className="inline-flex min-h-11 items-center rounded-xl bg-[#6d335b] px-4 text-sm font-semibold text-white">Visualise outfit</Link>}</div>}
    {actionsEnabled && savedStatus === "error" && <button type="button" onClick={() => { setError(""); setSavedStatus("loading"); setCheckAttempt(value => value + 1); }} className="min-h-11 text-sm underline">Retry saved status</button>}
    {historical && <Link href="/wardrobe" className="inline-flex min-h-11 items-center text-sm font-semibold underline">Open current wardrobe</Link>}
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
  </article>;
}
