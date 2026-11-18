"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, Download, ImagePlus, LoaderCircle, RotateCcw, Sparkles, Users, X } from "lucide-react";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import {
  cancelGroup, createGroup, detectGroup, downloadProtectedMedia, getGroup, getOutfits,
  getPersonImages, uploadPersonImage, type GroupDetection, type GroupResult,
  type Outfit, type PersonImage,
} from "@/lib/api";

type Step = "photo" | "people" | "outfits" | "result";
const steps: { id: Step; label: string }[] = [
  { id: "photo", label: "Photo" }, { id: "people", label: "People" },
  { id: "outfits", label: "Outfits" }, { id: "result", label: "Preview" },
];
const primary = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#6d335b] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#572747] disabled:cursor-not-allowed disabled:opacity-40";
const secondary = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40";

export default function GroupTryOn() {
  const [images, setImages] = useState<PersonImage[]>([]);
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [imageId, setImageId] = useState("");
  const [step, setStep] = useState<Step>("photo");
  const [detection, setDetection] = useState<GroupDetection>();
  const [selected, setSelected] = useState<number[]>([]);
  const [assignments, setAssignments] = useState<Record<number, string>>({});
  const [result, setResult] = useState<GroupResult>();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [detectionAttempt, setDetectionAttempt] = useState(0);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const submitLock = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const image = images.find((item) => item.id === imageId);
  const currentStep = steps.findIndex((item) => item.id === step);
  const pending = result?.status === "queued" || result?.status === "processing";

  useEffect(() => {
    let active = true;
    Promise.all([getPersonImages(), getOutfits()]).then(([photos, choices]) => {
      if (active) { setImages(photos); setOutfits(choices); }
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not load photos and outfits.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // Every selected photo gets its own detection; ignore late responses after a photo change.
  useEffect(() => {
    if (!imageId) return;
    let active = true;
    detectGroup(imageId).then((found) => {
      if (!active) return;
      setDetection(found);
      setStep("people");
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not detect people. Try another photo.");
    }).finally(() => { if (active) setDetecting(false); });
    return () => { active = false; };
  }, [imageId, detectionAttempt]);

  useEffect(() => {
    if (!result || !["queued", "processing"].includes(result.status)) return;
    let active = true;
    const timer = window.setTimeout(() => {
      getGroup(result.id).then((next) => {
        if (active) { setPollError(""); setResult(next); }
      }).catch((cause: unknown) => {
        if (active) setPollError(cause instanceof Error ? cause.message : "Could not refresh progress.");
      });
    }, 2000);
    return () => { active = false; window.clearTimeout(timer); };
  }, [result]);

  function choosePhoto(id: string) {
    setError(""); setPollError(""); setDetection(undefined); setSelected([]); setAssignments({}); setResult(undefined);
    submitLock.current = false;
    setDetecting(true);
    if (id === imageId) setDetectionAttempt((value) => value + 1);
    else setImageId(id);
  }

  async function upload(file?: File) {
    if (!file || busy) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) { setError("Choose a JPEG or PNG image."); return; }
    if (file.size > 10 * 1024 * 1024) { setError("Choose an image smaller than 10 MB."); return; }
    setBusy(true); setError("");
    try {
      const photo = await uploadPersonImage(file);
      setImages((current) => [photo, ...current]);
      choosePhoto(photo.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not upload photo."); }
    finally { setBusy(false); if (fileInput.current) fileInput.current.value = ""; }
  }

  function togglePerson(index: number) {
    setError("");
    if (selected.includes(index)) {
      setSelected((current) => current.filter((item) => item !== index));
      setAssignments((current) => { const next = { ...current }; delete next[index]; return next; });
    } else if (selected.length < 2) {
      setSelected((current) => [...current, index].sort((a, b) => a - b));
    } else setError("You can select up to two people for one preview. Remove a person to select someone else.");
  }

  async function generate() {
    if (!detection || submitLock.current || !selected.length || selected.some((index) => !assignments[index])) return;
    submitLock.current = true; setBusy(true); setError("");
    try {
      await createGroup(detection.id, selected.map((index) => ({ person_index: index, outfit_id: assignments[index] })));
      setResult({ id: detection.id, status: "queued", progress_message: "Waiting for the GPU.", error_message: null, output_media_id: null });
      setStep("result");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start try-on.");
      submitLock.current = false;
    } finally { setBusy(false); }
  }

  async function cancel() {
    if (!result || busy) return;
    setBusy(true); setError("");
    try { await cancelGroup(result.id); setResult(await getGroup(result.id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not cancel the request."); }
    finally { setBusy(false); }
  }

  function reset() {
    setImageId(""); setDetection(undefined); setSelected([]); setAssignments({}); setResult(undefined);
    setError(""); setPollError(""); setStep("photo"); submitLock.current = false;
  }

  return <Layout><div className="mx-auto max-w-6xl space-y-6">
    <header className="rounded-3xl border border-[#ead7e2] bg-white p-6 shadow-sm sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#9b6a89]">Your wardrobe, imagined</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Virtual try-on</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Choose a photo, select the people you want to dress, and give each person their own outfit.</p>
      <ol aria-label="Try-on progress" className="mt-6 grid grid-cols-4 gap-2">
        {steps.map((item, index) => <li key={item.id} aria-current={step === item.id ? "step" : undefined} className={`border-t-2 pt-2 text-xs font-semibold sm:text-sm ${index <= currentStep ? "border-[#6d335b] text-[#6d335b]" : "border-slate-200 text-slate-400"}`}><span className="mr-1 hidden sm:inline">{index + 1}.</span>{item.label}</li>)}
      </ol>
    </header>
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}

    {step === "photo" && <section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="photo-heading">
      <div><h2 id="photo-heading" className="text-xl font-bold">Choose a photo</h2><p className="mt-1 text-sm text-slate-600">Select an existing photo or upload a new one. We’ll find the people in it automatically.</p></div>
      <input ref={fileInput} type="file" accept="image/jpeg,image/png" aria-label="Upload a photo" className="sr-only" disabled={busy || detecting} onChange={(event) => void upload(event.target.files?.[0])} />
      <button type="button" onClick={() => fileInput.current?.click()} disabled={busy || detecting} className="flex min-h-24 w-full items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-[#d9bdd0] bg-[#fdf8fb] p-4 text-sm font-semibold text-[#6d335b] hover:bg-[#f9eef5] disabled:opacity-50"><ImagePlus className="h-5 w-5" />{busy ? "Uploading photo…" : "Upload a new photo"}<span className="font-normal text-slate-500">JPEG or PNG · up to 10 MB</span></button>
      <div className="flex items-center gap-3"><div className="h-px flex-1 bg-slate-200" /><span className="text-xs font-medium uppercase tracking-wider text-slate-400">or choose a saved photo</span><div className="h-px flex-1 bg-slate-200" /></div>
      {loading ? <p role="status" className="text-sm text-slate-500">Loading your photos…</p> : images.length ? <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">{images.map((photo) => <button key={photo.id} type="button" disabled={busy || detecting} onClick={() => choosePhoto(photo.id)} className="overflow-hidden rounded-2xl border border-slate-200 text-left transition hover:border-[#a66c91] disabled:opacity-50"><ProtectedImage mediaId={photo.media_id} alt={photo.display_name} className="aspect-[3/4] w-full bg-slate-50 object-contain" /><span className="block truncate p-3 text-sm font-semibold">{photo.display_name}</span></button>)}</div> : <p className="rounded-xl bg-slate-50 p-5 text-sm text-slate-600">No saved photos yet. Upload one to get started.</p>}
      {detecting && <p role="status" className="flex items-center gap-2 text-sm text-[#6d335b]"><LoaderCircle className="h-4 w-4 animate-spin" /> Finding people in your photo…</p>}
      {imageId && !detecting && !detection && <button type="button" className={secondary} onClick={() => choosePhoto(imageId)}>Try detecting again</button>}
    </section>}

    {step === "people" && image && detection && <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="people-heading">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 id="people-heading" className="text-xl font-bold">Who would you like to dress?</h2><p className="mt-1 text-sm text-slate-600">We found {detection.people.length} {detection.people.length === 1 ? "person" : "people"}. Select up to two; select again to remove them.</p></div><button type="button" onClick={reset} className={secondary}>Change photo</button></div>
      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
        <div className="relative mx-auto w-full max-w-lg overflow-hidden rounded-2xl bg-slate-100" style={{ aspectRatio: `${detection.width} / ${detection.height}` }}>
          <ProtectedImage mediaId={image.media_id} alt="Photo with numbered detected people" className="h-full w-full object-contain" />
          {detection.people.map((person) => { const isSelected = selected.includes(person.index); return <button key={person.index} type="button" aria-label={`${isSelected ? "Remove" : "Select"} person ${person.index + 1}`} aria-pressed={isSelected} onClick={() => togglePerson(person.index)} className={`absolute border-2 text-left focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#6d335b] ${isSelected ? "border-[#6d335b] bg-[#6d335b]/10" : "border-white bg-black/5 shadow-[0_0_0_1px_rgba(0,0,0,0.4)]"}`} style={{ left: `${person.box[0] / detection.width * 100}%`, top: `${person.box[1] / detection.height * 100}%`, width: `${(person.box[2] - person.box[0]) / detection.width * 100}%`, height: `${(person.box[3] - person.box[1]) / detection.height * 100}%` }}><span className={`absolute left-0 top-0 inline-flex min-h-8 min-w-8 items-center justify-center gap-1 rounded-br-lg px-2 text-xs font-bold text-white ${isSelected ? "bg-[#6d335b]" : "bg-slate-800"}`}>{isSelected && <Check className="h-3 w-3" />}{person.index + 1}</span></button>; })}
        </div>
        <div className="space-y-3"><p className="text-sm font-semibold text-slate-900"><Users className="mr-2 inline h-4 w-4" />{selected.length} of 2 selected</p><p className="text-xs leading-5 text-slate-500">Tap a box or use the list below. People you leave unselected keep their original clothes.</p>{detection.people.map((person) => { const isSelected = selected.includes(person.index); return <button key={person.index} type="button" onClick={() => togglePerson(person.index)} aria-pressed={isSelected} className={`flex min-h-12 w-full items-center justify-between rounded-xl border px-4 text-left text-sm font-semibold ${isSelected ? "border-[#6d335b] bg-[#f8edf4] text-[#6d335b]" : "border-slate-200 text-slate-700 hover:bg-slate-50"}`}><span>Person {person.index + 1}</span><span className="text-xs">{isSelected ? "Remove" : "Select"}</span></button>; })}<button type="button" disabled={!selected.length} onClick={() => { setError(""); setStep("outfits"); }} className={`${primary} w-full`}>Confirm people <ArrowRight className="h-4 w-4" /></button></div>
      </div>
    </section>}

    {step === "outfits" && detection && <section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="outfits-heading">
      <div><h2 id="outfits-heading" className="text-xl font-bold">Choose an outfit for each person</h2><p className="mt-1 text-sm text-slate-600">Each saved outfit can contain a top, bottom, dress, or other supported garments.</p></div>
      {!outfits.length && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">You don’t have any saved outfits yet. <Link href="/wardrobe" className="font-semibold underline">Create an outfit in your wardrobe</Link>, then return here.</p>}
      <div className="grid gap-4 md:grid-cols-2">{selected.map((index) => <section key={index} aria-label={`Outfits for person ${index + 1}`} className="rounded-2xl border border-slate-200 p-5">
        <div className="flex items-center gap-2"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f5eaf1] text-sm font-bold text-[#6d335b]">{index + 1}</span><h3 className="font-bold">Person {index + 1}</h3></div>
        <p className="mt-3 text-sm text-slate-600">Choose an outfit to try on.</p>
        <div className="mt-3 max-h-[32rem] space-y-3 overflow-y-auto pr-1">{outfits.map((outfit) => {
          const isSelected = assignments[index] === outfit.id;
          return <article key={outfit.id} className={`rounded-xl border p-3 ${isSelected ? "border-[#6d335b] bg-[#fdf8fb] ring-1 ring-[#6d335b]" : "border-slate-200 bg-white"}`}>
            <div className="flex items-center justify-between gap-3"><h4 className="min-w-0 break-words text-sm font-bold text-slate-900">{outfit.name}</h4><button type="button" aria-pressed={isSelected} onClick={() => setAssignments((current) => ({ ...current, [index]: outfit.id }))} className={`min-h-10 shrink-0 rounded-lg px-3 text-xs font-bold ${isSelected ? "bg-[#6d335b] text-white" : "border border-slate-300 text-slate-700 hover:bg-slate-50"}`}>{isSelected ? "Selected" : "Select outfit"}</button></div>
            {outfit.items.length ? <div className="mt-3 flex gap-2 overflow-x-auto pb-1" aria-label={`Garments in ${outfit.name}`}>{outfit.items.map((item) => <div key={item.garment_id} className="w-24 shrink-0"><div className="h-28 overflow-hidden rounded-lg bg-slate-50">{item.preferred_media_id ? <ProtectedImage mediaId={item.preferred_media_id} alt={item.name} className="h-full w-full object-contain" /> : <div className="flex h-full items-center justify-center p-2 text-center text-xs text-slate-500">Image unavailable</div>}</div><p className="mt-1 break-words text-xs leading-4 text-slate-600">{item.name}</p></div>)}</div> : <p className="mt-3 text-xs text-slate-500">No garments in this outfit.</p>}
          </article>;
        })}</div>
      </section>)}</div>
      <div className="flex flex-wrap gap-3"><button type="button" className={secondary} onClick={() => { setError(""); setStep("people"); }}><ArrowLeft className="h-4 w-4" /> Edit people</button><button type="button" className={primary} disabled={busy || selected.some((index) => !assignments[index])} onClick={() => void generate()}><Sparkles className="h-4 w-4" />{busy ? "Starting…" : "Generate preview"}</button></div>
    </section>}

    {step === "result" && result && <section className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="preview-heading">
      <h2 id="preview-heading" className="text-xl font-bold">Your try-on preview</h2><p role="status" className="text-sm text-slate-600">{result.error_message || result.progress_message || result.status}</p>
      {pollError && <div role="alert" className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{pollError} <button type="button" className="font-semibold underline" onClick={() => { setPollError(""); void getGroup(result.id).then(setResult).catch((cause: unknown) => setPollError(cause instanceof Error ? cause.message : "Could not refresh progress.")); }}>Retry progress</button></div>}
      {pending && <><div className="flex items-center gap-2 text-sm text-[#6d335b]"><LoaderCircle className="h-4 w-4 animate-spin" /> Applying your outfits. This can take several minutes.</div><p className="text-sm text-slate-600">You can leave this page while it runs. Return through <Link href="/activity" className="font-semibold text-[#6d335b] underline">Current processes</Link>.</p><button type="button" disabled={busy} onClick={() => void cancel()} className={secondary}><X className="h-4 w-4" />Cancel</button></>}
      {result.status === "completed" && result.output_media_id && <><ProtectedImage mediaId={result.output_media_id} alt="Generated virtual try-on preview" className="mx-auto max-h-[70vh] w-auto max-w-full rounded-2xl" /><p className="text-xs text-slate-500">AI-generated preview; it does not predict physical fit. Check the result for changes around overlapping people and objects.</p><button type="button" className={primary} onClick={() => void downloadProtectedMedia(result.output_media_id!, "virtual-try-on.png").catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Download failed."))}><Download className="h-4 w-4" />Download preview</button></>}
      {!pending && <button type="button" onClick={reset} className={secondary}><RotateCcw className="h-4 w-4" />Start another try-on</button>}
    </section>}
  </div></Layout>;
}
