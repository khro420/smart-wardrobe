export type SubtypeEntry = { id: string; label: string; parents: string[]; definition: string };
export type SubtypeRegistry = { contract: string; entries: SubtypeEntry[]; applies_to_parents: string[] };
export type VerifiedSubtypeView = { version: string; subject_id: string; category: string; state: string; value: string | null; revision: string | null; registry: SubtypeRegistry; events: { recorded_at: string; state: string; subtype: string | null; reason: string }[] };
export type SubtypeUpdate = { action_id: string; expected_revision: string | null; state: "Known" | "Unspecified" | "Inapplicable"; value: string | null; review_basis: "owner_review" | "synthetic_fixture_declaration"; reason: string };
export const subtypeLabel = (value: string) => (({ t_shirt: "T-shirt", polo_shirt: "Polo shirt", blouse: "Blouse", button_up_shirt: "Button-up shirt", knit_top: "Knit / sweater top" } as Record<string,string>)[value] ?? value.replaceAll("_", " "));
export function capturedSubtypeSummaries(provenance: Record<string, unknown> | null) {
  const raw = provenance?.wearer_category_eligibility;
  if (!raw || typeof raw !== "object" || !("version" in raw) || raw.version !== "wearer-category-eligibility-evidence-2.0.0" || !("subtype_sources" in raw) || !Array.isArray(raw.subtype_sources)) return [];
  return raw.subtype_sources.flatMap((source: unknown) => {
    if (!source || typeof source !== "object" || !("subject_id" in source) || typeof source.subject_id !== "string" || !("state" in source) || typeof source.state !== "string" || !("value" in source)) return [];
    return [{ garment_id: source.subject_id, label: source.state === "Known" && typeof source.value === "string" ? subtypeLabel(source.value) : source.state === "Inapplicable" ? "Not required for this category" : "Unknown", state: source.state }];
  });
}
export function subtypeSummary(view: VerifiedSubtypeView | undefined) {
  return view?.state === "Known" ? view.registry.entries.find(e => e.id === view.value)?.label ?? "Unknown" : view?.state === "Inapplicable" ? "Not required for this category" : `Unknown${view ? ` (${view.state})` : ""}`;
}

// A verified subtype is deliberately narrower than the stored garment category.
// Show it only when it provides a confirmed, more-specific type; otherwise the
// already-established category is the truthful garment type to show on a card.
export const garmentTypeSummary = (category: string, view: VerifiedSubtypeView | undefined) =>
  view?.state === "Known" ? subtypeSummary(view) : category.replaceAll("_", " ");
