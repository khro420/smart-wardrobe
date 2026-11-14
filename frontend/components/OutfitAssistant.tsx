"use client";
import { useWearerCategoryEligibility } from "@/lib/wearer-category-eligibility";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getCompletedChat, createRecommendation, getRecommendationCapabilities, type RefinementCategory, type RefinementAction, type ContextSummary, type RecommendationCapabilities, type IntegratedRecommendation } from "@/lib/api";
import { readAssistantDraft, writeAssistantDraft, singleFlight, sessionOwner, type AssistantDraft } from "@/lib/recommendation-session";
import { contextEvidenceMessage, errorMessage, outcomeMessage } from "@/lib/recommendation-messages";
import { captureWearer } from "@/lib/wearer-selection";
import RecommendationResult from "./RecommendationResult";
import AttributeRequestControls from "./AttributeRequestControls";
import { CapturedAttributeRequirements } from "./AttributeRequirements";
import { attributeDraftVersion, copyAttributeConditions, storedTypedAttributes, codePointCount, stableAttributeText, type AttributeConditions } from "@/lib/attribute-request";

async function restoreChat(chatId: string, wearerProfileId: string | undefined) {
  try { return await getCompletedChat(chatId, {}, wearerProfileId); }
  catch (cause) {
    if (!(cause instanceof ApiError) || cause.status !== 409 || !wearerProfileId) throw cause;
    return getCompletedChat(chatId, { view: "historical", wearer_profile_id: wearerProfileId }, wearerProfileId);
  }
}

