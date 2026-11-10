import { subtypeLabel } from "@/lib/verified-subtypes";
import { attributeLabels, roleLabels, quantifierLabels, describeAttributeValue, type AttributeDisplay, type AttributeConditions } from "@/lib/attribute-request";

export function CapturedAttributeRequirements({ value }: { value: AttributeConditions | undefined }) {
  if (!value) return null;
  return <details className="min-w-0 rounded-xl border border-slate-200 p-3 text-sm [overflow-wrap:anywhere]">
    <summary className="min-h-11 cursor-pointer font-semibold">Captured typed requirements</summary>
    <p>These requirements are part of this request and are kept on retry.</p>
    {value.groups.map(group => <p key={group.id} className="mt-2">{quantifierLabels[group.quantifier]} · {roleLabels[group.role]} · same garment: {group.conditions.map(c => `${attributeLabels[c.attribute]}: ${c.values.map(v => c.attribute === "verified_subtype" && typeof v === "string" ? subtypeLabel(v) : describeAttributeValue(v)).join(c.operator === "contains_all" ? " and " : " or ")}`).join("; ")}.</p>)}
  </details>;
}

export default function AttributeRequirements({ value }: { value: AttributeDisplay | undefined }) {
  if (!value || value.version !== "assistant-attribute-display-1.0.0") return null;
  return <section aria-label="Matched garment requirements" className="min-w-0 space-y-3 rounded-xl bg-slate-50 p-3 text-sm [overflow-wrap:anywhere]">
    <h3 className="font-semibold">Matched garment requirements</h3>
    <p>Every rule below applies alongside the situation and wardrobe restrictions. A verified garment type requires an owner-confirmed record; other descriptive requirements still need their own evidence.</p>
    {value.groups.map(group => <div key={group.id} className="min-w-0 space-y-1">
      <p className="font-semibold">{quantifierLabels[group.quantifier]} · {roleLabels[group.role]}</p>
      <p>Same garment: {group.conditions.map(c => `${attributeLabels[c.attribute]}: ${c.values.map(v => c.attribute === "verified_subtype" && typeof v === "string" ? subtypeLabel(v) : describeAttributeValue(v)).join(c.operator === "contains_all" ? " and " : " or ")}`).join("; ")}.</p>
      <p>{group.quantifier === "none" ? "The forbidden combination was excluded." : "The combined rule was established from recorded descriptions."}</p>
      {group.member_results.some(m => m.source_kind === "dated_reviewed_observation") && <p>Construction and condition are dated owner observations, rather than a new inspection.</p>}
    </div>)}
    {value.source_limitations.map(text => <p key={text}>{text}</p>)}
  </section>;
}
