import type { IntegratedRecommendation, RecommendationCapabilities } from "./api";
import type { AssistantDraft } from "./recommendation-session";
import { attributeDraftVersion, storedTypedAttributes } from "./attribute-request";

export function continuationDescriptor(record?: IntegratedRecommendation) {
  if (record?.development_continuation?.version === "mixed-development-continuation-1.0.0") return record.development_continuation;
  if (record?.scoring_display?.kind === "RequestLocalPreference") return undefined;
  if (record?.garment_continuation?.version === "garment-only-continuation-display-1.0.0") return record.garment_continuation;
  const view=record?.scoring_display;
  if (view?.kind === "ContextRelevance" && view.version === "assistant-scoring-display-2.2.0"
    || view?.kind === "AttributePreference" && view.version === "assistant-scoring-display-3.0.0"
    || view?.kind === "PaletteCompatibility" && view.version === "assistant-scoring-display-4.0.0") return view.refinement;
  return undefined;
}

/** An explicit history link must never fall back to an unrelated local draft. */
export function followUpChatId(search: string): string | undefined {
  const query=new URLSearchParams(search);
  if (!query.has("continue_chat")) return undefined;
  const values=query.getAll("continue_chat");
  if (values.length!==1 || !/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(values[0]))
    throw new Error("Choose one valid completed chat from history. No previous recommendation was guessed.");
  return values[0];
}

/** UI availability only; authentication and locked verification stay server-owned. */
export function eligibleContinuation(record: IntegratedRecommendation | undefined, capabilities: RecommendationCapabilities | undefined, wearerId: string | undefined, ended=false): boolean {
  const descriptor=continuationDescriptor(record), action=descriptor?.next_action;
  if (!record?.chat_id || !record.request_text || record.wearer_archived || !wearerId
      || (record.mixed_wardrobe_display ? record.wearer_association?.profile_id : record.intended_wearer?.profile_id)!==wearerId || ended || !descriptor || descriptor.limit_reached
      || !Number.isInteger(descriptor.ordinal) || descriptor.ordinal<0 || descriptor.ordinal>=9
      || !action?.submission_key || action.refinement.version!=="assistant-refinement-request-1.0.0"
      || action.refinement.kind!=="alternative" || action.refinement.parent_recommendation_id!==record.id
      || !capabilities?.assistant_enabled) return false;
  if (record.mixed_wardrobe_display) return capabilities.mixed_wardrobe?.enabled===true && capabilities.mixed_wardrobe.wearers?.includes(wearerId)===true;
  return record.garment_continuation?.version==="garment-only-continuation-display-1.0.0"
    ? capabilities.garment_continuation?.version==="garment-only-continuation-capabilities-1.0.0" && capabilities.garment_continuation.available
    : capabilities.refinement?.version==="recommendation-refinement-capabilities-1.0.0" && capabilities.refinement.available===true;
}

/** Reopen one explicitly chosen authenticated history record; perform no POST. */
export function historyFollowUpDraft(record: IntegratedRecommendation, wearerId: string | null, key: string): AssistantDraft {
  const descriptor=continuationDescriptor(record);
  if (!record.chat_id || !record.request_text || !wearerId || (record.mixed_wardrobe_display ? record.wearer_association?.profile_id : record.intended_wearer?.profile_id) !== wearerId || record.wearer_archived)
    throw new Error("Select the same active wearer as this saved recommendation before continuing. No parent was substituted.");
  if (!descriptor?.next_action || descriptor.limit_reached) throw new Error("This saved result has no continuation action. Its history remains read-only.");
  const attributes=storedTypedAttributes(record);
  return {key, text:record.request_text, submitted:record.request_text, chatId:record.chat_id,
    wearerProfileId:wearerId, wearerName:record.mixed_wardrobe_display ? record.wearer_association?.name ?? undefined : record.intended_wearer?.name_at_request,
    preferenceProfile:descriptor.next_action.preference_profile, compatibilityProfile:descriptor.next_action.compatibility_profile,
    attributeDraftVersion:attributes ? attributeDraftVersion : undefined, attributeConditions:attributes};
}
