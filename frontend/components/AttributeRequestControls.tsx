"use client";
import { useRef, useState } from "react";
import { attributeRequestVersion, attributeLabels, roleLabels, quantifierLabels, operatorLabels, describeAttributeValue, copyAttributeConditions, stableAttributeText, validAttributeConditions, type AttributeCapability, type AttributeConditions, type AttributeGroup, type AttributeCondition, type AttributeField, type AttributeOperator, type AttributeRole, type AttributeQuantifier, type AttributeValue } from "@/lib/attribute-request";

type Props = { capability: AttributeCapability; value?: AttributeConditions; disabled: boolean; submitted: boolean; allowedCategories?: string[]; onApply: (value: AttributeConditions | undefined) => void };
const control = "min-h-11 min-w-0 w-full rounded-lg border border-slate-300 bg-white p-2";

export default function AttributeRequestControls({ capability, value, disabled, submitted, allowedCategories, onApply }: Props) {
  const [editing, setEditing] = useState(false);
  const [groups, setGroups] = useState<AttributeGroup[]>(() => copyAttributeConditions(value)?.groups ?? []);
  const [error, setError] = useState("");
  const details = useRef<HTMLDetailsElement>(null);
  if (capability.version !== "attribute-request-capabilities-1.0.0" || !capability.enabled) return null;
  const count = groups.reduce((sum, group) => sum + group.conditions.length, 0);
  const begin = () => { setGroups(copyAttributeConditions(value)?.groups ?? []); setEditing(true); setError(""); };
  const cancel = () => { setEditing(false); setError(""); if (details.current) details.current.open = false; };
  const blank = (): AttributeCondition => {
    const field = capability.fields.find(item => item.attribute === "pattern") ?? capability.fields[0];
    return { id: "c01", attribute: field.attribute, operator: field.operators[0], values: [] };
  };
  const update = (gi: number, ci: number, changes: Partial<AttributeCondition>) => setGroups(current => current.map((group, index) => index === gi ? { ...group, conditions: group.conditions.map((condition, i) => i === ci ? { ...condition, ...changes } : condition) } : group));
  const changeValue = (gi: number, ci: number, index: number, next: AttributeValue) => {
    const values = [...groups[gi].conditions[ci].values]; values[index] = next; update(gi, ci, { values });
  };
  const apply = () => {
    let index = 0;
    const next: AttributeConditions | undefined = groups.length ? { version: groups.some(g => g.conditions.some(c => c.attribute === "verified_subtype")) ? "attribute-conditions-2.0.0" : attributeRequestVersion, groups: groups.map((group, gi) => ({ ...group, id: `g${String(gi + 1).padStart(2, "0")}`, conditions: group.conditions.map(condition => ({ ...condition, id: `c${String(++index).padStart(2, "0")}`, values: condition.values.map(item => typeof item === "string" ? item.normalize("NFC") : item).sort((a, b) => stableAttributeText(a).localeCompare(stableAttributeText(b))) })) })) } : undefined;
    if (next && !validAttributeConditions(next)) { setError("Choose a supported value for every feature. Use at most 16 features, 20 values per feature and 64 values in total; keep text values within 100 characters."); return; }
    if (allowedCategories && next?.groups.some(g => g.quantifier !== 'none' && g.conditions.some(c => c.attribute === 'category' && !c.values.some(v => typeof v === 'string' && allowedCategories.includes(v))))) { setError('This category is not permitted for the selected wearer. Your draft is retained; change the requirement or select another wearer.'); return; }
    if (stableAttributeText(next) !== stableAttributeText(value)) onApply(next);
    setEditing(false); setError(""); if (details.current) details.current.open = false;
  };
  return <details ref={details} className="min-w-0 space-y-3 rounded-xl border border-slate-200 bg-white p-4 text-sm [overflow-wrap:anywhere]">
    <summary className="min-h-11 cursor-pointer font-semibold">Optional garment requirements</summary>
    <p>These controls add to your written request. All features within one rule must describe the same garment. Missing descriptions cannot prove a match.</p>
    {submitted && <p>Your submitted requirements stay unchanged. Applying edits starts a new request.</p>}
    {!editing ? <><p>{value ? `${value.groups.length} garment rule${value.groups.length === 1 ? "" : "s"} applied.` : "No additional typed requirements."}</p><button type="button" disabled={disabled} onClick={begin} className="min-h-11 font-semibold underline">Edit garment requirements</button></> : <fieldset disabled={disabled} className="min-w-0 space-y-4">
      <legend className="font-semibold">Garment requirements</legend>
      {groups.map((group, gi) => <fieldset key={gi} className="min-w-0 space-y-3 rounded-xl border border-slate-200 p-3">
        <legend className="px-1 font-semibold">Rule {gi + 1} · same garment</legend>
        <div className="grid min-w-0 gap-3 sm:grid-cols-2">
          <label className="min-w-0">Garment scope<select aria-label={`Garment scope for rule ${gi + 1}`} className={control} value={group.role} onChange={e => setGroups(current => current.map((g, i) => i === gi ? { ...g, role: e.target.value as AttributeRole } : g))}>{capability.roles.map(role => <option key={role} value={role}>{roleLabels[role]}</option>)}</select></label>
          <label className="min-w-0">Requirement<select aria-label={`Requirement for rule ${gi + 1}`} className={control} value={group.quantifier} onChange={e => setGroups(current => current.map((g, i) => i === gi ? { ...g, quantifier: e.target.value as AttributeQuantifier } : g))}>{capability.quantifiers.map(q => <option key={q} value={q}>{quantifierLabels[q]}</option>)}</select></label>
        </div>
        {group.conditions.map((condition, ci) => {
          const field = capability.fields.find(item => item.attribute === condition.attribute);
          if (!field) return <p key={ci} role="alert">This stored feature is unavailable. Start a new request to change it.</p>;
          const options = field.values.filter(v => typeof v === "string" && !v.startsWith("#") && (condition.attribute !== "category" || group.quantifier === "none" || !allowedCategories || allowedCategories.includes(v) || condition.values.includes(v)));
          const literal = condition.operator === "exact_text" || condition.attribute === "descriptive_tag";
          return <div key={ci} className="min-w-0 space-y-3 border-t border-slate-200 pt-3">
            <div className="grid min-w-0 gap-3 sm:grid-cols-2">
              <label className="min-w-0">Feature<select aria-label={`Feature ${ci + 1} in rule ${gi + 1}`} className={control} value={condition.attribute} onChange={e => { const selected = capability.fields.find(item => item.attribute === e.target.value)!; update(gi, ci, { attribute: selected.attribute as AttributeField, operator: selected.operators[0], values: [] }); }}>{capability.fields.map(item => <option key={item.attribute} value={item.attribute}>{attributeLabels[item.attribute]}</option>)}</select></label>
              <label className="min-w-0">Match<select aria-label={`Match ${ci + 1} in rule ${gi + 1}`} className={control} value={condition.operator} onChange={e => update(gi, ci, { operator: e.target.value as AttributeOperator, values: [] })}>{field.operators.map(op => <option key={op} value={op}>{operatorLabels[op]}</option>)}</select></label>
            </div>
            {condition.operator === "bool_eq" ? <label>Observation<select aria-label={`Observation ${ci + 1} in rule ${gi + 1}`} className={control} value={condition.values.length ? String(condition.values[0]) : ""} onChange={e => update(gi, ci, { values: e.target.value === "" ? [] : [e.target.value === "true"] })}><option value="">Choose an observation</option><option value="true">Yes</option><option value="false">No</option></select></label>
              : condition.operator === "coverage_ge" ? <div className="grid min-w-0 gap-3 sm:grid-cols-2">{(() => {
                const entry = condition.values[0]; const threshold = entry && typeof entry === "object" ? entry : { colour: "", minimum: "" };
                return <><label>Palette colour or exact hex<input aria-label={`Palette colour ${ci + 1} in rule ${gi + 1}`} className={control} value={threshold.colour} onChange={e => update(gi, ci, { values: [{ ...threshold, colour: e.target.value.toLowerCase() }] })} placeholder="blue or #123abc" /></label><label>Minimum recorded fraction<input aria-label={`Minimum coverage ${ci + 1} in rule ${gi + 1}`} inputMode="decimal" className={control} value={threshold.minimum} onChange={e => update(gi, ci, { values: [{ ...threshold, minimum: e.target.value }] })} placeholder="0.500000" /></label></>;
              })()}</div>
              : condition.operator === "exact_hex" ? <label>Exact colour hex<input aria-label={`Exact hex ${ci + 1} in rule ${gi + 1}`} className={control} value={String(condition.values[0] ?? "")} onChange={e => update(gi, ci, { values: [e.target.value.toLowerCase()] })} placeholder="#123abc" /></label>
              : literal ? <div className="space-y-2">{(condition.values.length ? condition.values : [""]).map((entry, vi) => <label key={vi} className="block">Exact text {vi + 1}<input aria-label={`Exact text ${vi + 1} for feature ${ci + 1} in rule ${gi + 1}`} className={control} value={String(entry)} onChange={e => changeValue(gi, ci, vi, e.target.value)} /></label>)}{condition.operator !== "exact_text" && <button type="button" disabled={condition.values.length >= 20} onClick={() => update(gi, ci, { values: [...(condition.values.length ? condition.values : [""]), ""] })} className="min-h-11 underline">Add another literal value</button>}</div>
              : <label className="block">Supported values<select aria-label={`Values ${ci + 1} in rule ${gi + 1}`} multiple className={`${control} min-h-32`} value={condition.values.filter(v => typeof v === "string") as string[]} onChange={e => update(gi, ci, { values: Array.from(e.target.selectedOptions, option => option.value) })}>{options.map(v => <option key={String(v)} value={String(v)} disabled={condition.attribute === "category" && group.quantifier !== "none" && !!allowedCategories && !allowedCategories.includes(String(v))}>{condition.attribute === "category" || condition.attribute === "condition" ? String(v).replaceAll("_", " ").replace("outwear", "outerwear") : describeAttributeValue(v)}</option>)}</select></label>}
            <button type="button" className="min-h-11 underline" onClick={() => setGroups(current => current.flatMap((g, i) => i !== gi ? [g] : g.conditions.length === 1 ? [] : [{ ...g, conditions: g.conditions.filter((_, index) => index !== ci) }]))}>Remove feature {ci + 1}</button>
          </div>;
        })}
        <button type="button" disabled={count >= 16} className="min-h-11 underline" onClick={() => setGroups(current => current.map((g, i) => i === gi ? { ...g, conditions: [...g.conditions, blank()] } : g))}>Add a feature to this same garment</button>
      </fieldset>)}
      <button type="button" disabled={groups.length >= 8 || count >= 16 || !capability.fields.length} className="min-h-11 rounded-lg border px-3" onClick={() => { const condition = blank(); setGroups(current => [...current, { id: "g01", role: capability.fields.find(f => f.attribute === condition.attribute)!.default_role, quantifier: "exists", conditions: [condition] }]); }}>Add another garment rule</button>
      {error && <p role="alert" className="text-amber-900">{error}</p>}
      <div className="flex flex-wrap gap-3"><button type="button" onClick={apply} className="min-h-11 rounded-lg bg-[#6d335b] px-4 font-semibold text-white">{submitted ? "Apply as a new request" : "Apply garment requirements"}</button><button type="button" onClick={cancel} className="min-h-11 underline">Cancel garment changes</button><button type="button" onClick={() => setGroups([])} className="min-h-11 underline">Clear typed requirements</button></div>
    </fieldset>}
  </details>;
}
