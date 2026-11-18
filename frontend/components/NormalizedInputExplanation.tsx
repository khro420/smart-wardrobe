import type { NormalizedInputDisplay } from "@/lib/api";
import {attributeLabels,roleLabels,quantifierLabels,describeAttributeValue} from "@/lib/attribute-request";

export default function NormalizedInputExplanation({value}:{value:NormalizedInputDisplay | undefined}) {
  if(value?.version!=="normalized-input-display-1.0.0" && value?.version!=="compositional-input-display-1.0.0") return null;
  return <details className="rounded-xl border border-slate-200 p-3 text-sm" aria-label="Input interpretation">
    <summary className="cursor-pointer font-semibold">Input interpretation</summary>
    <p>Understood as: {value.normalized_text}</p>
    <p>Your original request is kept unchanged in history.</p>
    {value.hard_conditions?.groups.map(group=><p key={group.id}>
      Required: {quantifierLabels[group.quantifier]} · {roleLabels[group.role]} · same garment: {group.conditions.map(c=>`${attributeLabels[c.attribute]}: ${c.values.map(describeAttributeValue).join(c.operator==="contains_all"?" and ":" or ")}`).join("; ")}.
    </p>)}
  </details>;
}
