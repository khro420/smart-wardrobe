const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof window !== "undefined") {
    const token = window.sessionStorage.getItem("smart_wardrobe_access_token");
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new Error("Could not connect to the wardrobe service. Check your connection and try again.");
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    if (response.status === 401) throw new Error("Your session has expired. Sign in again to continue.");
    if (response.status >= 500) throw new Error("The wardrobe service is unavailable. Please try again shortly.");
    const message = typeof detail?.detail === "string" ? detail.detail : Array.isArray(detail?.detail) ? detail.detail.map((item: { msg: string }) => item.msg).join(" ") : "The request could not be completed.";
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export type ProcessingItem = { id: string; detected_category: string; confidence: number; review_status: "pending" | "accepted" | "rejected" | "confirmed"; crop_media_id: string; preferred_media_id: string; mask_media_id: string | null; vtoff_media_id: string | null; bounding_box: number[] | null; attributes: Record<string, unknown> };
export type ProcessingJob = { id: string; status: string; error_message?: string | null; items: ProcessingItem[] };

export async function submitWardrobeImage(file: File) {
  const form = new FormData(); form.append("file", file);
  return request<{ id: string; status: string }>("/processing/jobs", { method: "POST", body: form });
}
export const getProcessingJob = (jobId: string) => request<ProcessingJob>(`/processing/jobs/${jobId}`);
export const reviewProcessingJob = (jobId: string, items: unknown[]) => request<ProcessingJob>(`/processing/jobs/${jobId}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items }) });
export const confirmProcessingJob = (jobId: string, itemIds: string[], saveMode: "garments" | "outfit", outfitName?: string) => request<{ garment_ids: string[]; outfit_id: string | null }>(`/processing/jobs/${jobId}/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ save_mode: saveMode, item_ids: itemIds, outfit_name: saveMode === "outfit" ? outfitName : null }) });
export const cancelProcessingJob = (jobId: string) => request<void>(`/processing/jobs/${jobId}/cancel`, { method: "POST" });

export type Garment = { id: string; name: string; category: string; primary_colour?: string | null; pattern?: string | null; preferred_media_id: string; is_favourite: boolean; attributes: Record<string, unknown>; created_at?: string; updated_at?: string };
export type OutfitItem = { outfit_id: string; garment_id: string; role: string; item_order: number; name: string; category: string };
export type Outfit = { id: string; name: string; description?: string | null; creation_type: "image_upload" | "manual" | "recommendation"; is_favourite: boolean; items: OutfitItem[]; created_at?: string; updated_at?: string };
export type WardrobeSort = "updated_desc" | "updated_asc" | "name_asc" | "name_desc" | "favourites";
export type GarmentFilters = { query?: string; category?: string; favourite?: boolean; sort?: WardrobeSort };
export type OutfitFilters = GarmentFilters & { creationType?: Outfit["creation_type"] };
export type WardrobeDependencies = { resource: { id: string; name: string; type: "garment" | "outfit" }; active_outfits: { id: string; name: string }[]; active_visualisations: { id: string; status: string }[]; can_archive: boolean; policy: string };
export type RecommendationItem = { recommendation_id: string; garment_id: string; garment_role: string; item_order: number; name: string; category: string; preferred_media_id: string };
export type Recommendation = { id: string; recommendation_type: string; status: "available" | "saved"; request_text?: string; created_at?: string; request_match_score: number; compatibility_score: number; preference_score: number; total_score: number; items: RecommendationItem[] };
export type SavedRecommendationOutfit = { id: string; name: string; garment_ids: string[] };
export type PersonImage = { id: string; media_id: string; display_name: string; status: string };
export type VisualisationItem = { garment_id: string; source_media_id: string; category: string; role: string; item_order: number };
export type VisualisationPreparation = { source_type: "outfit" | "recommendation"; source_id: string; category: "upper" | "lower" | "overall"; capture_guidance: string; items: (VisualisationItem & { name: string })[] };
export type Visualisation = { id: string; status: "queued" | "processing" | "completed" | "failed" | "cancelled"; source_type: "outfit" | "recommendation"; outfit_id?: string | null; recommendation_id?: string | null; person_image_id: string; output_media_id?: string | null; output_kind?: "generated" | "development" | null; model_version?: string | null; error_code?: string | null; error_message?: string | null; configuration: Record<string, unknown>; metrics: Record<string, unknown>; items: VisualisationItem[]; notice: string; is_development_fallback: boolean };

function wardrobeQuery(filters: GarmentFilters & { creationType?: Outfit["creation_type"] } = {}) {
  const params = new URLSearchParams();
  if (filters.query) params.set("query", filters.query);
  if (filters.category) params.set("category", filters.category);
  if (filters.favourite !== undefined) params.set("favourite", String(filters.favourite));
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.creationType) params.set("creation_type", filters.creationType);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const getGarments = (filters: GarmentFilters = {}) => request<Garment[]>(`/wardrobe/garments${wardrobeQuery(filters)}`);
export const getOutfits = (filters: OutfitFilters = {}) => request<Outfit[]>(`/wardrobe/outfits${wardrobeQuery(filters)}`);
export type GarmentUpdate = Partial<Pick<Garment, "name" | "category" | "primary_colour" | "pattern" | "is_favourite">> & { attributes?: Record<string, string | string[] | boolean> };
export const updateGarment = (id: string, payload: GarmentUpdate) => request<Garment>(`/wardrobe/garments/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
export const deleteGarment = (id: string) => request<void>(`/wardrobe/garments/${id}`, { method: "DELETE" });
export const getGarmentDependencies = (id: string) => request<WardrobeDependencies>(`/wardrobe/garments/${id}/dependencies`);
export const createOutfit = (name: string, garmentIds: string[], description?: string) => request<Outfit>("/wardrobe/outfits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, garment_ids: garmentIds, description }) });
export const updateOutfit = (id: string, payload: { name?: string; description?: string; is_favourite?: boolean; garment_ids?: string[] }) => request<Outfit>(`/wardrobe/outfits/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
export const deleteOutfit = (id: string) => request<void>(`/wardrobe/outfits/${id}`, { method: "DELETE" });
export const getOutfitDependencies = (id: string) => request<WardrobeDependencies>(`/wardrobe/outfits/${id}/dependencies`);
export const getRecommendations = () => request<Recommendation[]>("/recommendations");
export const createRecommendation = (requestText: string) => request<Recommendation>("/recommendations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_text: requestText }) });
export const saveRecommendationAsOutfit = (id: string, name?: string) => request<SavedRecommendationOutfit>(`/recommendations/${id}/save-as-outfit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
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
export const savePreference = (preferenceType: string, preferenceValue: Record<string, unknown>, weight?: number) => request<UserPreference>(`/account/preferences/${encodeURIComponent(preferenceType)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preference_value: preferenceValue, weight }) });
export type Authentication = { access_token: string; profile: Profile };
export const register = (email: string, password: string, displayName: string) => request<Authentication>("/account/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password, display_name: displayName }) });
export const login = (email: string, password: string) => request<Authentication>("/account/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
export const saveAccessToken = (token: string) => window.sessionStorage.setItem("smart_wardrobe_access_token", token);
export const clearAccessToken = () => window.sessionStorage.removeItem("smart_wardrobe_access_token");
export const getAccessToken = () => typeof window === "undefined" ? null : window.sessionStorage.getItem("smart_wardrobe_access_token");
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
