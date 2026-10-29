"use client";
import { useEffect, useState } from "react";
import { createHomepageRecommendation, type RecommendationOutcome } from "@/lib/api";
import { homepageFlowKey, singleFlight } from "@/lib/recommendation-session";
import { errorMessage, outcomeMessage } from "@/lib/recommendation-messages";
import RecommendationResult from "./RecommendationResult";

export default function HomepageRecommendation({ onSaved }: { onSaved?: () => Promise<void> }) {
  const [result,setResult] = useState<RecommendationOutcome>();
  const [error,setError] = useState("");
  useEffect(() => {
    let active = true;
    const load = async () => {
      // Next may preserve page state while deactivating its effects on navigation.
      // A resumed flow must not retain a previous success if this request fails.
      await Promise.resolve();
      if (!active) return;
      setResult(undefined); setError("");
      const key = homepageFlowKey();
      return singleFlight(`home:${key}`,() => createHomepageRecommendation(key));
    };
    load().then(value => { if (active) setResult(value); }).catch(cause => { if (active) setError(errorMessage(cause)); });
    return () => { active = false; };
  },[]);
  return <section aria-labelledby="homepage-recommendation-title" className="space-y-4"><h2 id="homepage-recommendation-title" className="text-2xl font-semibold">An outfit from your wardrobe</h2>
    {!result && !error && <p role="status">Finding one complete outfit…</p>}
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error} A saved outfit has not been substituted. Reloading this page retries the same page flow.</p>}
    {result && (result.status === "Selected" && result.complete && result.recommendation ? <RecommendationResult recommendation={result.recommendation} historical={result.replayed === true} onSaved={onSaved} /> : <p role="status" className="rounded-xl bg-white p-4 text-sm text-slate-600">{outcomeMessage(result.status)}</p>)}
  </section>;
}
