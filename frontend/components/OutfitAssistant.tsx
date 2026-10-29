"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getCompletedChat, createRecommendation, getRecommendationCapabilities, type RefinementCategory, type RefinementAction, type ContextSummary, type RecommendationCapabilities, type IntegratedRecommendation } from "@/lib/api";
import { readAssistantDraft, writeAssistantDraft, singleFlight, sessionOwner, type AssistantDraft } from "@/lib/recommendation-session";
import { contextEvidenceMessage, errorMessage, outcomeMessage } from "@/lib/recommendation-messages";
import RecommendationResult from "./RecommendationResult";

export default function OutfitAssistant() {
  const [draft,setDraft] = useState<AssistantDraft>();
  const current = useRef<AssistantDraft | undefined>(undefined);
  const busy = useRef(false);
  const alive = useRef(false);
  const [pending,setPending] = useState(false);
  const [result,setResult] = useState<IntegratedRecommendation>();
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
  const send = useCallback(async (value: AssistantDraft, focusOutcome = false) => {
    if (busy.current || !value.submitted) return;
    const owner = sessionOwner();
    if (focusOutcome) focusOutcomeKey.current = value.key;
    busy.current = true; setPending(true); setMessage(""); setRetryable(false); setContextSummary(undefined);
    try {
      const response = await singleFlight(`assistant:${value.key}`, () => createRecommendation(value.submitted!, value.key, value.refinement));
      if (!alive.current || current.current?.key !== value.key || sessionOwner() !== owner) return;
      if (response.outcome === "Selected" && response.complete && response.recommendation?.chat_id) {
        const completed = { ...value, chatId: response.recommendation.chat_id };
        current.current = completed; writeAssistantDraft(completed); setDraft(completed);
        setResult(response.recommendation); setHistorical(response.replayed === true);
        if (response.replayed && value.refinement?.kind === "alternative") setMessage("This alternative was already generated; continue from it.");
      } else { setContextSummary(response.context_summary); setMessage(contextEvidenceMessage(response.context_summary?.version, response.outcome) ?? (response.outcome ? outcomeMessage(response.outcome, response.contextual_message, response.context_reason) : "The integrated Assistant is unavailable. No legacy result is displayed.")); }
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
    void getRecommendationCapabilities().then(value => { if (alive.current) setCapabilities(value); }).catch(() => { /* Submission retains the normal controlled error path. */ });
    const owner = sessionOwner();
    Promise.resolve().then(async () => {
      if (!alive.current) return;
      const value = readAssistantDraft();
      current.current = value; setDraft(value);
      if (value.chatId) {
        try { const chat = await getCompletedChat(value.chatId); if (alive.current && current.current?.key === value.key && sessionOwner() === owner) { setResult(chat.recommendation); setHistorical(true); } }
        catch (cause) { if (alive.current && current.current?.key === value.key) setMessage(errorMessage(cause)); }
      } else if (value.submitted) {
        if (value.previousChatId) {
          setPending(true);
          try { const prior = await getCompletedChat(value.previousChatId); if (alive.current && current.current?.key === value.key && sessionOwner() === owner) setResult(prior.recommendation); }
          catch { /* Retry remains authoritative even if the prior card cannot be restored. */ }
        }
        if (!alive.current || current.current?.key !== value.key || sessionOwner() !== owner) return;
        await send(value);
      }
    });
    return () => { alive.current = false; };
  },[send]);
  const submit = () => {
    if (!draft || draft.submitted || busy.current || !draft.text.trim()) return;
    const value = { ...draft, submitted: draft.text };
    remember(value); void send(value, true);
  };
  const newChat = () => {
    if (busy.current) return;
    focusOutcomeKey.current = undefined;
    remember({ key: crypto.randomUUID(), text: "" }); setPending(false); setResult(undefined); setMessage(""); setHistorical(false); setRetryable(false); setContextSummary(undefined);
    setEditingExclusions(false); setExcludedDraft([]);
  };
  const refinementEnabled = capabilities?.refinement?.version === "recommendation-refinement-capabilities-1.0.0" && capabilities.refinement.available;
  const view = result?.scoring_display;
  const descriptor = view?.version === "assistant-scoring-display-2.2.0" && view.kind === "ContextRelevance" ? view.refinement : undefined;
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
      const next: AssistantDraft = { key: crypto.randomUUID(), text, submitted: text, refinement: action, previousChatId: result?.chat_id ?? undefined };
      remember(next); void send(next, true);
    } else remember({ ...draft, refinement: action });
  };
  const another = () => {
    if (!descriptor?.next_action || !result?.request_text || busy.current || !refinementEnabled) return;
    const next: AssistantDraft = { key: descriptor.next_action.submission_key, text: result.request_text, submitted: result.request_text, refinement: descriptor.next_action.refinement, previousChatId: result.chat_id ?? undefined };
    remember(next); void send(next, true);
  };
  return <section className="space-y-5">
    <div className="flex items-center justify-between gap-4"><div><h1 className="text-3xl font-semibold">Outfit Assistant</h1><p className="mt-2 text-sm text-slate-600">One outfit request per interaction. Required conditions are never silently ignored.</p></div><button onClick={newChat} disabled={!draft || pending} className="min-h-11 shrink-0 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold disabled:opacity-50">New Chat</button></div>
    <details open={!draft?.submitted}><summary className="cursor-pointer text-sm font-semibold">Supported situations and examples</summary>
    {capabilities?.context_support && <p className="[overflow-wrap:anywhere] text-sm text-slate-600">{capabilities.context_support.limits}</p>}
    {capabilities?.context_ranking?.version === "context-ranking-capabilities-1.0.0" && <p className="text-sm text-slate-600 [overflow-wrap:anywhere]">Ordinary shopping, class and outing requests use a casual appearance goal; ordinary dates and dinner use smart casual. These are unvalidated prototype defaults, not dress codes. An explicit supported style request overrides the default. No separate garment review or occasion profile is required.</p>}
    {capabilities?.context_support?.situations.some(s => s.id === "everyday.academic_attendance" && s.policy_available) && <p className="text-sm text-slate-600 [overflow-wrap:anywhere]">Try “I’m going to class”, “I have university tomorrow”, “I’m going shopping” or “I’m going out with friends”. Ordinary appearance suggestions still require reliable garment evidence.</p>}
    {capabilities?.context_ranking?.version === "context-ranking-capabilities-1.1.0" && <div className="space-y-2 text-sm [overflow-wrap:anywhere]">
      <p>Ordinary appearance goals are unvalidated prototype conventions, not dress codes. An explicit supported style request overrides the default. These ordinary policies require no separate garment review or occasion profile. Wedding, presentation and interview evidence remains strict.</p>
      <ul>{capabilities.context_support?.situations.filter(s => s.policy_available && s.example).map(s => <li key={s.id}>{s.label}: {s.example}</li>)}</ul>
      <p>Library/study restrictions can inherit campus Deny; office/meeting restrictions inherit work Deny. Other ordinary subcontexts preserve their stated broad restrictions. Broad permission does not invent missing appearance evidence.</p>
    </div>}
    </details>
    {!draft ? <p role="status">Loading your interaction…</p> : draft.submitted ? <div className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-sm font-semibold text-slate-500">Original request · read-only</h2><p className="mt-2 whitespace-pre-wrap">{draft.submitted}</p></div> : <form onSubmit={event => { event.preventDefault(); submit(); }} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
      <label htmlFor="outfit-request" className="block text-sm font-semibold">What would you like to wear?</label><textarea id="outfit-request" value={draft.text} onChange={event => remember({ ...draft, text: event.target.value })} maxLength={500} className="min-h-32 w-full rounded-xl border border-slate-300 p-3" placeholder="Suggest an outfit with vintage style" /><p className="text-right text-xs text-slate-500">{draft.text.length}/500</p><button disabled={pending || !draft.text.trim()} className="min-h-11 rounded-xl bg-[#6d335b] px-4 text-sm font-semibold text-white disabled:opacity-50">Suggest an outfit</button>
    </form>}
    {refinementEnabled && (!draft?.submitted || descriptor) && <section aria-label="Optional recommendation controls" className="min-w-0 space-y-3 rounded-xl border border-slate-200 p-4 text-sm">
      {!editingExclusions ? <button type="button" onClick={openExclusions} disabled={pending} className="min-h-11 font-semibold underline">Exclude garment categories</button> : <fieldset disabled={pending} className="space-y-3">
        <legend className="font-semibold">Exclude garment categories</legend>
        <p>Hard exclusions for this request only. These are not your saved preferences.</p>
        <div className="flex flex-wrap gap-2">{Object.entries(capabilities.refinement!.shortcuts).map(([label,values]) => <button type="button" key={label} className="min-h-11 rounded-lg border px-3" onClick={() => setExcludedDraft(current => Array.from(new Set([...current,...values])))}>{label}</button>)}</div>
        <details><summary className="min-h-11 cursor-pointer py-3 font-semibold">All garment categories</summary><div className="grid gap-2 sm:grid-cols-2">{capabilities.refinement!.categories.map(category => <label key={category} className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={excludedDraft.includes(category)} onChange={event => setExcludedDraft(current => event.target.checked ? [...current,category] : current.filter(c => c !== category))} />{category.replaceAll("_", " ")}</label>)}</div></details>
        <p>Selected: {excludedDraft.map(c => c.replaceAll("_", " ")).join(", ") || "none"}</p>
        <div className="flex flex-wrap gap-3"><button type="button" onClick={applyExclusions} className="min-h-11 rounded-lg border px-3 font-semibold">Apply exclusions</button><button type="button" onClick={() => setEditingExclusions(false)} className="min-h-11 px-3 underline">Cancel</button><button type="button" onClick={() => setExcludedDraft([])} className="min-h-11 px-3 underline">Clear draft</button></div>
      </fieldset>}
      {!editingExclusions && draft?.refinement?.kind === "initial" && !draft.submitted && <p>Request exclusions: {draft.refinement.excluded_categories.map(c => c.replaceAll("_", " ")).join(", ") || "none"}.</p>}
      {descriptor && <button type="button" disabled={pending || !descriptor.next_action} onClick={another} className="min-h-11 rounded-xl bg-[#6d335b] px-4 font-semibold text-white disabled:opacity-50">Suggest another outfit</button>}
    </section>}
    {pending && <p role="status">Interpreting your request and checking complete outfits…</p>}
    {(message || result) && <div ref={outcomeRegion} tabIndex={-1} role="region" aria-label="Recommendation outcome" className="min-w-0 scroll-mt-24 space-y-3 focus:outline-none">
      {message && <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><h2 className="mb-2 text-lg font-semibold">{retryable ? "Request could not be completed" : result ? "Recommendation update" : "No outfit generated"}</h2><p>{message}</p><Link href="/wardrobe" className="mt-2 inline-flex min-h-11 items-center font-semibold underline">Open wardrobe</Link>{retryable && !pending && draft?.submitted && !draft.chatId && <button onClick={() => void send(draft, true)} className="ml-3 min-h-11 font-semibold underline">Retry same request</button>}</div>}
      {result && <RecommendationResult key={result.id} recommendation={result} historical={historical} />}
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
