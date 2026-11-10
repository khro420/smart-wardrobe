import { authenticationSession } from "./wearer-selection";

export type PreferenceValue = string | boolean | { colour: string; minimum: string };
export type PreferenceAxis = { scope: string; importance: string; liked: PreferenceValue[]; avoided: PreferenceValue[] };
export type PreferenceFamily = { mode: "inherit_p1" | "disabled" } | { mode: "override"; importance: string; axes: Record<string, PreferenceAxis> };
export type PreferenceFamilies = Record<string, PreferenceFamily>;
export type AttributePreferenceView = { contract: string; wearer_id: string; revision: string; document: { contract: string; families: PreferenceFamilies } | null; effective: Record<string, { importance: string; mode: string }>; legacy_digest: string; policy: string };
export type AttributePreferenceCapability = { enabled: boolean; profile?: string; families?: string[]; axes?: { axis: string; family: string; default_scope: string; aggregation: string }[]; values?: { axis: string; value: PreferenceValue; status: string; blocker: string | null }[] };
export type PreferenceSaveAction = { contract: "attribute-preferences-update-1.0.0"; wearer_id: string; action_id: string; expected_revision: string; families: PreferenceFamilies };
export const P2_PROFILE = "attribute_preference_decision_v2";
export const FAMILY_LABELS: Record<string, string> = { colour: "Colour", styles: "Styles", garment_categories: "Garment categories", formality: "Formality", pattern: "Pattern", material: "Material", silhouette: "Visible silhouette", neckline: "Neckline", sleeve_length: "Sleeve length", descriptive_tag: "Descriptive tags" };
export const AXIS_LABELS: Record<string, string> = { primary_colour: "Primary colour", secondary_colour: "Secondary colour", palette_colour: "Colour in the image palette", palette_coverage: "Image colour coverage", colour_temperature: "Colour temperature", colour_dominance: "One dominant colour", style: "Style", category: "Garment category", formality: "Formality", pattern: "Pattern", material: "Material", silhouette: "Visible silhouette", neckline: "Neckline", sleeve_length: "Sleeve length", descriptive_tag: "Descriptive tags" };
export const SCOPES: Record<string, string> = { all_selected: "Whole outfit", base: "Main outfit", base_upper_body: "Main upper body", upper: "Top", lower: "Bottom", one_piece: "One piece", outerwear: "Outer layer" };
export const isInheritedFamily = (family: string) => ["colour", "styles", "garment_categories", "formality"].includes(family);
export const preferenceDraftKey = (wearer: string, session = authenticationSession()) => `smart_wardrobe_interaction:p2settings:${session}:${wearer}`;
export const copyFamilies = (value: PreferenceFamilies): PreferenceFamilies => JSON.parse(JSON.stringify(value));
export const valueKey = (v: PreferenceValue) => typeof v === "object" ? `${v.colour}:${v.minimum}` : `${typeof v}:${v}`;

export function togglePreference(axis: PreferenceAxis, value: PreferenceValue, polarity: "liked" | "avoided"): PreferenceAxis {
  const key = valueKey(value), other = polarity === "liked" ? "avoided" : "liked";
  return { ...axis, [polarity]: axis[polarity].some(v => valueKey(v) === key) ? axis[polarity].filter(v => valueKey(v) !== key) : [...axis[polarity], value], [other]: axis[other].filter(v => valueKey(v) !== key) };
}

export function percentageMinimum(text: string): string {
  if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,4})?$/.test(text)) throw new Error("Enter a percentage from 0 to 100, up to four decimal places.");
  const [whole, part = ""] = text.split(".");
  const ticks = BigInt(whole) * BigInt(10000) + BigInt(part.padEnd(4, "0"));
  if (ticks > BigInt(1000000)) throw new Error("Coverage cannot exceed 100%.");
  if (ticks === BigInt(1000000)) return "1";
  return `0.${ticks.toString().padStart(6, "0")}`.replace(/0+$/, "").replace(/\.$/, "") || "0";
}
