const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(message: string, public status: number, public outcome?: string, public payload?: unknown) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof window !== "undefined") {
    const token = window.sessionStorage.getItem("smart_wardrobe_access_token");
    if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new Error("Could not connect to the wardrobe service. Check your connection and try again.");
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const quotaError = response.status === 409 && detail?.detail?.code === "WardrobeQuotaExceeded" && typeof detail.detail.message === "string" ? detail.detail : undefined;
    const outcome = quotaError?.code ?? (typeof detail?.outcome === "string" ? detail.outcome : typeof detail?.status === "string" ? detail.status : undefined);
    const message = response.status === 401 && path !== "/account/login" ? "Your session has expired. Sign in again to continue." : quotaError ? quotaError.message : typeof detail?.detail === "string" ? detail.detail : Array.isArray(detail?.detail) ? detail.detail.map((item: { msg: string }) => item.msg).join(" ") : response.status >= 500 ? "The wardrobe service is unavailable. Please try again shortly." : "The request could not be completed.";
    throw new ApiError(message, response.status, outcome, detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export type OwnerStyleConfirmation = { contract: "owner-style-confirmation-1.0.0"; expected_revision: string; style: string };
export type StyleConfirmationView = { revision: string; current: boolean; source?: "candidate_accept" | "garment_edit" | null };
export type AdmissionMode = "manual_review_v1" | "automatic_structural_v1";
export type ProcessingAdmission = { mode: AdmissionMode; state: string; reason: string | null; garment_ids: string[] };
export type SavedAttributeEvidence = { state: "Absent" | "Known" | "Malformed" | "Stale"; origin: string; contributor: string | null; recorded_at: string | null };
export type ProcessingItem = { style_confirmation?: StyleConfirmationView; id: string; detected_category: string; confidence: number; review_status: "pending" | "accepted" | "rejected" | "confirmed"; crop_media_id: string; preferred_media_id: string; mask_media_id: string | null; vtoff_media_id: string | null; bounding_box: number[] | null; attributes: Record<string, unknown> };
export type ProcessingJob = { admission?: ProcessingAdmission; id: string; status: string; error_message?: string | null; progress_percent: number; progress_message?: string | null; items: ProcessingItem[] };

export async function submitWardrobeImage(file: File, admissionMode: AdmissionMode = "manual_review_v1") {
  const form = new FormData(); form.append("file", file);
  return request<{ id: string; status: string; admission_mode?: AdmissionMode }>(`/processing/jobs?admission_mode=${admissionMode}`, { method: "POST", body: form });
}
export const getProcessingJob = (jobId: string) => request<ProcessingJob>(`/processing/jobs/${jobId}`);
export const reviewProcessingJob = (jobId: string, items: unknown[]) => request<ProcessingJob>(`/processing/jobs/${jobId}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items }) });
export const confirmProcessingJob = (jobId: string, itemIds: string[], saveMode: "garments" | "outfit", outfitName?: string, admissionMode: AdmissionMode = "manual_review_v1") => request<{ garment_ids: string[]; outfit_id: string | null }>(`/processing/jobs/${jobId}/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ save_mode: saveMode, item_ids: itemIds, outfit_name: saveMode === "outfit" ? outfitName : null, admission_mode: admissionMode }) });
export const cancelProcessingJob = (jobId: string) => request<void>(`/processing/jobs/${jobId}/cancel`, { method: "POST" });

export type WardrobeQuota = { policy_version: string; scope: string; limit: number; used: number; remaining: number; over_limit: boolean; pending_reserved: number };
export const getWardrobeQuota = () => request<WardrobeQuota>("/wardrobe/quota", { cache: "no-store" });
export const wardrobeCapacityText = (quota: WardrobeQuota) => `Active garments: ${quota.used} / ${quota.limit} — ${quota.remaining} space${quota.remaining === 1 ? "" : "s"} left${quota.over_limit ? " (over capacity)" : ""}`;

