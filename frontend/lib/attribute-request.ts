export const attributeRequestVersion = "attribute-conditions-1.0.0" as const;
export const attributeDraftVersion = "assistant-attribute-draft-1.0.0" as const;
export type AttributeField = "verified_subtype" | "garment_name" | "category" | "primary_colour" | "secondary_colour" | "palette_colour" | "palette_coverage" | "style" | "pattern" | "material" | "silhouette" | "neckline" | "sleeve_length" | "colour_temperature" | "colour_dominance" | "descriptive_tag" | "condition" | "construction_collared" | "construction_structured" | "construction_tailored";
export type AttributeOperator = "in" | "contains_any" | "contains_all" | "exact_text" | "exact_hex" | "coverage_ge" | "bool_eq";
export type AttributeRole = "all_selected" | "base" | "upper" | "lower" | "one_piece" | "outerwear" | "base_upper_body";
export type AttributeQuantifier = "exists" | "all_present" | "none";
export type AttributeValue = string | boolean | { colour: string; minimum: string };
export type AttributeCondition = { id: string; attribute: AttributeField; operator: AttributeOperator; values: AttributeValue[] };
export type AttributeGroup = { id: string; role: AttributeRole; quantifier: AttributeQuantifier; conditions: AttributeCondition[] };
export type AttributeConditions = { version: typeof attributeRequestVersion | "attribute-conditions-2.0.0"; groups: AttributeGroup[] };
export type AttributeCapability = { version: "attribute-request-capabilities-1.0.0"; enabled: boolean; request_version: string; grammar_version: string | null; grammar_sha256: string | null; policy_version: string | null; policy_sha256: string | null; fields: { attribute: AttributeField; operators: AttributeOperator[]; values: AttributeValue[]; dynamic_domain: boolean; source_requirements: string; default_role: AttributeRole; default_quantifier: AttributeQuantifier }[]; roles: AttributeRole[]; quantifiers: AttributeQuantifier[]; bounds: Record<string, number>; blocked_sources: string[] };
export type AttributeSpan = { condition_id: string; source: "nlp" | "typed"; start: number | null; end: number | null; text: string | null };
export type AttributeDisplay = { version: "assistant-attribute-display-1.0.0"; intent_sha256: string; wearer_profile_id: string; outcome: string; source_limitations: string[]; groups: { id: string; role: AttributeRole; quantifier: AttributeQuantifier; state: "Pass" | "Fail" | "Unknown"; conditions: (AttributeCondition & { state: string; reason_codes: string[]; spans: AttributeSpan[] })[]; member_results: { garment_id: string; role: string; condition_id: string; state: string; source_kind: string; source_revision: string | null; reason_codes: string[] }[] }[] };

export const attributeLabels: Record<AttributeField, string> = {
  verified_subtype: "Verified garment type", garment_name: "Garment name", category: "Garment category", primary_colour: "Main colour", secondary_colour: "Secondary colour", palette_colour: "Palette colour", palette_coverage: "Palette coverage", style: "Style", pattern: "Pattern", material: "Material label", silhouette: "Silhouette", neckline: "Neckline", sleeve_length: "Sleeve length", colour_temperature: "Colour temperature", colour_dominance: "Dominant colour observation", descriptive_tag: "Literal descriptive tag", condition: "Reviewed condition", construction_collared: "Reviewed collar observation", construction_structured: "Reviewed structure observation", construction_tailored: "Reviewed tailoring observation",
};
export const roleLabels: Record<AttributeRole, string> = { all_selected: "Whole outfit", base: "Base garments", upper: "Top", lower: "Bottom", one_piece: "Dress", outerwear: "Outerwear", base_upper_body: "Top or dress" };
export const quantifierLabels: Record<AttributeQuantifier, string> = { exists: "At least one garment", all_present: "Every selected garment in this scope", none: "Exclude any garment with all these features" };
export const operatorLabels: Record<AttributeOperator, string> = { in: "Any selected value", contains_any: "Contains any selected value", contains_all: "Contains every selected value", exact_text: "Exactly this text", exact_hex: "Exactly this colour hex", coverage_ge: "Coverage at least", bool_eq: "Recorded observation is" };
export const codePointCount = (value: string) => Array.from(value).length;
export const codePointSlice = (value: string, start: number, end: number) => Array.from(value).slice(start, end).join("");
const exact = (value: unknown, keys: string[]): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => key in value);
const own = (value: object, key: string) => Object.prototype.hasOwnProperty.call(value, key);
const reserved = /^(rec:|owner_style_|saved_attribute_|garment_description_|contextual_suitability_|appearance_evidence_|automatic_|neckline:|sleeve length:|silhouette:)/i;
const decimal = /^(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?)$/;
const hex = /^#[0-9a-f]{6}$/;
const namedPalette = new Set(["black", "white", "grey", "navy", "blue", "red", "green", "yellow", "orange", "pink", "purple", "brown", "beige"]);
const operators: Record<AttributeOperator, readonly AttributeField[]> = {
  in: ["verified_subtype", "category", "primary_colour", "secondary_colour", "pattern", "silhouette", "neckline", "sleeve_length", "colour_temperature", "condition"], contains_any: ["style", "material", "palette_colour", "descriptive_tag"], contains_all: ["style", "material", "palette_colour", "descriptive_tag"], exact_text: ["garment_name", "descriptive_tag"], exact_hex: ["primary_colour", "secondary_colour", "palette_colour"], coverage_ge: ["palette_coverage"], bool_eq: ["colour_dominance", "construction_collared", "construction_structured", "construction_tailored"],
};

