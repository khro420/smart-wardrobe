import { ApiError } from "./api";
export function relativeCoverageMessage(certified: boolean, unresolved: number) {
  return certified ? "This outfit ranks first under the recorded facts and ranking conventions."
    : `Best among outfits with computable style alignment. ${unresolved} other eligible outfit${unresolved === 1 ? " has" : "s have"} missing relative evidence and could rank higher.`;
}
const messages: Record<string,string> = {
  SoftProfileUnavailable: "Text preferences support basic P1/C1 only, without context, detailed controls or exclusions. Turn off saved attribute preferences and recorded palette compatibility, then start a new chat. No requirement was dropped.",
  UnsupportedSoftPreference: "Use one supported positive top or bottom wish, such as I'd prefer black trousers. Multiple wishes, material preferences and other modifiers are not supported.",
  AmbiguousSoftBinding: "Name one required top or bottom before preferably, so the preference has a clear garment to refer to.",
  SoftContinuationUnavailable: "Suggest another outfit is unavailable for optional text preferences. Start a new chat; the saved result remains unchanged.",
  wearer_subtype_unresolved: "Some garment types are unconfirmed for this wearer. Review their garment type in your wardrobe before trying again; the remaining pool is not confirmed exhausted.",
  WearerSubtypeNotPermitted: "Blouses are not permitted for the selected male wearer. Choose another wearer or change the requirement. No other top type was substituted.",
  WearerSubtypeUnresolved: "This garment type is not confirmed for the selected wearer. Review its type in your wardrobe before using it.",
  GarmentRefinementExhausted: "No more distinct outfit bases satisfy the original garment requirements and wearer restrictions.",
  GarmentRefinementInsufficientEvidence: "Some remaining garments lack qualified evidence for the original requirements. Review their descriptions before starting a new request. This is not exhaustion.",
  GarmentWordingClarification: "That garment distinction cannot be represented or confirmed. Use a registered garment type and qualified descriptors; replace dark with a named colour. Your requirement was kept.",
  WearerCategoryNotPermitted: "This garment category is not supported for the selected male wearer profile. Choose another wearer or change the request.",
  WearerCategoryPolicyUnconfigured: "Choose Male or Female in the selected wearer information under Profile before starting new work. Other descriptions have no approved category policy yet.",
  WearerCategoryUnresolved: "Review the garment's missing or inconsistent category before using it.",
  WearerEligibilityChanged: "Wearer information or account garment sources changed. Start a fresh request; saved history is retained.",
  PreferenceUnavailable: "Saved attribute preference ranking is unavailable. Your captured request was kept; start a new chat for the basic mode.",
  PreferenceInvalid: "Saved preferences or their stored evidence cannot be read. Review preferences before starting a fresh request.",
  PreferenceCapacityExceeded: "Preference settings or evidence exceed the supported limit. No partial recommendation was saved.",
  AttributeUnavailable: "Detailed garment matching is unavailable. Your requirements were kept.",
  AttributeConflict: "Some garment requirements contradict each other. Edit the requirements in a new request.",
  UnsupportedAttributeValue: "One or more garment values are unsupported. Your requirements were not removed.",
  EncodingLimitExceeded: "These requirements exceed the supported request or evidence size. Shorten the request explicitly before trying again.",
  WardrobeCapacityExceeded: "The eligible shared wardrobe exceeds the 100-garment recommendation limit. No outfit was generated and no garments were removed.",
  WearerSelectionRequired: "Choose the intended wearer before requesting an outfit.",
  WearerArchived: "This wearer is archived. Choose an active wearer for a fresh request.",
  WearerMismatch: "The request wearer and selected wearer disagree. Start a fresh request for the intended wearer.",
  RefinementExhausted: "No other base outfit remains at the original style-alignment floor under these conditions.",
  RefinementInsufficientEvidence: "Other eligible base outfits have missing style-alignment evidence. No qualifying alternative can be established; this is not exhaustion.",
  RefinementLimitReached: "This sequence has reached its ten-result safety limit. This does not mean every qualifying outfit was exhausted. Start a fresh recommendation if needed.",
  RefinementScopeChanged: "Wardrobe, preferences or ranking conditions changed. Start a fresh recommendation.",
  RefinementConflict: "A required garment category is also excluded. Change the optional exclusions or start a fresh request.",
  RefinementUnavailable: "Optional refinement requires an enabled ordinary relative recommendation. Your original request was not replaced or relaxed.",
  RefinementNotFound: "The parent recommendation was not found or is not accessible.",
  NoEligibleGarments: "No current, available garments can be used. Add garments or resolve incomplete processing in your wardrobe.",
  InsufficientStructure: "Your wardrobe cannot yet form a complete supported outfit.", NoStructuralCandidates: "No complete supported outfit could be formed.",
  NoMatchingCandidates: "No complete eligible outfit satisfies all mandatory conditions. Your requirements were kept.", InsufficientEvidence: "Some required garment details cannot be verified from saved information. This does not prove that no outfit matches.",
  UnsupportedRequest: "This request contains unsupported or unrepresentable conditions. Start a new chat with one supported outfit request.",
  PolicyUnavailable: "Matching rules for one or more requested conditions are not available. The conditions were not ignored.",
  WardrobeChanged: "Your wardrobe changed while the outfit was being processed. No stale result was saved.",
  PersistenceFailure: "The result could not be confirmed as saved. Retry the same interaction to recover any committed result.",
  ProcessingFailure: "Recommendation processing could not finish. No partial outfit is shown.", ProcessingError: "The request could not be interpreted.",
  InvalidScoringInput: "The outfit could not be scored safely. No partial recommendation is shown.",
  Interrupted: "Processing was interrupted. No incomplete result is shown.", IntegrationDisabled: "This recommendation feature is disabled on the backend. No placeholder result will be used.",
  InvalidInput: "Enter one nonempty outfit request of up to 500 characters.", IdempotencyConflict: "This interaction key belongs to a different wearer or request intent. Start a new chat.",
  InvalidPreferenceData: "Stored preferences cannot be used safely. Review your preferences before starting a new chat.", ProfileUnavailable: "The approved scoring profile is unavailable.",
  NotFound: "This completed chat was not found or is not accessible.", HistoryUnavailable: "Chat history is temporarily unavailable.",
};
const contextualMessages = new Set([
  "This wedding role or dress code is not supported. Start a new chat with a supported guest request.",
  "No outfit passed the wedding rules. Review the garment style evidence or your explicit suitability choices before starting a new chat.",
  "No complete eligible outfit is available for this wedding request. Check your wardrobe before starting a new chat.",
]);
const contextReasons: Record<string, string> = {
  unsupported_compositional_clause: "Split the request into clear garment requirements and one optional colour/category wish. Every clause must be understood; none was ignored.",
  compositional_literal_scope_unavailable: "Quoted garment names and literal descriptions are outside this opt-in clause grammar. Use the original supported request path for literal matching.",
  unrepresentable_compositional_target: "Use a supported garment and its recorded attributes. This clause cannot be represented safely; no partial outfit request was submitted.",
  compositional_or_jeans_scope_unavailable: "Colour choices with jeans need a separate category-plus-material binding. Use a single supported colour requirement or trousers; no denim requirement was discarded.",
  empty_compositional_clause: "Finish every clause. A trailing comma, and or but does not specify another garment requirement.",
  empty_compositional_target: "Name the garment or condition after the request words; no requirement was inferred.",
  unbound_compositional_instead: "State the excluded garment before instead. This word does not infer a previous outfit or saved request.",
  unmodeled_compositional_modifier: "Describe a supported style or garment attribute explicitly. Relative formality and words such as flashy are not defined; they were not converted to casual or silently removed.",
  ambiguous_compositional_or_scope: "Name one garment and its colour choices, for example black or grey trousers. Alternatives across different garment roles are ambiguous here.",
  ambiguous_compositional_antecedent: "Name the garment instead of one or ones; no previous garment could be bound safely.",
  ambiguous_compositional_soft_binding: "Name one upper or lower garment before preferably, or state one explicit preference such as I prefer blue trousers.",
  multiple_compositional_preferences: "Use one optional upper or lower colour/category preference. Multiple independent wishes are not supported.",
  unsupported_compositional_preference: "Optional requests support one positive upper/lower category or named-colour wish; material and other modifiers remain unsupported.",
  compositional_profile_scope_unavailable: "Compositional requests support P1/C1 text only. Turn off P2/C2 and detailed controls; no requirement was dropped.",
  compositional_context_contract_unavailable: "The occasion was recognized, but this rewritten contextual request needs a separate verified persistence contract. Use a complete existing context sentence; no neutral outfit was substituted.",
  compositional_context_role_required: "State your role for the interview or wedding, for example interview candidate or wedding guest. No role was assumed.",
  compositional_continuation_unavailable: "Another outfit is not supported for this new compositional proof. Start a new request; no previous conditions were replaced.",
  ambiguous_normalized_contraction: "Write your or you are explicitly instead of ur. That abbreviation is ambiguous; no garment requirement was guessed.",
  ambiguous_normalized_preference_boundary: "Finish one required garment clause before preferably. A dangling and, or, with or but cannot safely identify the optional boundary.",
  normalized_profile_scope_unavailable: "Normalized requests currently support non-contextual P1/C1 text only. Turn off P2/C2 and detailed controls, or use the original supported wording. No requirement was dropped.",
  normalized_context_scope_unavailable: "This contextual abbreviation combination is outside the verified normalization scope. Use a complete supported context sentence; no generic outfit was substituted.",
  soft_preference_apostrophe_required: "Use I'd prefer with an apostrophe, for example: I'd prefer black trousers. Id prefer is not a supported phrase; no request was rewritten or made mandatory.",
  hard_evidence_unknown_conflicting_preference: "The mandatory garment details, including colour, cannot be verified from saved evidence. The optional preference conflicts with a mandatory requirement, which takes priority. No requirement was relaxed; this does not prove that no outfit matches.",
  unsupported_sleeve_mapping: "Three-quarter sleeves do not have an established mapping to the saved sleeve lengths. No short- or long-sleeve value was substituted.",
  multiple_requests: "Request one outfit at a time. Multiple outfit recommendations in one request are not supported.",
  unsupported_external_capability: "I can suggest outfits from your saved wardrobe, but cannot check weather, buy clothes or verify physical guarantees such as waterproofing. No outfit was generated.",
  unsupported_exclusion_target: "I could not represent that exclusion. Name a supported garment category or material; your requirement was not removed.",
  unsupported_fit_mapping: "Slim-fit and relaxed-fit do not have an established mapping to the saved garment silhouettes. Use regular-fit, loose-fitting, or a supported silhouette. These describe garment shape, not wearer sizing.",
  outfit_style_scope_required: "Do you mean a styled outfit or one particular garment? Say, for example, A formal outfit, or name the garment and style. No scope was guessed; style alone does not certify an occasion or dress code.",
  ambiguous_garment_reference: "Name the garment instead of one or ones. I could not safely attach the contrast to a single garment; no outfit was generated.",
  contrasting_garment_scope: "The contrast refers to different garment roles or types. State what to include and what to exclude explicitly.",
  language_negated_event: "You said you are not attending that activity. Which occasion should this outfit be for?",
  language_ambiguous_activity: "Which activity do you mean? For example, an ordinary office day, a work meeting, dinner, or a casual outing with friends.",
  language_context_clarification: "Please clarify the activity. For an interview, say whether it is a job interview and your role. For a presentation, say where it takes place and whether you are presenting or attending.",
  mixed_context_dress_code_required: "Your interview role was understood. Please also state the dress code: this existing job-interview policy supports smart casual only. No dress code was assumed and no outfit was generated.",
  semantic_context_clarification: "Please name the activity or purpose and any required role. A mall visit, team meeting or unspecified seminar does not establish one supported outfit context; no purpose was guessed.",
  semantic_context_scope_unavailable: "That event or role cannot be safely mapped to the supported contexts. Wedding support is for the existing guest policy; no bridal, professional or neutral substitute was generated.",
  semantic_context_collision: "The activities imply different outfit policies. Please clarify one complete situation; no activity or garment condition was dropped.",
  language_conflicting_request: "The request contains conflicting, alternative, or unclear conditions. Please state one activity and the requirements to keep together.",
  language_unsupported_requirement: "I could not represent one of the requested features or modifiers. Please clarify it or use the garment requirements controls. Your condition was kept; no outfit was generated.",
  soft_preference_requires_settings: "Conversational soft preferences are not supported yet. Use the available saved preference settings, or state a mandatory requirement only if that is what you mean. Your preference was not turned into a hard condition.",
  alternative_requires_parent: "Open a completed recommendation and, if available, use Suggest another outfit. It keeps the original requirements and excludes outfit bases already suggested in that sequence. No previous recommendation was assumed.",
  unsupported_intent: "Tell me the activity or garment requirements for one outfit. For example: I'm having dinner, or recommend an outfit for shopping.",
  required_garment_description_unknown: "The required garment details, such as colour, pattern or material, cannot be verified from the saved evidence. Information may be missing, unqualified or out of date. This is not a proven nonmatch; your requirements were kept.",
  garment_description_mismatch: "No complete outfit matches all the recorded garment features you requested. All conditions and restrictions were kept.",
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
  if (status.startsWith("Refinement") || status.startsWith("GarmentRefinement")) return messages[status] ?? "This refinement could not be completed.";
  if (status === "AttributeConflict") return messages.AttributeConflict;
  if (typeof contextReason === "string" && contextReasons[contextReason]) return contextReasons[contextReason];
  return typeof contextual === "string" && contextualMessages.has(contextual) ? contextual : messages[status] ?? "The request could not be completed safely.";
}
export function contextEvidenceMessage(version: unknown, status: unknown, reason?: unknown) {
  if (reason === "required_garment_description_unknown" || reason === "garment_description_mismatch") return undefined;
  if ((version === "general-context-explanation-1.4.0" || version === "general-context-explanation-2.0.0") && status === "InsufficientEvidence") return "No complete outfit has enough usable saved information for this request. Suggestions can use supported saved casual or smart-casual style without a separate review. Check missing, unsupported or inconsistent styles and any requested dress code. Correct uncovered styles should not be relabelled. Attribute corrections and occasion restrictions are optional; no per-garment review is required for this policy.";
  if (version === "general-context-explanation-1.3.0" && status === "InsufficientEvidence") return "Current evidence does not establish a complete everyday outfit. In Wardrobe Edit, explicitly select and save a supported style to confirm it once. Missing or stale evidence may need correction; correct uncovered styles should not be relabelled. Collar, tailoring and condition observations are not required for this ordinary appearance policy.";
  if (version === "general-context-explanation-1.2.0" && status === "InsufficientEvidence") return "No complete outfit has enough usable saved style information for this request. Check saved styles and any requested dress code; physical condition and dress-code compliance are not established by this suggestion.";
  return version === "general-context-explanation-1.1.0" && status === "InsufficientEvidence"
    ? "Current garment evidence does not establish a suitable complete outfit for this policy. Missing or stale attributes may need review; an uncovered style can be correct and should not be relabelled just to obtain a result."
    : undefined;
}
export function errorMessage(error: unknown) {
  const contextual = error instanceof ApiError && error.payload && typeof error.payload === "object" && "contextual_message" in error.payload ? error.payload.contextual_message : undefined;
  const contextReason = error instanceof ApiError && error.payload && typeof error.payload === "object" && "context_reason" in error.payload ? error.payload.context_reason : undefined;
  return error instanceof ApiError && error.outcome ? outcomeMessage(error.outcome, contextual, contextReason) : error instanceof Error ? error.message : "The service could not be reached.";
}
