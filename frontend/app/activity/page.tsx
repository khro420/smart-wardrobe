"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { cancelGroup, cancelProcessingJob, cancelVisualisation, getActivity, type ActivityJob } from "@/lib/api";

const title = (job: ActivityJob) => job.kind === "processing" ? "Garment processing" : job.kind === "group" ? "Group try-on" : "Outfit try-on";
const link = (job: ActivityJob) => job.kind === "processing" ? `/extract/results?job=${encodeURIComponent(job.id)}` : job.kind === "group" ? `/try-on/group/result?id=${encodeURIComponent(job.id)}` : `/try-on/result?id=${encodeURIComponent(job.id)}`;
const statusText = (status: string) => ({ review_required: "Ready to review", queued: "Queued", processing: "Processing", completed: "Completed", failed: "Failed", cancelled: "Cancelled" }[status] ?? status);

export default function ActivityPage() {
  const [jobs, setJobs] = useState<ActivityJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const refresh = useCallback(async () => {
    try { const result = await getActivity(); setJobs(result.jobs); setError(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load current processes."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const initial = window.setTimeout(() => void refresh(), 0); const timer = window.setInterval(() => void refresh(), 5000); return () => { window.clearTimeout(initial); window.clearInterval(timer); }; }, [refresh]);
  async function cancel(job: ActivityJob) {
    if (busy || !window.confirm(`Cancel ${title(job).toLowerCase()}?`)) return;
    setBusy(job.id);
    try {
      if (job.kind === "processing") await cancelProcessingJob(job.id);
      else if (job.kind === "group") await cancelGroup(job.id);
      else await cancelVisualisation(job.id);
      await refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not cancel this process."); }
    finally { setBusy(""); }
  }
  return <Layout><div className="mx-auto max-w-4xl space-y-6"><header className="rounded-3xl border border-[#ead7e2] bg-white p-7"><h1 className="text-3xl font-bold">Current processes</h1><p className="mt-2 text-sm text-slate-600">Your active wearer’s garment processing and try-on jobs continue while you use other tabs. This list refreshes automatically and includes recently finished jobs.</p></header>{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}<div className="rounded-2xl bg-slate-100 p-4 text-sm text-slate-600">Try-on requests waiting for the GPU show as queued. Garment processing can show as processing while waiting for resources. Order is not guaranteed; no queue position is estimated. A service restart can interrupt unfinished jobs.</div>{loading ? <p role="status">Loading processes…</p> : jobs.length ? <div className="space-y-3">{jobs.map((job) => <article key={`${job.kind}-${job.id}`} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-bold">{title(job)}</h2><p className="mt-1 text-xs text-slate-500">Submitted {new Date(job.created_at).toLocaleString()}</p></div><span className="rounded-full bg-[#f5eaf1] px-3 py-1 text-xs font-semibold text-[#6d335b]">{statusText(job.status)}</span></div><p className="mt-3 text-sm text-slate-600">{job.error_message || job.progress_message || statusText(job.status)}</p>{job.progress_percent != null && ["queued", "processing"].includes(job.status) && <progress aria-label={`${title(job)} progress`} max={100} value={Math.max(0, Math.min(100, job.progress_percent))} className="mt-3 h-2 w-full" />}<div className="mt-4 flex flex-wrap gap-4 text-sm font-semibold"><Link href={link(job)} className="text-[#6d335b] underline">{job.status === "review_required" ? "Review garments" : ["queued", "processing"].includes(job.status) ? "View progress" : "View result"}</Link>{["queued", "processing", "review_required"].includes(job.status) && <button type="button" disabled={Boolean(busy)} onClick={() => void cancel(job)} className="text-rose-700 underline disabled:opacity-50">Cancel</button>}</div></article>)}</div> : <p className="rounded-2xl bg-white p-6 text-sm text-slate-600">No active processes for this wearer. Completed try-ons are in <Link href="/try-on/history" className="font-semibold text-[#6d335b] underline">try-on history</Link>.</p>}</div></Layout>;
}
