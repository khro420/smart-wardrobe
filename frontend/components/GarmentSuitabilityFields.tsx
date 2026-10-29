"use client";

import type { GarmentTagEdit } from "@/lib/api";
export type SuitabilityChoice = "unknown" | "allow" | "deny";
export const declarationKey = (field: string, value: string) => `${field}:${value}`;

export default function GarmentSuitabilityFields({ view, choices, removed, onChoice, onRemove }: {
  view: GarmentTagEdit; choices: Record<string, SuitabilityChoice>; removed: number[];
  onChoice: (key: string, choice: SuitabilityChoice) => void; onRemove: (index: number) => void;
}) {
  return <fieldset className="col-span-2 space-y-3 border-2 border-zinc-300 p-3" disabled={!view.editable}>
    <legend className="px-1 text-sm font-bold">Owner-declared suitability</legend>
    <p className="text-xs text-zinc-600">These are your declarations, not independently verified appropriateness. Nothing is inferred from style or AI output. Review them after material garment changes. There is no separate annotation-review provenance.</p>
    {!view.editable && <p role="alert" className="text-xs text-rose-700">Stored tag data is invalid. Suitability editing is unavailable until the record is explicitly repaired.</p>}
    <div className="grid grid-cols-2 gap-2">{view.declarations.map(item => {
      const key=declarationKey(item.field,item.value);
      const label=`${item.field === "occasion" ? "Occasion" : "Formality"}: ${item.label}`;
      return <div key={key} className="space-y-1">
        <label className="block text-xs font-bold">{label}<select aria-label={label} value={choices[key] ?? item.choice} onChange={event=>onChoice(key,event.target.value as SuitabilityChoice)} className="mt-1 w-full border-2 border-black bg-white p-2 text-sm"><option value="unknown">Unknown</option><option value="allow">Allow</option><option value="deny">Deny</option></select></label>
        {item.conflict && <p className="text-xs text-rose-700">Saved Allow and Deny conflict. Evidence remains Unknown. Choose a decision to correct it, or <button type="button" onClick={()=>onChoice(key,"unknown")} className="underline" aria-label={`Clear conflict for ${label}`}>clear this conflict</button>.</p>}
        {item.malformed && <p className="text-xs text-rose-700">Unrecognised annotations affect this field. Its evidence remains Unknown until explicitly corrected.</p>}
      </div>;
    })}</div>
    {view.malformed.length > 0 && <div className="space-y-2 text-xs text-rose-700"><p>Unrecognised saved suitability annotations are preserved. Selecting a decision does not repair them automatically.</p>{view.malformed.map((item,index)=><div key={item.index}><span>Unrecognised annotation {index+1} affects {item.fields.join(" and ")}. </span><button type="button" disabled={removed.includes(item.index)} onClick={()=>onRemove(item.index)} className="underline">{removed.includes(item.index) ? `Annotation ${index+1} removal pending` : `Remove unrecognised annotation ${index+1}`}</button></div>)}</div>}
    <p className="text-xs text-zinc-600">Unknown removes only the selected value&apos;s valid declaration pair. Other declarations and ordinary tags are preserved. Exercise and formal suitability are unavailable. Recommendation suitability evaluation remains off by default.</p>
  </fieldset>;
}
