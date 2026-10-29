import { getAccessToken, refinementCategories, type RefinementAction } from "./api";

// Namespace only; backend authentication remains authoritative.
export const sessionOwner = () => getAccessToken()?.split(".")[0] ?? "signed-out";
const prefix = "smart_wardrobe_interaction:";
export type AssistantDraft = { key: string; text: string; submitted?: string; chatId?: string; refinement?: RefinementAction; previousChatId?: string };
function validAction(action: unknown): action is RefinementAction {
  if (!action || typeof action !== "object" || !("version" in action) || action.version !== "assistant-refinement-request-1.0.0" || !("kind" in action)) return false;
  if (action.kind === "initial" && "excluded_categories" in action && Object.keys(action).length === 3) {
    const values = action.excluded_categories;
    return Array.isArray(values) && values.length <= 13 && new Set(values).size === values.length && values.every(c => typeof c === "string" && (refinementCategories as readonly string[]).includes(c));
  }
  return action.kind === "alternative" && "parent_recommendation_id" in action && Object.keys(action).length === 3 && typeof action.parent_recommendation_id === "string" && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(action.parent_recommendation_id);
}
export function homepageFlowKey() {
  const owner = sessionOwner();
  const state = window.history.state ?? {};
  if (state.wardrobeHomepage?.owner === owner) return state.wardrobeHomepage.key as string;
  const key = crypto.randomUUID();
  // Preserve Next's own history fields; one flow is one browser history entry.
  window.history.replaceState({ ...state, wardrobeHomepage: { owner, key } }, "");
  return key;
}
export function leaveHomepageFlow() {
  // Next copies custom history state to a newly pushed entry. Clear the copy
  // on other routes, preserving the original Homepage entry for reload/back.
  if (!window.history.state?.wardrobeHomepage) return;
  const state = { ...window.history.state };
  delete state.wardrobeHomepage;
  window.history.replaceState(state, "");
}
export function readAssistantDraft(): AssistantDraft {
  try {
    const stored = JSON.parse(sessionStorage.getItem(prefix + sessionOwner()) ?? "null");
    if (stored && typeof stored.key === "string" && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/.test(stored.key) && typeof stored.text === "string" && stored.text.length <= 500 &&
      (stored.submitted === undefined || typeof stored.submitted === "string" && stored.submitted.length <= 500) &&
      (stored.chatId === undefined || typeof stored.chatId === "string") &&
      (stored.previousChatId === undefined || typeof stored.previousChatId === "string") &&
      (stored.refinement === undefined || validAction(stored.refinement))) return stored;
  } catch { /* A malformed local draft is not a completed server interaction. */ }
  return { key: crypto.randomUUID(), text: "" };
}
export function writeAssistantDraft(draft: AssistantDraft) {
  sessionStorage.setItem(prefix + sessionOwner(), JSON.stringify(draft));
}
const pending = new Map<string, Promise<unknown>>();
export function singleFlight<T>(key: string, operation: () => Promise<T>): Promise<T> {
  const scoped = `${sessionOwner()}:${key}`;
  const existing = pending.get(scoped);
  if (existing) return existing as Promise<T>;
  const promise = operation().finally(() => pending.delete(scoped));
  pending.set(scoped, promise);
  return promise;
}
