"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus, RefreshCw, Shirt, WandSparkles } from "lucide-react";
import Layout from "@/components/Layout";
import HomepageRecommendation from "@/components/HomepageRecommendation";
import { getOutfits, type Outfit } from "@/lib/api";

export default function HomePage() {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try { setOutfits(await getOutfits()); setError(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load saved outfits."); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    let active = true;
    getOutfits().then(rows => { if (active) setOutfits(rows); }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : "Could not load saved outfits."); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
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

        {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700"><span>{error}</span><button type="button" onClick={() => void load()} className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 font-bold underline"><RefreshCw className="h-4 w-4" aria-hidden="true" /> Retry saved outfits</button></div>}

        <HomepageRecommendation onSaved={load} />

        <section>
          <div className="flex items-end justify-between border-b-2 border-black pb-3">
            <div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">SAVED OUTFITS</p><h2 className="text-2xl font-black">Ready to visualise</h2></div>
            <Link href="/wardrobe" className="inline-flex items-center gap-1 text-sm font-bold underline">View wardrobe <ArrowRight className="h-4 w-4" /></Link>
          </div>
          {loading ? <div className="mt-5 grid gap-4 md:grid-cols-2" role="status" aria-label="Loading saved outfits">{[0, 1].map((item) => <div key={item} className="ui-skeleton h-36 rounded-xl" />)}</div> : outfits.length ? <div className="mt-5 grid gap-4 md:grid-cols-2">{outfits.slice(0, 4).map((outfit) => <article key={outfit.id} className="border-2 border-black bg-white p-5"><h3 className="text-lg font-black">{outfit.name}</h3><p className="mt-2 text-sm text-zinc-600">{outfit.items.map((item) => item.name).join(" · ")}</p><Link href={`/try-on?outfit=${outfit.id}`} className="mt-5 inline-flex min-h-10 items-center gap-2 bg-black px-3 py-2 text-xs font-bold text-white"><WandSparkles className="h-4 w-4" aria-hidden="true" /> Visualise outfit</Link></article>)}</div> : <div className="mt-5 border-2 border-dashed border-zinc-400 p-8 text-center"><p className="font-bold">No confirmed outfits yet.</p><p className="mt-1 text-sm text-zinc-600">Save reviewed candidates as an outfit, or construct one in your wardrobe.</p><Link href="/extract" className="mt-4 inline-flex min-h-10 items-center gap-2 underline"><Plus className="h-4 w-4" aria-hidden="true" /> Start with a wardrobe image</Link></div>}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-2xl font-semibold">Outfit Assistant</h2><p className="mt-2 text-sm text-slate-600">Submit one outfit request, then view its completed result in read-only history.</p><Link href="/assistant" className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-[#6d335b] px-4 text-sm font-semibold text-white">Open Outfit Assistant</Link></section>
      </div>
    </Layout>
  );
}