export type SuitabilityDeclaration = { field: "occasion" | "formality"; value: string; label: string; choice: "unknown" | "allow" | "deny"; state: "Unknown" | "Pass" | "Fail"; conflict: boolean; malformed: boolean; allow_tag: string; deny_tag: string };
export type GarmentTagEdit = { version: string; revision: string; editable: boolean; tags: string[]; ordinary_tags: string[]; reserved_indices: number[]; declarations: SuitabilityDeclaration[]; malformed: { index: number; fields: string[] }[]; source_state: string; colour_names: string[] };
export type ContextualGarmentEdit = { revision: string; styles: string[]; style_state: string; style_options: string[]; review_current: boolean; wedding_choice: "unknown" | "allow" | "deny"; evidence_state: string };
export type AppearanceReviewAction = { withdraw: true } | { construction_features: { collared_neckline: boolean | null; tailored_cut: boolean | null; structured_shape: boolean | null }; condition_observation: "clean_intact" | "needs_attention" | "unknown" };
export type AppearanceEdit = { revision: string; current: boolean; state: string; features: [string, boolean | null][]; condition: string | null; reviewed_at: string | null };
export type Garment = { style_confirmation?: StyleConfirmationView; id: string; status?: string | null; name: string; category: string; primary_colour?: string | null; pattern?: string | null; preferred_media_id: string; is_favourite: boolean; attributes: Record<string, unknown>; tag_edit?: GarmentTagEdit; contextual_edit?: ContextualGarmentEdit; appearance_edit?: AppearanceEdit; style_tags?: unknown; additional_attributes?: Record<string, unknown> | null; created_at?: string; updated_at?: string };
export type OutfitItem = { outfit_id: string; garment_id: string; role: string; item_order: number; name: string; category: string };
export type Outfit = { id: string; name: string; description?: string | null; creation_type: "image_upload" | "manual" | "recommendation"; is_favourite: boolean; items: OutfitItem[]; created_at?: string; updated_at?: string };
export type WardrobeSort = "updated_desc" | "updated_asc" | "name_asc" | "name_desc" | "favourites";
export type GarmentFilters = { query?: string; category?: string; favourite?: boolean; sort?: WardrobeSort; colour?: string; style?: string; availability?: "available" | "unavailable" | "archived" | "all" };
export type OutfitFilters = GarmentFilters & { creationType?: Outfit["creation_type"] };
export type WardrobeDependencies = { resource: { id: string; name: string; type: "garment" | "outfit" }; active_outfits: { id: string; name: string }[]; active_visualisations: { id: string; status: string }[]; can_archive: boolean; policy: string };
export type RecommendationItem = { recommendation_id: string; garment_id: string; garment_role: string; item_order: number; name: string; category: string; preferred_media_id: string };
export type Recommendation = { id: string; recommendation_type: string; status: "available" | "saved"; request_text?: string; created_at?: string; request_match_score: number; compatibility_score: number; preference_score: number; total_score: number; items: RecommendationItem[] };
export type SavedRecommendationOutfit = { id: string; name: string; garment_ids: string[] };
export type PersonImage = { id: string; media_id: string; display_name: string; status: string };
export type VisualisationItem = { garment_id: string; source_media_id: string; category: string; role: string; item_order: number };
export type VisualisationPreparation = { source_type: "outfit" | "recommendation"; source_id: string; category: "upper" | "lower" | "overall" | "outfit"; categories: ("upper" | "lower" | "overall")[]; capture_guidance: string; items: (VisualisationItem & { name: string })[] };
export type Visualisation = { id: string; status: "queued" | "processing" | "completed" | "failed" | "cancelled"; source_type: "outfit" | "recommendation"; outfit_id?: string | null; recommendation_id?: string | null; person_image_id: string; output_media_id?: string | null; output_kind?: "generated" | "development" | null; model_version?: string | null; error_code?: string | null; error_message?: string | null; progress_percent: number; progress_current: number; progress_total: number; progress_message?: string | null; started_at?: string | null; configuration: Record<string, unknown>; metrics: Record<string, unknown>; items: VisualisationItem[]; notice: string; is_development_fallback: boolean };

function wardrobeQuery(filters: GarmentFilters & { creationType?: Outfit["creation_type"] } = {}) {
  const params = new URLSearchParams();
  if (filters.query) params.set("query", filters.query);
  if (filters.category) params.set("category", filters.category);
  if (filters.favourite !== undefined) params.set("favourite", String(filters.favourite));
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.colour) params.set("colour", filters.colour);
  if (filters.style) params.set("style", filters.style);
  if (filters.availability) params.set("availability", filters.availability);
  if (filters.creationType) params.set("creation_type", filters.creationType);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const getGarments = (filters: GarmentFilters = {}) => request<Garment[]>(`/wardrobe/garments${wardrobeQuery(filters)}`);
