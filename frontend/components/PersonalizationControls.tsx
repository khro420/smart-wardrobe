"use client";
import { useEffect,useState } from "react";
import { getOutfitFeedback,saveOutfitFeedback,type PersonalizationDisplay } from "../lib/api";

export default function PersonalizationControls({value,recommendationId,wearerId}:{value?:PersonalizationDisplay;recommendationId:string;wearerId?:string|null}) {
  const [verdict,setVerdict]=useState<string|null>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  useEffect(()=>{let current=true;if(value&&wearerId)void getOutfitFeedback(recommendationId,wearerId).then(r=>{if(current)setVerdict(r.verdict);}).catch(()=>{if(current)setMessage("Feedback is unavailable; no preference was changed.");});return()=>{current=false;};},[recommendationId,wearerId,value]);
  if(!value||!wearerId)return null;
  async function save(choice:"like"|"dislike"|"clear") {
    if(busy||!wearerId)return;setBusy(true);setMessage("");
    try {const r=await saveOutfitFeedback(recommendationId,wearerId,choice);setVerdict(r.verdict);setMessage("Explicit feedback saved for this wearer's exact base outfit. Existing results are unchanged.");}
    catch {setMessage("Feedback could not be saved. No success is assumed; try again.");} finally {setBusy(false);}
  }
  return <section aria-label="Personalization and variety" className="rounded-xl border border-slate-200 p-3 text-sm">
    <strong>Personalization and variety</strong>
    <p>Recorded clothing preferences contribute to P. Variety and explicit feedback only reorder outfits with identical R, C, P and total scores. No hard requirement is relaxed.</p>
    <p>{value.reason==="request_policy_unchanged"?"Request-local preferences and continuation ordering are unchanged.":`Compared ${value.eligible_ties} exact-score ties; ${value.applied?"a less repeated or explicitly preferred base was selected":"the existing winner was retained"}.`}</p>
    <p>Like or dislike applies only to this exact base outfit, not every garment, colour or style. Viewing, saving and “Suggest another outfit” never imply dislike. Feedback affects future new chats, not this result or its continuation. A disliked outfit can still win if no equally scored alternative exists.</p>
    <p>Variety uses the last 10 completed recommendations for this wearer. The newest 20 explicit base-outfit feedback choices are retained; older choices fall outside this bounded profile.</p>
    <div className="flex flex-wrap gap-2"><button type="button" disabled={busy} aria-pressed={verdict==="like"} onClick={()=>void save("like")} className="border px-3 py-2">Like this outfit</button><button type="button" disabled={busy} aria-pressed={verdict==="dislike"} onClick={()=>void save("dislike")} className="border px-3 py-2">Dislike this outfit</button><button type="button" disabled={busy} onClick={()=>void save("clear")} className="border px-3 py-2">Clear feedback</button></div>
    {message&&<p role="status">{message}</p>}
    <a href="/profile" className="underline">Edit clothing preferences for the selected wearer</a>
  </section>;
}
