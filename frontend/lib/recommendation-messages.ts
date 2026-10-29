import { ApiError } from "./api";
export function relativeCoverageMessage(certified: boolean, unresolved: number) {
  return certified ? "This outfit ranks first under the recorded facts and ranking conventions."
    : `Best among outfits with computable style alignment. ${unresolved} other eligible outfit${unresolved === 1 ? " has" : "s have"} missing relative evidence and could rank higher.`;
}
const messages: Record<string,string> = {
  RefinementExhausted: "No other base outfit remains at the original style-alignment floor under these conditions.",
  RefinementInsufficientEvidence: "Other eligible base outfits have missing style-alignment evidence. No qualifying alternative can be established; this is not exhaustion.",
  RefinementLimitReached: "This sequence has reached its ten-result safety limit. This does not mean every qualifying outfit was exhausted. Start a fresh recommendation if needed.",
  RefinementScopeChanged: "Wardrobe, preferences or ranking conditions changed. Start a fresh recommendation.",
  RefinementConflict: "A required garment category is also excluded. Change the optional exclusions or start a fresh request.",
  RefinementUnavailable: "Optional refinement requires an enabled ordinary relative recommendation. Your original request was not replaced or relaxed.",
  RefinementNotFound: "The parent recommendation was not found or is not accessible.",
  NoEligibleGarments: "No current, available garments can be used. Add garments or resolve incomplete processing in your wardrobe.",
  InsufficientStructure: "Your wardrobe cannot yet form a complete supported outfit.", NoStructuralCandidates: "No complete supported outfit could be formed.",
  NoMatchingCandidates: "No outfit meets all required conditions.", InsufficientEvidence: "Garment information is insufficient to establish all required conditions.",
  UnsupportedRequest: "This request contains unsupported or unrepresentable conditions. Start a new chat with one supported outfit request.",
  PolicyUnavailable: "Matching rules for one or more requested conditions are not available. The conditions were not ignored.",
  WardrobeChanged: "Your wardrobe changed while the outfit was being processed. No stale result was saved.",
  PersistenceFailure: "The result could not be confirmed as saved. Retry the same interaction to recover any committed result.",
  ProcessingFailure: "Recommendation processing could not finish. No partial outfit is shown.", ProcessingError: "The request could not be interpreted.",
  InvalidScoringInput: "The outfit could not be scored safely. No partial recommendation is shown.",
  Interrupted: "Processing was interrupted. No incomplete result is shown.", IntegrationDisabled: "This recommendation feature is disabled on the backend. No placeholder result will be used.",
  InvalidInput: "Enter one nonempty outfit request of up to 500 characters.", IdempotencyConflict: "This interaction key belongs to different request text. Start a new chat.",
  InvalidPreferenceData: "Stored preferences cannot be used safely. Review your preferences before starting a new chat.", ProfileUnavailable: "The approved scoring profile is unavailable.",
  NotFound: "This completed chat was not found or is not accessible.", HistoryUnavailable: "Chat history is temporarily unavailable.",
};
const contextualMessages = new Set([
  "This wedding role or dress code is not supported. Start a new chat with a supported guest request.",
  "No outfit passed the wedding rules. Review the garment style evidence or your explicit suitability choices before starting a new chat.",
  "No complete eligible outfit is available for this wedding request. Check your wardrobe before starting a new chat.",
]);
const contextReasons: Record<string, string> = {
  context_clarification_required: "Please specify whether this is an ordinary office, academic study, social meetup, or city sightseeing request. The missing purpose was not guessed. Submit a fresh complete request.",
  capability_not_enabled: "This situation was understood, but its outfit policy is not enabled. No generic outfit was substituted.",
  required_context_missing: "This situation was understood, but needs more context before a supported outfit policy can be used. No generic outfit was substituted. Edit your request in a new chat.",
  unsupported_role: "This role is understood, but no approved outfit policy is available for it.",
  unsupported_dress_code: "This dress code is understood, but its outfit requirements are not supported. Check the invitation before starting a new chat.",
  unsupported_constraint: "One or more contextual conditions cannot yet be evaluated. They were not ignored.",
  conflicting_context: "The contextual conditions conflict. Edit your request in a new chat.",
  required_attribute_unknown: "No reliable outfit could be established. Review missing or stale garment style evidence; individual occasion tags are optional.",
  requirement_failed: "No outfit passed all required conditions. Explicit suitability restrictions were preserved.",
  wardrobe_incomplete: "No complete eligible outfit is available for this situation. Check your wardrobe before starting a new chat.",
};
export function outcomeMessage(status: string, contextual?: unknown, contextReason?: unknown) {
  if (status.startsWith("Refinement")) return messages[status] ?? "This refinement could not be completed.";
  if (typeof contextReason === "string" && contextReasons[contextReason]) return contextReasons[contextReason];
  return typeof contextual === "string" && contextualMessages.has(contextual) ? contextual : messages[status] ?? `The request could not be completed safely (${status}).`;
}
export function contextEvidenceMessage(version: unknown, status: unknown) {
  if ((version === "general-context-explanation-1.4.0" || version === "general-context-explanation-2.0.0") && status === "InsufficientEvidence") return "No complete outfit has enough usable saved information for this request. Ordinary suggestions can use saved casual or smart-casual style without a separate review. Check missing, unsupported or inconsistent styles and any requested dress code. Correct uncovered styles should not be relabelled. Attribute corrections and occasion restrictions are optional; no per-garment review is required for this policy.";
  if (version === "general-context-explanation-1.3.0" && status === "InsufficientEvidence") return "Current evidence does not establish a complete everyday outfit. In Wardrobe Edit, explicitly select and save a supported style to confirm it once. Missing or stale evidence may need correction; correct uncovered styles should not be relabelled. Collar, tailoring and condition observations are not required for this ordinary appearance policy.";
  if (version === "general-context-explanation-1.2.0" && status === "InsufficientEvidence") return "The reviewed evidence does not establish a complete outfit for this appearance policy. Interview suggestions require construction details and dated condition observations as well as reviewed style. Correct style labels should not be changed just to obtain a result.";
  return version === "general-context-explanation-1.1.0" && status === "InsufficientEvidence"
    ? "Current garment evidence does not establish a suitable complete outfit for this policy. Missing or stale attributes may need review; an uncovered style can be correct and should not be relabelled just to obtain a result."
    : undefined;
}
export function errorMessage(error: unknown) {
  const contextual = error instanceof ApiError && error.payload && typeof error.payload === "object" && "contextual_message" in error.payload ? error.payload.contextual_message : undefined;
  const contextReason = error instanceof ApiError && error.payload && typeof error.payload === "object" && "context_reason" in error.payload ? error.payload.context_reason : undefined;
  return error instanceof ApiError && error.outcome ? outcomeMessage(error.outcome, contextual, contextReason) : error instanceof Error ? error.message : "The service could not be reached.";
}
