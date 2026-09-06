"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus, RefreshCw, Shirt, Sparkles, WandSparkles } from "lucide-react";

import Layout from "@/components/Layout";
import {
  createRecommendation,
  getOutfits,
  getRecommendations,
  saveRecommendationAsOutfit,
  type Outfit,
  type Recommendation,
} from "@/lib/api";

export default function HomePage() {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [error, setError] = useState("");
  const [recommendationRequest, setRecommendationRequest] = useState("Suggest an outfit from my confirmed wardrobe.");
  const [generating, setGenerating] = useState(false);
  const [savingId, setSavingId] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [nextOutfits, nextRecommendations] = await Promise.all([getOutfits(), getRecommendations()]);
      setOutfits(nextOutfits);
      setRecommendations(nextRecommendations);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load your wardrobe.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    void Promise.all([getOutfits(), getRecommendations()]).then(([nextOutfits, nextRecommendations]) => {
      if (!active) return;
      setOutfits(nextOutfits);
      setRecommendations(nextRecommendations);
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not load your wardrobe.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const generate = async () => {
    if (!recommendationRequest.trim()) return;
    setGenerating(true);
    setError("");
    try {
      const recommendation = await createRecommendation(recommendationRequest.trim());
      setRecommendations((current) => [recommendation, ...current]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not generate a recommendation.");
    } finally {
      setGenerating(false);
    }
  };

  const saveRecommendation = async (recommendation: Recommendation) => {
    setSavingId(recommendation.id);
    setError("");
    try {
      await saveRecommendationAsOutfit(recommendation.id, "Recommended outfit");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save the recommendation.");
    } finally {
      setSavingId("");
    }
  };

  return (
    <Layout>
      <div className="space-y-10">
        <section className="border-4 border-black bg-black p-7 text-white">
          <p className="font-mono text-[10px] font-black tracking-[0.2em] text-zinc-400">SMART WARDROBE</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight">Review. Save. Visualise.</h1>
          <p className="mt-3 max-w-xl text-sm text-zinc-300">Upload a wardrobe image, confirm detected garments, build outfits, and request a private AI-assisted visualisation.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/extract" className="inline-flex items-center gap-2 bg-white px-4 py-3 text-xs font-black text-black"><Plus className="h-4 w-4" /> Add garments from image</Link>
            <Link href="/wardrobe" className="inline-flex items-center gap-2 border-2 border-white px-4 py-3 text-xs font-black text-white"><Shirt className="h-4 w-4" /> Open wardrobe</Link>
          </div>
        </section>

        {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700"><span>{error}</span><button type="button" onClick={() => void load()} className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 font-bold underline"><RefreshCw className="h-4 w-4" aria-hidden="true" /> Retry</button></div>}

        <section>
          <div className="flex items-end justify-between border-b-2 border-black pb-3">
            <div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">SAVED OUTFITS</p><h2 className="text-2xl font-black">Ready to visualise</h2></div>
            <Link href="/wardrobe" className="inline-flex items-center gap-1 text-sm font-bold underline">View wardrobe <ArrowRight className="h-4 w-4" /></Link>
          </div>
          {loading ? <div className="mt-5 grid gap-4 md:grid-cols-2" role="status" aria-label="Loading saved outfits">{[0, 1].map((item) => <div key={item} className="ui-skeleton h-36 rounded-xl" />)}</div> : outfits.length ? <div className="mt-5 grid gap-4 md:grid-cols-2">{outfits.slice(0, 4).map((outfit) => <article key={outfit.id} className="border-2 border-black bg-white p-5"><h3 className="text-lg font-black">{outfit.name}</h3><p className="mt-2 text-sm text-zinc-600">{outfit.items.map((item) => item.name).join(" · ")}</p><Link href={`/try-on?outfit=${outfit.id}`} className="mt-5 inline-flex min-h-10 items-center gap-2 bg-black px-3 py-2 text-xs font-bold text-white"><WandSparkles className="h-4 w-4" aria-hidden="true" /> Visualise outfit</Link></article>)}</div> : <div className="mt-5 border-2 border-dashed border-zinc-400 p-8 text-center"><p className="font-bold">No confirmed outfits yet.</p><p className="mt-1 text-sm text-zinc-600">Save reviewed candidates as an outfit, or construct one in your wardrobe.</p><Link href="/extract" className="mt-4 inline-flex min-h-10 items-center gap-2 underline"><Plus className="h-4 w-4" aria-hidden="true" /> Start with a wardrobe image</Link></div>}
        </section>

        <section className="border-2 border-black bg-zinc-50 p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">NLP OUTFIT ASSISTANT</p><h2 className="text-2xl font-black">Recommendations from confirmed garments</h2><p className="mt-2 max-w-2xl text-sm text-zinc-600">A recommendation is persisted with its request and source items. You can save it as an outfit or use it directly as a visualisation source.</p></div>
            <div className="w-full max-w-md"><label className="block text-xs font-bold">What are you dressing for?<textarea value={recommendationRequest} onChange={(event) => setRecommendationRequest(event.target.value)} maxLength={500} disabled={generating} className="mt-1 min-h-24 w-full resize-y border-2 border-black bg-white p-3 text-sm font-normal" /></label><div className="mt-1 text-right text-[11px] text-zinc-500">{recommendationRequest.length}/500</div><button onClick={() => void generate()} disabled={generating || !recommendationRequest.trim()} aria-busy={generating} className="mt-2 inline-flex min-h-11 items-center gap-2 bg-black px-4 py-3 text-xs font-black text-white disabled:opacity-40"><Sparkles className="h-4 w-4" aria-hidden="true" />{generating ? "Generating…" : "Suggest an outfit"}</button></div>
          </div>
          {loading ? <div className="mt-5 grid gap-4 md:grid-cols-2" role="status" aria-label="Loading recommendations">{[0, 1].map((item) => <div key={item} className="ui-skeleton h-40 rounded-xl" />)}</div> : recommendations.length ? <div className="mt-5 grid gap-4 md:grid-cols-2">{recommendations.slice(0, 4).map((recommendation) => <article key={recommendation.id} className="border-2 border-black bg-white p-5"><p className="font-mono text-[10px] font-bold tracking-widest text-zinc-500">{recommendation.status.toUpperCase()}</p><h3 className="mt-1 font-black">{recommendation.items.map((item) => item.name).join(" · ")}</h3><p className="mt-2 text-sm text-zinc-600">{recommendation.items.map((item) => item.garment_role).join(" · ")}</p><div className="mt-5 flex flex-wrap gap-2"><Link href={`/try-on?recommendation=${recommendation.id}`} className="inline-flex min-h-10 items-center gap-2 bg-black px-3 py-2 text-xs font-bold text-white"><WandSparkles className="h-4 w-4" aria-hidden="true" /> Visualise</Link><button onClick={() => void saveRecommendation(recommendation)} disabled={recommendation.status === "saved" || savingId === recommendation.id} className="min-h-10 border-2 border-black px-3 py-2 text-xs font-bold disabled:opacity-40">{savingId === recommendation.id ? "Saving…" : recommendation.status === "saved" ? "Saved as outfit" : "Save as outfit"}</button></div></article>)}</div> : <p className="mt-5 text-sm text-zinc-600">Confirm wardrobe garments, then ask the assistant for a private recommendation.</p>}
        </section>
      </div>
    </Layout>
  );
}
