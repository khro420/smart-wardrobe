"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import ProtectedImage from "@/components/ProtectedImage";
import { getTryOnHistory, removeTryOnHistory, type TryOnHistoryItem } from "@/lib/api";

export default function TryOnHistoryPage() {
  const [items, setItems] = useState<TryOnHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [more, setMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { let active = true; getTryOnHistory().then((rows) => { if (active) { setItems(rows); setOffset(rows.length); setMore(rows.length === 50); } }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Could not load history."); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, []);
  async function remove(item: TryOnHistoryItem) {
    if (busy || !window.confirm("Remove this preview from your try-on history? The private media is retained.")) return;
    setBusy(item.id); setError("");
    try { await removeTryOnHistory(item.kind, item.id); setItems((current) => current.filter((row) => row.id !== item.id || row.kind !== item.kind)); setOffset((current) => Math.max(0, current - 1)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not remove this preview."); } finally { setBusy(""); }
  }
  async function loadMore() {
    setBusy("more"); setError("");
    try { const rows = await getTryOnHistory(offset); setItems((current) => [...current, ...rows]); setOffset((current) => current + rows.length); setMore(rows.length === 50); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load more results."); } finally { setBusy(""); }
  }
  return <Layout><div className="space-y-6"><header className="rounded-3xl border border-[#ead7e2] bg-white p-7"><h1 className="text-3xl font-bold">Try-on history</h1><p className="mt-2 text-sm text-slate-600">Revisit completed previews from your account. Removing an item hides it from this list; its private media is retained.</p></header>{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}{loading ? <p role="status">Loading history…</p> : items.length ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{items.map((item) => <article key={`${item.kind}-${item.id}`} className="overflow-hidden rounded-2xl border border-slate-200 bg-white"><Link href={item.kind === "group" ? `/try-on/group/result?id=${encodeURIComponent(item.id)}` : `/try-on/result?id=${encodeURIComponent(item.id)}`}><ProtectedImage mediaId={item.output_media_id} alt={`${item.kind === "group" ? "Group" : "Single-person"} try-on preview`} className="aspect-[4/3] w-full bg-slate-50 object-contain" /></Link><div className="space-y-2 p-4"><h2 className="font-bold">{item.kind === "group" ? "Group try-on" : "Single-person try-on"}</h2><p className="text-xs text-slate-500">{new Date(item.finished_at || item.created_at).toLocaleString()}</p>{item.output_kind === "development" && <p className="text-xs text-amber-700">Development copy; not a generated try-on.</p>}<div className="flex flex-wrap gap-3 text-sm font-semibold"><Link href={item.kind === "group" ? `/try-on/group/result?id=${encodeURIComponent(item.id)}` : `/try-on/result?id=${encodeURIComponent(item.id)}`} className="text-[#6d335b] underline">View</Link><button disabled={Boolean(busy)} onClick={() => void remove(item)} className="text-rose-700 underline disabled:opacity-50">Remove</button></div></div></article>)}</div> : <p className="rounded-2xl bg-white p-6 text-sm text-slate-600">No completed try-ons yet. <Link href="/try-on/group" className="font-semibold text-[#6d335b] underline">Start a try-on</Link>.</p>}{more && <button disabled={Boolean(busy)} onClick={() => void loadMore()} className="rounded-xl border border-slate-300 bg-white px-4 py-2 font-semibold">Load more</button>}</div></Layout>;
}
