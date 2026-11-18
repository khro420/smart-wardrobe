"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import { cancelGroup, downloadProtectedMedia, getGroup, type GroupResult } from "@/lib/api";

function GroupResultPage() {
  const id = useSearchParams().get("id");
  const [result, setResult] = useState<GroupResult>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!id) return;
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await getGroup(id);
        if (!active) return;
        setError(""); setResult(next);
        if (next.status === "queued" || next.status === "processing") timer = window.setTimeout(poll, 3000);
      } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : "Could not load this preview."); }
    };
    void poll();
    return () => { active = false; if (timer) window.clearTimeout(timer); };
  }, [id, refresh]);
  const pending = result?.status === "queued" || result?.status === "processing";
  return <Layout><div className="mx-auto max-w-4xl space-y-5"><div className="flex flex-wrap gap-4 text-sm font-semibold text-[#6d335b]"><Link href="/activity">← Current processes</Link><Link href="/try-on/history">Try-on history</Link></div><section className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h1 className="text-2xl font-bold">Group try-on</h1>{!id && <p role="alert">No try-on was selected.</p>}{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error} <button className="underline" onClick={() => setRefresh((value) => value + 1)}>Retry</button></p>}{id && !result && !error && <p role="status">Loading preview…</p>}{result && <p role="status" className="text-sm text-slate-600">{result.error_message || result.progress_message || result.status}</p>}{pending && <><p className="text-sm text-slate-600">You can leave this page and return from Current processes.</p><button type="button" disabled={busy} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold" onClick={() => { if (!id) return; setBusy(true); void cancelGroup(id).then(() => setRefresh((value) => value + 1)).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not cancel." )).finally(() => setBusy(false)); }}>Cancel request</button></>}{result?.status === "completed" && result.output_media_id && <><ProtectedImage mediaId={result.output_media_id} alt="Group try-on result" className="mx-auto max-h-[70vh] w-auto max-w-full rounded-2xl" /><p className="text-xs text-slate-500">AI-generated preview; it does not predict physical fit.</p><button className="rounded-xl bg-[#6d335b] px-4 py-3 text-sm font-semibold text-white" onClick={() => void downloadProtectedMedia(result.output_media_id!, "group-try-on.png").catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not download."))}>Download</button></>}</section></div></Layout>;
}

export default function Page() { return <Suspense fallback={<Layout><p>Loading…</p></Layout>}><GroupResultPage /></Suspense>; }