export const getOutfits = (filters: OutfitFilters = {}) => request<Outfit[]>(`/wardrobe/outfits${wardrobeQuery(filters)}`);
export type GarmentUpdate = Partial<Pick<Garment, "name" | "category" | "primary_colour" | "pattern" | "is_favourite">> & { style_confirmation?: OwnerStyleConfirmation; attributes?: Record<string, string | string[] | boolean | null> };
export const updateGarment = (id: string, payload: GarmentUpdate, tagRevision?: string) => request<Garment>(`/wardrobe/garments/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json", ...(tagRevision ? { "If-Match": tagRevision } : {}) }, body: JSON.stringify(payload) });
export const reviewContextualSuitability = (id: string, payload: { revision: string; review_style?: boolean; wedding_choice?: "unknown" | "allow" | "deny"; appearance_review?: AppearanceReviewAction }) => request<Garment>(`/wardrobe/garments/${id}/contextual-suitability`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
export const deleteGarment = (id: string) => request<void>(`/wardrobe/garments/${id}`, { method: "DELETE" });
export const getGarmentDependencies = (id: string) => request<WardrobeDependencies>(`/wardrobe/garments/${id}/dependencies`);
export const createOutfit = (name: string, garmentIds: string[], description?: string) => request<Outfit>("/wardrobe/outfits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, garment_ids: garmentIds, description }) });
export const updateOutfit = (id: string, payload: { name?: string; description?: string; is_favourite?: boolean; garment_ids?: string[] }) => request<Outfit>(`/wardrobe/outfits/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
export const deleteOutfit = (id: string) => request<void>(`/wardrobe/outfits/${id}`, { method: "DELETE" });
export const getOutfitDependencies = (id: string) => request<WardrobeDependencies>(`/wardrobe/outfits/${id}/dependencies`);
export const getRecommendations = () => request<Recommendation[]>("/recommendations");
export const saveRecommendationAsOutfit = (id: string, name?: string) => request<SavedRecommendationOutfit>(`/recommendations/${id}/save-as-outfit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
export const getRecommendationSavedOutfit = (id: string) => request<{ saved: boolean; outfit_id: string | null }>(`/recommendations/${id}/saved-outfit`);
export const getPersonImages = () => request<PersonImage[]>("/visualisations/person-images");
export async function uploadPersonImage(file: File) { const form = new FormData(); form.append("file", file); return request<PersonImage>("/media/person-images", { method: "POST", body: form }); }
export type VisualisationSource = { outfitId: string; recommendationId?: never } | { recommendationId: string; outfitId?: never };
const visualisationSourceBody = (source: VisualisationSource) => ({ outfit_id: source.outfitId, recommendation_id: source.recommendationId });
export const prepareVisualisation = (source: VisualisationSource) => request<VisualisationPreparation>("/visualisations/prepare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(visualisationSourceBody(source)) });
export const createVisualisation = (source: VisualisationSource, personImageId: string) => request<{ id: string; status: string }>("/visualisations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ outfit_id: source.outfitId, recommendation_id: source.recommendationId, person_image_id: personImageId }) });
export const getVisualisation = (id: string) => request<Visualisation>(`/visualisations/${id}`);
export const cancelVisualisation = (id: string) => request<void>(`/visualisations/${id}/cancel`, { method: "POST" });
export const mediaUrl = (mediaId: string) => `${API_URL}/media/${mediaId}`;
export type Profile = { id: string; email: string; display_name: string; account_status: string; created_at: string };
export type UserPreference = { id: string; preference_type: string; preference_value: Record<string, unknown>; weight?: number | null; source: string; is_active: boolean };
export const getProfile = () => request<Profile>("/account/profile");
export const updateProfile = (displayName: string) => request<Profile>("/account/profile", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ display_name: displayName }) });
export const getPreferences = () => request<UserPreference[]>("/account/preferences");
export type ClearedPreference = { preference_type: string; preference_value: { values: [] }; weight: number | null; is_active: false };
export const savePreference = (preferenceType: string, preferenceValue: Record<string, unknown>, weight?: number) => request<UserPreference | ClearedPreference>(`/account/preferences/${encodeURIComponent(preferenceType)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preference_value: preferenceValue, weight }) });
export type Authentication = { access_token: string; profile: Profile };
export type Registration = { status: "Registered"; message: string; profile: Profile };
export const register = (email: string, password: string, displayName: string, passwordConfirmation: string) => request<Registration>("/account/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password, display_name: displayName, password_confirmation: passwordConfirmation }) });
export type PreferenceOptions = { colours: string[]; styles: string[]; garment_categories: { kind: "category" | "group"; value: string }[]; formality: string[] };
export const getPreferenceOptions = () => request<PreferenceOptions>("/account/preference-options");
export const login = (email: string, password: string) => request<Authentication>("/account/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
export const saveAccessToken = (token: string) => window.sessionStorage.setItem("smart_wardrobe_access_token", token);
export const clearAccessToken = () => {
  window.sessionStorage.removeItem("smart_wardrobe_access_token");
  for (const key of Object.keys(window.sessionStorage)) if (key.startsWith("smart_wardrobe_interaction:")) window.sessionStorage.removeItem(key);
  const state = { ...window.history.state };
  delete state.wardrobeHomepage;
  window.history.replaceState(state, "");
};
export const getAccessToken = () => typeof window === "undefined" ? null : window.sessionStorage.getItem("smart_wardrobe_access_token");
export const logout = (token: string) => request<void>("/account/logout", { method: "POST", headers: { Authorization: `Bearer ${token}` } });

export type HistoricalItem = { garment_id: string; garment_role: string; item_order: number; name: string | null; category: string | null; preferred_media_id: string | null; currently_eligible: boolean; snapshot_available: boolean; historical_media_accessible?: boolean };
export type ExactRatio = { numerator: number; denominator: number };
export type LegacyScoringDisplay = {
  version: "assistant-scoring-display-1.0.0";
} & ({ kind: "Deferred"; profile_name: "compatibility_deferred" } | {
  kind: "Unavailable"; reason: string;
} | {
  kind: "Decision";
  profile_name: "experimental_compatibility_decision_v1";
  policy_version: string;
  policy_hash: string;
  raw_state: "Available" | "Unknown" | "NotApplicable";
  basis: "Computed" | "PartiallyConventional" | "FullyConventional" | "NoPairReference";
  raw_value: ExactRatio | null;
  decision_contribution: ExactRatio;
  lower: ExactRatio | null;
  upper: ExactRatio | null;
  known: number;
  possible: number;
  pair_count: number;
  structure: "top_bottom" | "top_bottom_outerwear" | "dress" | "dress_outerwear";
  weights: [ExactRatio, ExactRatio, ExactRatio];
});
export type StringRatio = { numerator: string; denominator: string };
export const refinementCategories = ["short_sleeve_top", "long_sleeve_top", "vest", "sling", "short_sleeve_outwear", "long_sleeve_outwear", "shorts", "trousers", "skirt", "short_sleeve_dress", "long_sleeve_dress", "vest_dress", "sling_dress"] as const;
export type RefinementCategory = typeof refinementCategories[number];
export type RefinementAction = { version: "assistant-refinement-request-1.0.0" } & (
  { kind: "initial"; excluded_categories: RefinementCategory[] } | { kind: "alternative"; parent_recommendation_id: string });
export type RefinementDescriptor = { version: "recommendation-refinement-lineage-1.0.0"; root_id: string; parent_id: string | null; ordinal: number; excluded_categories: RefinementCategory[]; root_R: StringRatio; root_total: StringRatio; mode: string; total_vs_root: "same" | "lower"; limit_reached: boolean; next_action: { submission_key: string; refinement: RefinementAction } | null; certificate_universe: string };
export type RefinementCapability = { version: "recommendation-refinement-capabilities-1.0.0"; available: boolean; categories: RefinementCategory[]; shortcuts: Record<string, RefinementCategory[]>; max_results: number; ordinary_situations: string[]; typed_input_only: boolean };
export type ContextRelevanceDisplay = { version: "assistant-scoring-display-2.0.0" | "assistant-scoring-display-2.1.0" | "assistant-scoring-display-2.2.0" } & ({ kind: "Unavailable"; reason: string } | {
  refinement?: RefinementDescriptor;
  kind: "ContextRelevance"; bundle_id?: string; context_plan?: { bindings: string[]; request: { context: { facets: { values: string[] } } } }; profile_name: string; policy_version: string;
  selection_mode: "best_evidenced_with_coverage_v1" | "baseline_disclosed_v1"; fallback_reason: string | null;
  objective: { target: string; authority: "prototype_convention" | "explicit_user_style"; explanation: string; limitations: string } | null;
  coverage: { hard_passed: number; point_candidates: number; unresolved_candidates: number; objective_unavailable_candidates: number; global_optimum_certified: boolean; already_seen?: number; below_floor_points?: number; unresolved_below_floor?: number };
  numeric_ties: number; compatibility_basis: string; total: StringRatio;
  components: { name: "R" | "C" | "P"; state: string; raw_value: StringRatio | null; contribution: StringRatio; weight: StringRatio; weighted: StringRatio; reasons: string[] }[];
  preferences: { id: string; kind: string; weight: StringRatio; suppressed: boolean }[]; preference_denominator: StringRatio;
  selected_members: { garment_id: string; role: string; styles: string[]; source_state: string; origin: string; review_state: string; match: number | null }[];
});
export type ScoringDisplay = LegacyScoringDisplay | ContextRelevanceDisplay;
export type IntegratedRecommendation = { id: string; chat_id: string | null; status: string; request_text?: string; created_at: string; items: HistoricalItem[]; total_score: number | null; compatibility_score: number | null; provenance: Record<string, unknown> | null; score_metadata?: unknown; scoring_display?: ScoringDisplay };
export type ContextSummary = { version: "general-context-explanation-1.0.0" | "general-context-explanation-1.1.0" | "general-context-explanation-1.2.0" | "general-context-explanation-1.3.0" | "general-context-explanation-1.4.0" | "general-context-explanation-2.0.0"; facets?: string[]; secondary_bindings?: string[]; negative_scope?: string | null; bundle_id?: string; evidence_contract?: string; scope_note?: string; role?: string | null; parent_negative?: string; missing_context?: string[]; situation: string; label: string; reason: string; assumptions: string[]; dress_code: string | null; formality: string | null; temporal: string[]; available: boolean; unavailable_conditions: string[]; binding?: string; policy_version?: string; declaration_target?: string; venue?: string | null; companions?: string[]; policy_note?: string | null; limits_note?: string; members?: { garment_id: string; saved_attribute_evidence?: SavedAttributeEvidence; style_verification?: "owner_reviewed_current" | "saved_unreviewed"; appearance_observations?: { features: [string, boolean | null][]; condition: string | null; reviewed_at: string | null }; appearance_current?: boolean; conditions: { field: string; state: string; basis: string; rule: string | null; declaration_target?: { field: string; value: string }; declaration_policy?: string; supporting_declarations?: { field: string; value: string; decision: string }[] }[] }[] };
export type RecommendationCapabilities = { refinement?: RefinementCapability; homepage_enabled: boolean; assistant_enabled: boolean; context_ranking?: { version: "context-ranking-capabilities-1.0.0" | "context-ranking-capabilities-1.1.0"; bundle_id?: string; profile: string; objectives: { situation: string; target: string; authority: string }[]; independent_appropriateness_validation: string }; context_support?: { version: string; situations: { id: string; label: string; policy_available: boolean; example?: string }[]; limits: string } };
export type RecommendationOutcome = { status: string; outcome?: string; complete: boolean; replayed?: boolean; recommendation?: IntegratedRecommendation; detail?: string; contextual_message?: string; context_reason?: string; context_summary?: ContextSummary };
export type ChatSummary = { chat_id: string; request_text: string; created_at: string; completed_at: string; recommendation_id: string; recommendation_status: string; read_only: true };
export type ChatPage = { status: string; items: ChatSummary[]; total: number; limit: number; next_cursor: string | null };
export type CompletedChat = { chat_id: string; request_text: string; structured_request: Record<string, unknown> | null; interpreted_entities: unknown; recommendation: IntegratedRecommendation; read_only: true };
export const getRecommendationCapabilities = () => request<RecommendationCapabilities>("/recommendations/capabilities");
export const createHomepageRecommendation = (submissionKey: string) => request<RecommendationOutcome>("/recommendations/homepage", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ submission_key: submissionKey }) });
/** @deprecated Generation requires a durable submission key; unkeyed calls reject without a request. */
export function createRecommendation(requestText: string): Promise<Recommendation>;
export function createRecommendation(requestText: string, submissionKey: string, refinement?: RefinementAction): Promise<RecommendationOutcome>;
export async function createRecommendation(requestText: string, submissionKey?: string, refinement?: RefinementAction): Promise<Recommendation | RecommendationOutcome> {
  if (submissionKey === undefined) throw new ApiError("A durable submission key is required to request an outfit.", 422, "InvalidInput");
  const capabilities = await getRecommendationCapabilities();
  if (!capabilities.assistant_enabled) throw new ApiError("Outfit Assistant integration is currently disabled.", 404, "IntegrationDisabled");
  return request<RecommendationOutcome>("/recommendations?pipeline=integrated", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_text: requestText, submission_key: submissionKey, ...(refinement ? { refinement } : {}) }) });
}
export const getChatHistory = (search: string, cursor?: string) => request<ChatPage>(`/chats?${new URLSearchParams({ search, limit: "50", ...(cursor ? { cursor } : {}) })}`);
export const getCompletedChat = (chatId: string) => request<CompletedChat>(`/chats/${encodeURIComponent(chatId)}`);
export async function downloadProtectedMedia(mediaId: string, filename: string) {
  const token = getAccessToken();
  if (!token) throw new Error("Sign in before downloading protected media.");
  const response = await fetch(mediaUrl(mediaId), { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Could not download the protected media.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
