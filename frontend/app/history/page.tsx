"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { History, WandSparkles } from "lucide-react";
import Layout from "@/components/Layout";
import { getRecommendations, type Recommendation } from "@/lib/api";

export default function RecommendationHistoryPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getRecommendations().then((rows) => { if (active) setRecommendations(rows); })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load recommendation history."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return <Layout><div className="space-y-6">
    <header className="border-2 border-black bg-white p-6"><div className="flex items-center gap-3"><History className="h-7 w-7" aria-hidden="true" /><div><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">PRIVATE HISTORY</p><h1 className="text-3xl font-black">Recommendation history</h1></div></div><p className="mt-3 max-w-2xl text-sm text-zinc-600">Review your persisted requests and the confirmed wardrobe garments selected for each response.</p></header>
    {error && <p role="alert" className="border-2 border-rose-600 bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    {loading ? <div className="grid gap-4 md:grid-cols-2" role="status" aria-label="Loading recommendation history">{[0, 1].map((item) => <div key={item} className="ui-skeleton h-48 rounded-xl" />)}</div> : recommendations.length ? <div className="grid gap-4 md:grid-cols-2">{recommendations.map((recommendation) => <article key={recommendation.id} className="border-2 border-black bg-white p-5"><div className="flex items-start justify-between gap-3"><p className="font-mono text-[10px] font-black tracking-widest text-zinc-500">{recommendation.status.toUpperCase()}</p>{recommendation.created_at && <time className="text-xs text-zinc-500">{new Date(recommendation.created_at).toLocaleString()}</time>}</div><h2 className="mt-2 font-black">{recommendation.request_text ?? "Wardrobe recommendation"}</h2><p className="mt-2 text-sm text-zinc-600">{recommendation.items.map((item) => item.name).join(" · ")}</p><p className="mt-2 text-xs text-zinc-500">Recorded score: {Math.round(recommendation.total_score * 100)}%</p><Link href={`/try-on?recommendation=${recommendation.id}`} className="mt-4 inline-flex min-h-10 items-center gap-2 bg-black px-3 py-2 text-xs font-bold text-white"><WandSparkles className="h-4 w-4" aria-hidden="true" /> Visualise</Link></article>)}</div> : <div className="border-2 border-dashed border-zinc-400 p-8 text-center"><p className="font-bold">No recommendation history yet.</p><Link href="/" className="mt-3 inline-flex min-h-10 items-center underline">Request your first recommendation</Link></div>}
  </div></Layout>;
}