export function validAttributeConditions(value: unknown): value is AttributeConditions {
  if (!exact(value, ["version", "groups"]) || ![attributeRequestVersion,"attribute-conditions-2.0.0"].includes(String(value.version)) || !Array.isArray(value.groups) || value.groups.length < 1 || value.groups.length > 8) return false;
  const groupIds = new Set<string>(), conditionIds = new Set<string>(); let total = 0;
  for (const group of value.groups) {
    if (!exact(group, ["id", "role", "quantifier", "conditions"]) || typeof group.id !== "string" || !/^g0[1-8]$/.test(group.id) || groupIds.has(group.id) || typeof group.role !== "string" || !own(roleLabels, group.role) || typeof group.quantifier !== "string" || !own(quantifierLabels, group.quantifier) || !Array.isArray(group.conditions) || !group.conditions.length || group.conditions.length > 16) return false;
    groupIds.add(group.id);
    for (const condition of group.conditions) {
      if (!exact(condition, ["id", "attribute", "operator", "values"]) || typeof condition.id !== "string" || !/^c(?:0[1-9]|1[0-6])$/.test(condition.id) || conditionIds.has(condition.id) || typeof condition.attribute !== "string" || typeof condition.operator !== "string" || !own(operators, condition.operator) || !operators[condition.operator as AttributeOperator].includes(condition.attribute as AttributeField) || !Array.isArray(condition.values) || !condition.values.length || condition.values.length > 20) return false;
      if (condition.attribute === "verified_subtype" && (value.version !== "attribute-conditions-2.0.0" || condition.values.some(v => typeof v !== "string" || !["t_shirt","polo_shirt","button_up_shirt","knit_top","blouse"].includes(v)))) return false;
      conditionIds.add(condition.id); total += condition.values.length;
      if (["exact_text", "exact_hex", "coverage_ge", "bool_eq"].includes(condition.operator) && condition.values.length !== 1) return false;
      if (new Set(condition.values.map(item => JSON.stringify(item))).size !== condition.values.length) return false;
      for (const item of condition.values) {
        if (condition.operator === "bool_eq") { if (typeof item !== "boolean") return false; continue; }
        if (condition.operator === "coverage_ge") {
          if (!exact(item, ["colour", "minimum"]) || typeof item.colour !== "string" || (!hex.test(item.colour) && !namedPalette.has(item.colour)) || typeof item.minimum !== "string" || !decimal.test(item.minimum)) return false;
          continue;
        }
        if (typeof item !== "string" || !item.trim() || codePointCount(item) > 100 || item.normalize("NFC") !== item) return false;
        if (condition.operator === "exact_hex" && !hex.test(item)) return false;
        if (condition.attribute === "descriptive_tag" && reserved.test(item)) return false;
      }
    }
  }
  return conditionIds.size <= 16 && total <= 64 && new TextEncoder().encode(JSON.stringify(value)).length <= 32768;
}

export function copyAttributeConditions(value: AttributeConditions | undefined): AttributeConditions | undefined {
  return value ? JSON.parse(JSON.stringify(value)) as AttributeConditions : undefined;
}

export function storedTypedAttributes(record: { provenance: Record<string, unknown> | null }): AttributeConditions | undefined {
  const selection = record.provenance?.attribute_selection;
  if (!selection || typeof selection !== "object" || !("version" in selection) || !["attribute-selection-evidence-1.0.0","attribute-selection-evidence-2.0.0"].includes(String(selection.version)) || !("intent" in selection) || !selection.intent || typeof selection.intent !== "object" || !("version" in selection.intent) || !["assistant-attribute-intent-1.0.0","assistant-attribute-intent-2.0.0"].includes(String(selection.intent.version)) || !("typed_input" in selection.intent)) return undefined;
  if (selection.intent.typed_input === null) return undefined;
  if (!validAttributeConditions(selection.intent.typed_input)) throw new Error("Stored requirements could not be restored. Start a new request.");
  return copyAttributeConditions(selection.intent.typed_input);
}

export function describeAttributeValue(value: AttributeValue): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") return value;
  return `${value.colour} ≥ ${value.minimum}`;
}

export function stableAttributeText(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableAttributeText).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${stableAttributeText(item)}`).join(",")}}`;
  return JSON.stringify(value) ?? "null";
}