export default function OutfitAssistant() {
  const categoryPolicy = useWearerCategoryEligibility();
  const [draft,setDraft] = useState<AssistantDraft>();
  const current = useRef<AssistantDraft | undefined>(undefined);
  const busy = useRef(false);
  const alive = useRef(false);
  const [pending,setPending] = useState(false);
  const [result,setResult] = useState<IntegratedRecommendation>();
  const [continuationEnded,setContinuationEnded] = useState(false);
  const [historical,setHistorical] = useState(false);
  const [message,setMessage] = useState("");
  const [retryable,setRetryable] = useState(false);
  const [capabilities, setCapabilities] = useState<RecommendationCapabilities>();
  const [contextSummary, setContextSummary] = useState<ContextSummary>();
  const [editingExclusions,setEditingExclusions] = useState(false);
  const [excludedDraft,setExcludedDraft] = useState<RefinementCategory[]>([]);
  const outcomeRegion = useRef<HTMLDivElement>(null);
  const focusOutcomeKey = useRef<string | undefined>(undefined);
  const remember = (value: AssistantDraft) => { current.current = value; writeAssistantDraft(value); setDraft(value); };
  const send = useCallback(async (value: AssistantDraft, focusOutcome = false, recovery = false) => {
    if (busy.current || !value.submitted || !value.wearerProfileId) return;
    const owner = sessionOwner();
    if (focusOutcome) focusOutcomeKey.current = value.key;
    busy.current = true; setPending(true); setMessage(""); setRetryable(false); setContextSummary(undefined);
    try {
      const actionKey = stableAttributeText({ text: value.submitted, refinement: value.refinement ?? null, attributes: value.attributeConditions ?? null, preferenceProfile: value.preferenceProfile ?? null, compatibilityProfile: value.compatibilityProfile ?? null });
      const response = await singleFlight(`assistant:${value.key}:${actionKey}`, () => createRecommendation(value.submitted!, value.key, value.refinement, value.wearerProfileId, recovery, value.attributeConditions, value.preferenceProfile, value.compatibilityProfile), value.wearerProfileId);
      if (!alive.current || current.current?.key !== value.key || sessionOwner() !== owner) return;
      if (response.outcome === "Selected" && response.complete && response.recommendation?.chat_id) {
        const completed = { ...value, chatId: response.recommendation.chat_id };
        current.current = completed; writeAssistantDraft(completed); setDraft(completed);
        setContinuationEnded(false); setResult(response.recommendation); setHistorical(response.replayed === true);
        if (response.replayed && value.refinement?.kind === "alternative") setMessage("This alternative was already generated; continue from it.");
      } else { if (["GarmentRefinementExhausted", "GarmentRefinementInsufficientEvidence", "RefinementLimitReached"].includes(response.outcome ?? "")) setContinuationEnded(true); setContextSummary(response.context_summary); setMessage(response.outcome?.startsWith("GarmentRefinement") ? outcomeMessage(response.outcome, response.contextual_message, response.context_reason) : contextEvidenceMessage(response.context_summary?.version, response.outcome, response.context_reason) ?? (response.outcome ? outcomeMessage(response.outcome, response.contextual_message, response.context_reason) : "The integrated Assistant is unavailable. No legacy result is displayed.")); }
    } catch (cause) {
      if (alive.current && current.current?.key === value.key && sessionOwner() === owner) {
        if (cause instanceof ApiError && cause.payload && typeof cause.payload === "object" && "context_summary" in cause.payload) setContextSummary(cause.payload.context_summary as ContextSummary);
        setMessage(errorMessage(cause)); setRetryable(!(cause instanceof ApiError) || cause.status >= 500);
      }
    } finally { busy.current = false; if (alive.current) setPending(false); }
  },[]);
  useEffect(() => {
    if (!pending && (message || result) && focusOutcomeKey.current === current.current?.key) {
      focusOutcomeKey.current = undefined;
      outcomeRegion.current?.focus({ preventScroll: true });
      outcomeRegion.current?.scrollIntoView({ block: "start" });
    }
  }, [pending, message, result]);
  useEffect(() => {
    alive.current = true;
    let owner = "";
    Promise.resolve().then(async () => {
      if (!alive.current) return;
      const wearer = await captureWearer();
      if (!alive.current) return;
      owner = sessionOwner(wearer.id);
      void getRecommendationCapabilities(wearer.id).then(value => {
        if (alive.current && sessionOwner() === owner) {
          setCapabilities(value);
          const fresh = current.current;
          if (fresh && !fresh.submitted && !fresh.chatId && value.attribute_preferences?.enabled) {
            const captured = {...fresh, preferenceProfile: value.attribute_preferences.profile};
            current.current = captured; writeAssistantDraft(captured); setDraft(captured);
          }
        }
      }).catch(() => { /* The pinned submission returns controlled availability errors. */ });
      const value = readAssistantDraft(wearer.id, wearer.name);
      current.current = value; setDraft(value);
      if (value.chatId) {
        try { const chat = await restoreChat(value.chatId, value.wearerProfileId); if (alive.current && current.current?.key === value.key && sessionOwner() === owner) { setResult(chat.recommendation); setHistorical(true); } }
        catch (cause) { if (alive.current && current.current?.key === value.key) setMessage(errorMessage(cause)); }
      } else if (value.submitted) {
        if (value.previousChatId) {
          setPending(true);
          try { const prior = await restoreChat(value.previousChatId, value.wearerProfileId); if (alive.current && current.current?.key === value.key && sessionOwner() === owner) setResult(prior.recommendation); }
          catch { /* Retry remains authoritative even if the prior card cannot be restored. */ }
        }
        if (!alive.current || current.current?.key !== value.key || sessionOwner() !== owner) return;
        await send(value, false, true);
      }
    }).catch(cause => { if (alive.current) { setMessage(errorMessage(cause)); setDraft({ key: crypto.randomUUID(), text: "" }); } });
    return () => { alive.current = false; };
  },[send]);
  const submit = () => {
    if (!draft || !draft.wearerProfileId || draft.submitted || busy.current || !draft.text.trim() || codePointCount(draft.text) > 500) return;
    const value = { ...draft, submitted: draft.text };
    remember(value); void send(value, true);
  };
  const newChat = () => {
    if (busy.current) return;
    focusOutcomeKey.current = undefined;
    remember({ preferenceProfile: capabilities?.attribute_preferences?.enabled ? capabilities.attribute_preferences.profile : undefined, key: crypto.randomUUID(), text: "", wearerProfileId: draft?.wearerProfileId, wearerName: draft?.wearerName }); setPending(false); setResult(undefined); setMessage(""); setHistorical(false); setRetryable(false); setContextSummary(undefined);
    setContinuationEnded(false); setEditingExclusions(false); setExcludedDraft([]);
  };
  const refinementEnabled = capabilities?.refinement?.version === "recommendation-refinement-capabilities-1.0.0" && capabilities.refinement.available;
  const view = result?.scoring_display;
  const garmentEnabled = capabilities?.garment_continuation?.version === "garment-only-continuation-capabilities-1.0.0" && capabilities.garment_continuation.available;
  const descriptor = result?.garment_continuation?.version === "garment-only-continuation-display-1.0.0" ? result.garment_continuation : view?.kind === "ContextRelevance" && view.version === "assistant-scoring-display-2.2.0" || view?.kind === "AttributePreference" && view.version === "assistant-scoring-display-3.0.0" || view?.kind === "PaletteCompatibility" && view.version === "assistant-scoring-display-4.0.0" ? view.refinement : undefined;
  const openExclusions = () => {
    setExcludedDraft(descriptor?.excluded_categories ?? (draft?.refinement?.kind === "initial" ? draft.refinement.excluded_categories : []));
    setEditingExclusions(true);
  };
  const applyExclusions = () => {
    if (!draft || busy.current || !refinementEnabled) return;
    const action: RefinementAction = { version: "assistant-refinement-request-1.0.0", kind: "initial", excluded_categories: [...excludedDraft].sort() };
    setEditingExclusions(false);
    if (draft.submitted) {
      const text = result?.request_text ?? draft.submitted;
      let attributes: AttributeConditions | undefined;
      try { attributes = result ? storedTypedAttributes(result) : copyAttributeConditions(draft.attributeConditions); }
      catch (cause) { setMessage(errorMessage(cause)); return; }
      const next: AssistantDraft = { compatibilityProfile: draft.compatibilityProfile, preferenceProfile: draft?.preferenceProfile, wearerProfileId: draft?.wearerProfileId, wearerName: draft?.wearerName, key: crypto.randomUUID(), text, submitted: text, refinement: action, previousChatId: result?.chat_id ?? undefined, attributeDraftVersion: attributes ? attributeDraftVersion : undefined, attributeConditions: attributes };
      remember(next); void send(next, true);
    } else remember({ ...draft, refinement: action });
  };
  const another = () => {
    if (!descriptor?.next_action || !result?.request_text || result.wearer_archived || busy.current || continuationEnded || !(result.garment_continuation ? garmentEnabled : refinementEnabled)) return;
    let attributes: AttributeConditions | undefined;
    try { attributes = storedTypedAttributes(result); } catch (cause) { setMessage(errorMessage(cause)); return; }
    const next: AssistantDraft = { wearerProfileId: draft?.wearerProfileId, wearerName: draft?.wearerName, compatibilityProfile: descriptor.next_action.compatibility_profile ?? draft?.compatibilityProfile, preferenceProfile: descriptor.next_action.preference_profile ?? draft?.preferenceProfile, key: descriptor.next_action.submission_key, text: result.request_text, submitted: result.request_text, refinement: descriptor.next_action.refinement, previousChatId: result.chat_id ?? undefined, attributeDraftVersion: attributes ? attributeDraftVersion : undefined, attributeConditions: attributes };
    remember(next); void send(next, true);
  };
  const applyAttributes = (attributes: AttributeConditions | undefined) => {
    if (!draft || busy.current) return;
    const captured = copyAttributeConditions(attributes);
    const fields = { attributeDraftVersion: captured ? attributeDraftVersion : undefined, attributeConditions: captured };
    if (!draft.submitted) { remember({ ...draft, ...fields }); return; }
    const text = result?.request_text ?? draft.submitted;
    const action: RefinementAction | undefined = descriptor ? { version: "assistant-refinement-request-1.0.0", kind: "initial", excluded_categories: [...descriptor.excluded_categories] } : draft.refinement?.kind === "initial" ? draft.refinement : undefined;
    const next: AssistantDraft = { compatibilityProfile: draft.compatibilityProfile, preferenceProfile: draft?.preferenceProfile, wearerProfileId: draft.wearerProfileId, wearerName: draft.wearerName, key: crypto.randomUUID(), text, submitted: text, refinement: action, previousChatId: result?.chat_id ?? undefined, ...fields };
    remember(next); void send(next, true);
  };
  return <section className="space-y-5">
    <div className="flex items-center justify-between gap-4"><div><h1 className="text-3xl font-semibold">Outfit Assistant</h1><p className="mt-2 text-sm text-slate-600">One outfit request per interaction. Required conditions are never silently ignored.</p></div><button onClick={newChat} disabled={!draft || pending || !capabilities} className="min-h-11 shrink-0 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold disabled:opacity-50">New Chat</button></div>
    {draft?.wearerProfileId && <p className="text-sm font-semibold">For {draft.wearerName ?? "selected wearer"}</p>}
    <details open={!draft?.submitted}><summary className="cursor-pointer text-sm font-semibold">Supported situations and examples</summary>
    {capabilities?.context_support && <p className="[overflow-wrap:anywhere] text-sm text-slate-600">{capabilities.context_support.limits}</p>}
    {capabilities?.context_ranking?.version === "context-ranking-capabilities-1.0.0" && <p className="text-sm text-slate-600 [overflow-wrap:anywhere]">Ordinary shopping, class and outing requests use a casual appearance goal; ordinary dates and dinner use smart casual. These are unvalidated prototype defaults, not dress codes. An explicit supported style request overrides the default. No separate garment review or occasion profile is required.</p>}
    {capabilities?.context_support?.situations.some(s => s.id === "everyday.academic_attendance" && s.policy_available) && <p className="text-sm text-slate-600 [overflow-wrap:anywhere]">Try “I’m going to class”, “I have university tomorrow”, “I’m going shopping” or “I’m going out with friends”. Ordinary appearance suggestions still require reliable garment evidence.</p>}
    {capabilities?.context_ranking?.version === "context-ranking-capabilities-1.1.0" && <div className="space-y-2 text-sm [overflow-wrap:anywhere]">
      <p>Appearance suggestions use saved garment attributes and remain provisional, not dress-code certification. An explicit supported style request overrides the default. No separate garment review is required; explicit owner restrictions and unsupported conditions still apply.</p>
      <ul>{capabilities.context_support?.situations.filter(s => s.policy_available && s.example).map(s => <li key={s.id}>{s.label}: {s.example}</li>)}</ul>
      <p>Library/study restrictions can inherit campus Deny; office/meeting restrictions inherit work Deny. Other ordinary subcontexts preserve their stated broad restrictions. Broad permission does not invent missing appearance evidence.</p>
    </div>}
    </details>
    {!draft ? <p role="status">Loading your interaction…</p> : draft.submitted ? <div className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-sm font-semibold text-slate-500">Original request · read-only</h2><p className="mt-2 whitespace-pre-wrap">{draft.submitted}</p></div> : <form onSubmit={event => { event.preventDefault(); submit(); }} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
      <label htmlFor="outfit-request" className="block text-sm font-semibold">What would you like to wear?</label><textarea id="outfit-request" value={draft.text} onChange={event => { if (codePointCount(event.target.value) <= 500) remember({ ...draft, text: event.target.value }); else setMessage("Requests can contain up to 500 characters. Shorten the text before submitting."); }} className="min-h-32 w-full rounded-xl border border-slate-300 p-3" placeholder="Suggest an outfit with vintage style" /><p className="text-right text-xs text-slate-500">{codePointCount(draft.text)}/500</p><button disabled={pending || categoryPolicy.blocked || !draft.wearerProfileId || !draft.text.trim() || codePointCount(draft.text) > 500 || capabilities?.wearer_identity?.version !== "assistant-wearer-intent-1.0.0"} className="min-h-11 rounded-xl bg-[#6d335b] px-4 text-sm font-semibold text-white disabled:opacity-50">Suggest an outfit</button>
    </form>}
    {draft?.preferenceProfile && <p className="text-sm">Saved likes and avoids for this wearer influence ranking softly. Required conditions still apply. <Link href="/profile" className="underline">Edit saved preferences</Link>.</p>}
    <p data-testid="wearer-category-guidance" role="status">{categoryPolicy.text} <Link href="/profile" className="underline">Wearer information</Link></p>
    <CapturedAttributeRequirements value={draft?.attributeConditions} />
    {draft && capabilities?.palette_compatibility?.version === "palette-compatibility-capabilities-1.0.0" && capabilities.palette_compatibility.enabled && <fieldset disabled={pending || !!draft.submitted} className="space-y-2 rounded-xl border border-slate-200 p-4 text-sm">
      <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={draft.compatibilityProfile === "recorded_palette_compatibility_v1"} onChange={event => remember({...draft, compatibilityProfile: event.target.checked ? "recorded_palette_compatibility_v1" : undefined})} />Use recorded palette colours for compatibility</label>
      <p>Your recorded palette fractions extend the prototype colour rule. Uncertain fractions remain unknown. The choice is retained for retries and alternatives.</p>
    </fieldset>}
    {draft && capabilities?.attributes?.enabled && <AttributeRequestControls key={draft.key} capability={capabilities.attributes} allowedCategories={categoryPolicy.data?.enabled ? categoryPolicy.data.allowed_categories : undefined} value={draft.attributeConditions} disabled={pending || categoryPolicy.blocked || !draft.wearerProfileId} submitted={!!draft.submitted} onApply={applyAttributes} />}
    {(refinementEnabled || garmentEnabled && descriptor) && (!draft?.submitted || descriptor) && <section aria-label="Optional recommendation controls" className="min-w-0 space-y-3 rounded-xl border border-slate-200 p-4 text-sm">
      {!editingExclusions ? <button type="button" onClick={openExclusions} disabled={pending} className="min-h-11 font-semibold underline">Exclude garment categories</button> : <fieldset disabled={pending} className="space-y-3">
        <legend className="font-semibold">Exclude garment categories</legend>
        <p>Hard exclusions for this request only. These are not your saved preferences.</p>
        <div className="flex flex-wrap gap-2">{Object.entries((capabilities.refinement?.shortcuts ?? {})).map(([label,values]) => <button type="button" key={label} className="min-h-11 rounded-lg border px-3" onClick={() => setExcludedDraft(current => Array.from(new Set([...current,...values])))}>{label}</button>)}</div>
        <details><summary className="min-h-11 cursor-pointer py-3 font-semibold">All garment categories</summary><div className="grid gap-2 sm:grid-cols-2">{(capabilities.refinement?.categories ?? []).map(category => <label key={category} className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={excludedDraft.includes(category)} onChange={event => setExcludedDraft(current => event.target.checked ? [...current,category] : current.filter(c => c !== category))} />{category.replaceAll("_", " ")}</label>)}</div></details>
        <p>Selected: {excludedDraft.map(c => c.replaceAll("_", " ")).join(", ") || "none"}</p>
        <div className="flex flex-wrap gap-3"><button type="button" onClick={applyExclusions} className="min-h-11 rounded-lg border px-3 font-semibold">Apply exclusions</button><button type="button" onClick={() => setEditingExclusions(false)} className="min-h-11 px-3 underline">Cancel</button><button type="button" onClick={() => setExcludedDraft([])} className="min-h-11 px-3 underline">Clear draft</button></div>
      </fieldset>}
      {!editingExclusions && draft?.refinement?.kind === "initial" && !draft.submitted && <p>Request exclusions: {draft.refinement.excluded_categories.map(c => c.replaceAll("_", " ")).join(", ") || "none"}.</p>}
      {descriptor && <button type="button" disabled={pending || categoryPolicy.blocked || result?.wearer_archived || continuationEnded || !descriptor.next_action || !(result?.garment_continuation ? garmentEnabled : refinementEnabled)} onClick={another} className="min-h-11 rounded-xl bg-[#6d335b] px-4 font-semibold text-white disabled:opacity-50">Suggest another outfit</button>}
    </section>}
    {pending && <p role="status">Interpreting your request and checking complete outfits…</p>}
    {(message || result) && <div ref={outcomeRegion} tabIndex={-1} role="region" aria-label="Recommendation outcome" className="min-w-0 scroll-mt-24 space-y-3 focus:outline-none">
      {message && <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><h2 className="mb-2 text-lg font-semibold">{retryable ? "Request could not be completed" : result ? "Recommendation update" : "No outfit generated"}</h2><p>{message}</p><Link href="/wardrobe" className="mt-2 inline-flex min-h-11 items-center font-semibold underline">Open wardrobe</Link>{retryable && !pending && draft?.submitted && !draft.chatId && <button onClick={() => void send(draft, true, true)} className="ml-3 min-h-11 font-semibold underline">Retry same request</button>}</div>}
      {result && <RecommendationResult key={result.id} recommendation={result} historical={historical || categoryPolicy.blocked || result.items.some(item => !categoryPolicy.permitsItem(item.garment_id, item.category))} />}
    </div>}
    {contextSummary && ["general-context-explanation-1.0.0", "general-context-explanation-1.1.0", "general-context-explanation-1.2.0", "general-context-explanation-1.3.0", "general-context-explanation-1.4.0", "general-context-explanation-2.0.0"].includes(contextSummary.version) && <section aria-label="Understood situation" className="min-w-0 [overflow-wrap:anywhere] text-sm"><details open className="space-y-2">
      <summary className="cursor-pointer font-semibold">Situation and assumptions</summary>
      <p>Understood situation: {contextSummary.label}.</p>
      {contextSummary.scope_note && <p>{contextSummary.scope_note}</p>}
      {contextSummary.facets && contextSummary.facets.length > 0 && <p>Also understood: {contextSummary.facets.map(f => f.replaceAll(":", " — ")).join(", ")}. Every applicable requirement is retained.</p>}
      {contextSummary.negative_scope && <p>Applicable broad restriction: {contextSummary.negative_scope}. Broad Allow does not establish missing child-context evidence.</p>}
      {contextSummary.role && <p>Stated role: {contextSummary.role}.</p>}
      {contextSummary.missing_context && contextSummary.missing_context.length > 0 && <p>Missing context: {contextSummary.missing_context.join(", ")}. Edit your request in a new chat.</p>}
      {contextSummary.unavailable_conditions.length > 0 && <p>Unavailable conditions: {contextSummary.unavailable_conditions.join("; ")}.</p>}
      {contextSummary.assumptions.map(text => <p key={text}>{text}</p>)}
      {contextSummary.venue && <p>Stated venue: {contextSummary.venue}. No venue dress code has been established.</p>}
      {contextSummary.companions && contextSummary.companions.length > 0 && <p>Stated companions: {contextSummary.companions.join(", ")}.</p>}
      {contextSummary.limits_note && <p>{contextSummary.limits_note}</p>}
      {contextSummary.temporal.length > 0 && <p>Stated time: {contextSummary.temporal.join(", ")}. Current wardrobe used; weather and future availability are not inferred.</p>}
    </details></section>}

  </section>;
}
