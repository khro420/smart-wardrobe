"use client";
import {useEffect,useState} from "react";
import OutfitInventoryEditor from "./OutfitInventoryEditor";
import OutfitReviewResult from "./OutfitReviewResult";
import {correctionChanges,jsonAction,reviewPhoto,reviewRequest,type Prediction,type ReviewView} from "@/lib/outfit-review";
const button="min-h-11 rounded-xl bg-[#6d335b] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#552646] disabled:opacity-40";
const secondary="min-h-11 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium disabled:opacity-40";
const clone=<T,>(v:T):T=>JSON.parse(JSON.stringify(v));

export default function OutfitReviewExperience(){
  const [cap,setCap]=useState<{enabled:boolean;assets_present:boolean;ai_feedback?:boolean}|null>(null);
  const [view,setView]=useState<ReviewView|null>(null),[draft,setDraft]=useState<Prediction|null>(null),[target,setTarget]=useState<string|null>(null);
  const [photo,setPhoto]=useState<string|null>(null),[file,setFile]=useState<File|null>(null),[occasion,setOccasion]=useState("");
  const [error,setError]=useState(""),[busy,setBusy]=useState(false),[gpu,setGpu]=useState(false),[feedbackGpu,setFeedbackGpu]=useState(false),[reviewed,setReviewed]=useState(false);
  const active=view?.state==="analyzing"||view?.state==="reviewing";
  const dirty=!!draft&&!!view?.prediction&&(JSON.stringify(draft)!==JSON.stringify(view.prediction)||target!==null);
  const update=(next:ReviewView)=>{setView(next);setDraft(next.prediction?clone(next.prediction):null);setTarget(null);setReviewed(false);};
  const act=async(fn:()=>Promise<void>)=>{setError("");setBusy(true);try{await fn();}catch(e){setError(e instanceof Error?e.message:"Please try again.");}finally{setBusy(false);}};
  useEffect(()=>{let cancelled=false;reviewRequest<{enabled:boolean;assets_present:boolean;ai_feedback?:boolean}>("/capabilities").then(v=>{if(!cancelled)setCap(v);}).catch(e=>{if(!cancelled)setError(e.message);});return()=>{cancelled=true;};},[]);
  useEffect(()=>{
    if(!view?.id)return;const controller=new AbortController();let url:string|undefined;
    reviewPhoto(view.id,controller.signal).then(blob=>{url=URL.createObjectURL(blob);if(!controller.signal.aborted)setPhoto(url);}).catch(()=>{if(!controller.signal.aborted)setError("The temporary photo could not be loaded. It may have expired.");});
    return()=>{controller.abort();if(url)URL.revokeObjectURL(url);setPhoto(null);};
  },[view?.id]);
  useEffect(()=>{
    if(!view?.id||!active)return;let cancelled=false,timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{try{const next=await reviewRequest<ReviewView>(`/${view.id}`);if(!cancelled){update(next);if(["analyzing","reviewing"].includes(next.state))timer=setTimeout(poll,1200);}}catch(e){if(!cancelled)setError(e instanceof Error?e.message:"The review status could not be checked.");}};
    timer=setTimeout(poll,1200);return()=>{cancelled=true;clearTimeout(timer);};
  },[view?.id,active]);
  const edit=(next:Prediction)=>{setDraft(next);setReviewed(false);};
  const upload=()=>act(async()=>{
    if(!file)throw new Error("Choose an outfit photograph first.");
    if(!["image/jpeg","image/png"].includes(file.type)||file.size>10*1024*1024)throw new Error("Use a JPEG or PNG no larger than 10 MiB.");
    const form=new FormData();form.append("file",file);update(await reviewRequest<ReviewView>("",{method:"POST",body:form}));setGpu(false);
  });
  const save=()=>act(async()=>{
    if(!view?.prediction||!draft||!view.revision)return;
    const reason="User explicitly reviewed and corrected the visible outfit inventory.";
    const changes=correctionChanges(view.prediction,draft,reason,target);
    if(!changes.length)return;
    update(await reviewRequest<ReviewView>(`/${view.id}/inventory`,jsonAction("PATCH",{revision:view.revision,prediction:draft,changes,...(target?{selected_target:target}:{})})));
  });
  const generate=(ai:boolean)=>act(async()=>{
    if(!view)return;
    update(await reviewRequest<ReviewView>(`/${view.id}/review`,jsonAction("POST",{revision:view.revision,occasion,...(ai?{use_ai:true,gpu_available:feedbackGpu}:{})})));
    setFeedbackGpu(false);
  });
  const steps=["Photo","Analyze","Confirm clothing","Occasion","Review"];
  const step=!view?0:!view.prediction?1:!view.confirmed?2:view.state==="completed"?4:3;
  return <div className="mx-auto max-w-6xl space-y-6 pb-10">
    <header><p className="text-sm font-medium uppercase tracking-widest text-[#6d335b]">AURA · Outfit insights</p><h1 className="mt-2 text-3xl font-semibold">AI Outfit Review</h1><p className="mt-2 max-w-2xl text-slate-600">Review the clothing in your photo, confirm the details, then explore occasion-aware feedback.</p></header>
    <ol aria-label="Review steps" className="flex flex-wrap gap-2">{steps.map((label,n)=><li key={label} aria-current={n===step?"step":undefined} className={`rounded-full px-3 py-2 text-sm ${n===step?"bg-[#6d335b] text-white":"bg-white text-slate-500"}`}>{n+1}. {label}</li>)}</ol>
    {error&&<p role="alert" className="rounded-2xl bg-red-50 p-4 text-red-800">{error}</p>}
    {cap&&!cap.enabled&&<p role="status" className="rounded-2xl bg-amber-50 p-4">AI Outfit Review is disabled on this backend. Follow the local setup guide to enable it.</p>}
    {cap?.enabled&&!cap.assets_present&&<p role="status" className="rounded-2xl bg-amber-50 p-4">The approved local vision model is unavailable. Nothing will be downloaded automatically.</p>}
    <section className="space-y-4 rounded-3xl border border-slate-200 bg-white p-5 sm:p-7"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold">Your photograph</h2>{view&&<button className={secondary} disabled={busy||active} onClick={()=>act(async()=>{await reviewRequest(`/${view.id}`,{method:"DELETE"});setView(null);setDraft(null);setPhoto(null);setFile(null);setOccasion("");})}>Delete photo / start again</button>}</div>
      {!view?<><label className="block rounded-2xl border-2 border-dashed border-slate-200 p-6"><span className="block font-medium">Choose an outfit photo</span><span className="mt-1 block text-sm text-slate-500">JPEG or PNG · up to 10 MiB · use a clear photo you have permission to upload</span><input aria-label="Outfit photograph" className="mt-4 max-w-full text-sm" type="file" accept="image/jpeg,image/png" onChange={e=>setFile(e.target.files?.[0]??null)}/></label><button className={button} disabled={!file||busy||!cap?.enabled} onClick={upload}>{busy?"Uploading…":"Upload photo"}</button></>:<p className="text-sm text-slate-500">Private temporary photo · approximately {Math.ceil(view.expires_in_seconds/60)} minutes remaining · not added to your wardrobe</p>}
      {view&&!draft&&photo&&<svg role="img" aria-label="Private outfit photograph" viewBox="0 0 1000 1000" preserveAspectRatio="none" className="max-w-lg rounded-2xl" style={{width:"100%",aspectRatio:`${view.image.width}/${view.image.height}`}}><image href={photo} width="1000" height="1000" preserveAspectRatio="none"/></svg>}
      {view&&(view.state==="uploaded"||view.state==="failed"&&!view.prediction)&&<div className="space-y-3"><label className="flex gap-2 text-sm"><input type="checkbox" checked={gpu} onChange={e=>setGpu(e.target.checked)}/>GPU-intensive games/work are idle and I am ready for local AI analysis.</label><button className={button} disabled={!gpu||busy||active||!cap?.assets_present} onClick={()=>act(async()=>{update(await reviewRequest<ReviewView>(`/${view.id}/analyze`,jsonAction("POST",{gpu_available:gpu})));setGpu(false);})}>Analyze Outfit</button><p className="text-xs text-slate-500">Resource checks run before the model starts. Analysis may take a few minutes.</p></div>}
      {active&&<div role="status" className="rounded-2xl bg-purple-50 p-4"><p className="font-medium">{view?.state==="analyzing"?"Looking at the visible clothing…":"Preparing your grounded outfit assessment…"}</p><p className="mt-1 text-sm text-slate-600">Keep this page open. Long-running requests are checked in the background.</p></div>}
      {view?.error&&<p role="alert" className="rounded-2xl bg-amber-50 p-4">{view.error.message}</p>}
    </section>
    {view&&draft&&view.original_prediction&&<section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-5 sm:p-7"><h2 className="text-xl font-semibold">Review detected clothing</h2><p className="text-sm text-slate-600">AI proposals can be wrong. Correct what is visible, remove false items, and leave uncertain details Unknown.</p><fieldset disabled={busy||active} className="min-w-0 space-y-5 disabled:opacity-60">
      {!!view.normalization?.changes.length&&<p className="rounded-xl bg-slate-50 p-3 text-sm">Repeated identical attribute labels were recorded once. The original AI output is preserved; this does not verify its visual accuracy.</p>}<OutfitInventoryEditor prediction={draft} original={view.original_prediction} photo={photo} width={view.image.width} height={view.image.height} issues={view.issues} onChange={edit} onTarget={setTarget}/>
      <div className="flex flex-wrap items-center gap-3"><button className={secondary} disabled={!dirty} onClick={save}>Save my corrections</button>{dirty&&<p role="status" className="text-sm text-amber-800">Save these corrections before confirming or reviewing.</p>}</div>
      <label className="flex items-start gap-3 rounded-2xl bg-slate-50 p-4 text-sm"><input type="checkbox" className="mt-1" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>I reviewed the person, visible garments, duplicates and layers. Uncertain details stay Unknown.</label>
      <button className={button} disabled={!reviewed||dirty||!!view.issues.length||view.confirmed} onClick={()=>act(async()=>update(await reviewRequest<ReviewView>(`/${view.id}/confirm`,jsonAction("POST",{revision:view.revision,inventory_reviewed:reviewed}))))}>Confirm Outfit Details</button>
      {view.confirmed&&<p role="status" className="text-sm font-medium text-emerald-800">Outfit details confirmed. You can now describe the occasion.</p>}
    </fieldset><details><summary className="cursor-pointer text-xs text-slate-500">Developer details and original AI record</summary><p className="mt-2 text-xs">User corrections are not model-verified accuracy. The original record remains unchanged.</p><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify({original:view.original_prediction,original_model_response:view.original_model_response,normalization:view.normalization,current:draft,issues:view.issues,raw_failed_proposal:view.raw_failed_proposal},null,2)}</pre></details></section>}
    {view?.raw_failed_proposal&&!draft&&<details><summary className="text-sm">Developer details: unvalidated model proposal</summary><pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs">{view.raw_failed_proposal}</pre></details>}
    {view?.confirmed&&<section className="space-y-4 rounded-3xl border border-slate-200 bg-white p-5 sm:p-7"><h2 className="text-xl font-semibold">What is the occasion?</h2><label className="block text-sm font-medium">Occasion or purpose<textarea className="mt-2 block min-h-28 w-full rounded-2xl border border-slate-300 bg-white p-3 font-normal" value={occasion} maxLength={1600} placeholder="I'm going to the library to study." onChange={e=>setOccasion(e.target.value)}/></label><p className="text-sm text-slate-500">Include your participant role for interviews and any actual dress code. Unstated rules are not assumed.</p>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={feedbackGpu} onChange={e=>setFeedbackGpu(e.target.checked)}/>GPU availability is confirmed for the AI feedback step.</label><div className="flex flex-wrap gap-3"><button className={button} disabled={!occasion.trim()||!feedbackGpu||busy||active||dirty||!cap?.ai_feedback} onClick={()=>generate(true)}>Review My Outfit</button><button className={secondary} disabled={!occasion.trim()||busy||active||dirty} onClick={()=>generate(false)}>Basic summary (CPU only)</button></div><p className="text-xs text-slate-500">AI judgments use confirmed facts. Scores are experimental and withheld where evidence is insufficient.</p>
    </section>}
    {view?.state==="completed"&&view.result&&!dirty&&occasion===view.result.occasion.original_text&&<OutfitReviewResult value={view.result}/>}
    <details className="text-sm text-slate-500"><summary className="cursor-pointer">Privacy and limitations</summary><p className="mt-2">Photos and review data expire after 15 minutes or backend restart. No permanent review history is stored. The model may miss or misidentify clothing. Confirmation records your review, not verified AI accuracy. Fabric composition, hidden clothing and body attractiveness are not assessed.</p></details>
  </div>;
}
